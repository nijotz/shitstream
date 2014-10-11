#!flask/bin/python

from functools import wraps
import glob
import logging
import os
import sys
import subprocess
import time

from flask import Flask, jsonify, request, render_template
from flask.ext import restless
from flask.ext.babel import Babel
from flask.ext.conditional import conditional
from flask.ext.script import Manager, Command
from flask.ext.socketio import SocketIO, emit
from flask.ext.user import UserManager, SQLAlchemyAdapter
from lxml import html
from mutagen.mp3 import MP3
import requests

from downloaders.youtube import regex as youtube_regex,\
    download as download_youtube_url
from emberify import emberify
from mpd_util import mpd
import settings


class PEP3101Formatter(logging.Formatter):

    def usesTime(self):
        """
        Check if the format uses the creation time of the record.
        """
        return self._fmt.find("{asctime}") >= 0

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self._fmt.format(**record.__dict__)
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            try:
                s = s + record.exc_text
            except UnicodeError:
                # Sometimes filenames have non-ASCII chars, which can lead
                # to errors when s is Unicode and record.exc_text is str
                # See issue 8924.
                # We also use replace for when there are multiple
                # encodings, e.g. UTF-8 for the filesystem and latin-1
                # for a script. See issue 13232.
                s = s + record.exc_text.decode(sys.getfilesystemencoding(),
                                               'replace')
        return s


def create_app():
    app = Flask(__name__)
    log_level = logging.INFO
    if settings.debug:
        app.debug = True
        del(app.logger.handlers[0])  # DEBUG logger is fucking stupid, send it to hell
        log_level = logging.DEBUG
    app.config['SECRET_KEY'] = 'secret!'
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.db_uri
    app.config['USER_ENABLE_EMAIL'] = False

    handler = logging.StreamHandler()
    formatter = PEP3101Formatter('{asctime} [{module: ^10}] [{levelname: ^7}] {message}')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    return app

app = create_app()

import db
from admin import setup as admin_setup

api_prefix = '/api/v1.0'
socketio = SocketIO(app)

def api_route(route, *args, **kwargs):
    def wrapper(function):
        @app.route(api_prefix + route, *args, **kwargs)
        @wraps(function)
        def route_fn(*args, **kwargs):
            return function(*args, **kwargs)
        return route_fn
    return wrapper


@app.route('/')
def index():
    return render_template('index.html')


@api_route('/queue/<queue_id>', methods=['DELETE'])
@mpd
def del_song_from_queue(queue_id, mpdc=None):
    queue = db.Queue.query.filter(db.Queue.id == queue_id).one()
    mpdc.deleteid(queue.id)
    return jsonify({})


@api_route('/queue', methods=['POST'])
@mpd
def add_song_to_queue(mpdc=None):
    song_id = request.json['queue']['song']
    song = db.Song.query.filter(db.Song.id == song_id).one()
    queue_id = int(mpdc.addid(song.uri))
    queue_data = mpdc.playlistid(queue_id)[0]
    if not mpdc.currentsong():
        mpdc.playid(queue_id)

    return jsonify({'queue': {
        'id': queue_id,
        'pos': queue_data['pos'],
        'song': song_id
    }})


@api_route('/queue/album', methods=['POST'])
@mpd
def add_album_to_queue(mpdc=None):
    #TODO: some kind of lock to make sure a song isn't queued between album
    # songs by another request

    album_id = request.json['album']['id']
    album = db.Album.query.filter(db.Album.id == album_id).one()
    songs = db.Song.query.filter(db.Song.album_id == album.id).order_by(db.Song.track).all()

    # Capture queued songs to send back to the client
    queue = []
    first = None
    for song in songs:

        queue_id = int(mpdc.addid(song.uri))
        queue_data = mpdc.playlistid(queue_id)[0]
        queue.append({
            'id': queue_id,
            'pos': queue_data['pos'],
            'song': song.id
        })

        if not first:
            first = queue_id

    # If not currently playing, play the first song of the album
    if not mpdc.currentsong():
        mpdc.playid(first)

    return jsonify({'queue': queue})


@socketio.on('connect', namespace = api_prefix + '/add_url/')
def add_url_connect():
    emit('response', {'msg': 'Connected'});

@mpd
def update_mpd(uri=None, updating=None, mpdc=None):
    job = mpdc.update(uri)
    added = False
    while not added:
        cur_job = mpdc.status().get('updating_db')
        if (cur_job and cur_job <= job):
            if updating:
                updating()
            time.sleep(1)
        else:
            added = True

@mpd
def add_url(url, output, mpdc=None):
    in_dir = settings.download_dir
    music_dir = settings.mpd_dir

    filename = download_youtube_url(url, in_dir, output)

    common = os.path.commonprefix([in_dir, music_dir])
    uri = filename.replace(common, '')
    if uri[0] == '/':
        uri = uri[1:]

    # Add song to MPD
    output('Adding song to music database')
    update_mpd(uri, lambda: output('Music database still updating'))
    output('Song added to music database')

    # Add song to database
    song = mpdc.listallinfo(uri)[0]
    db.new_song_from_mpd_data(song)
    db.db.session.commit()

    # Add song to Queue
    output('Adding song to queue')
    songid = mpdc.addid(uri)
    if not mpdc.currentsong():
        mpdc.playid(songid)
    output('Song queued')

    # Identify and tag song
    output('Identifying song')
    #Good ol' try-except-pass. Quality.
    try:
        tag_song_from_filename(filename)
    except:
        pass

    beet_path = subprocess.check_output("which beet", shell=True).strip()
    subprocess.call([beet_path, 'import', '-qsC', filename]) # No escaping

    # Re-scan file
    output('Updating song database')
    update_mpd(uri, lambda: output('Music database still updating'))
    output('Song info updated')


# artist and song are probably separated by a -
def tag_song_from_filename(filepath):
    filename = os.path.basename(filepath)
    artist, title = filename.split('- ')[0:2]
    title = ''.join(title.split('.')[0:-2]).strip()
    artist = artist.strip()
    id3info = MP3(filename)
    id3info['artist'] = artist
    id3info['title'] = title
    return

@mpd
@socketio.on('add_url', namespace = api_prefix + '/add_url/')
def add_url_event(msg, mpdc=None):
    output = lambda m: emit('response', {'msg': m})

    if not msg:
        output('No URL received')
        return  #FIXME disconnect

    url = msg.get('url', None)
    if not url:
        output('No URL received')
        return  #FIXME disconnect

    output('Received URL')

    if not youtube_regex.match(url):
        output('URL does not appear to be valid')
        return  #FIXME disconnect

    output('URL appears to be valid')
    output('Starting youtube-dl')

    try:
        add_url(url, output)
        output('Done')
    except Exception as exception:
        output(str(exception))
        emit('disconnect')
        return

    emit('disconnect')

@api_route('/listeners')
def get_listeners():
    try:
        url = settings.icecast_status_url
        page = requests.get(url)
        tree = html.fromstring(page.text)
        elem = tree.xpath('//td[text()="Current Listeners:"]/following-sibling::td')
        return jsonify({'listeners':elem[0].text})
    except:
        return jsonify({'listeners': None})


##
## Test methods, enabled only if debug is True
##
@conditional(app.route('/tests'), app.debug)
def tests():
    return render_template('tests.html')


@conditional(app.route('/tests/reset'), app.debug)
@mpd
def tests_reset(mpdc=None):
    files_glob = os.path.join(settings.download_dir, '*')
    files = glob.glob(files_glob)
    for f in files:
        os.remove(f)
    update_mpd(mpdc=mpdc)
    mpdc.clear()
    return jsonify({'status': 'OK'})


def init():
    db.db.create_all()
    if settings.db_clear_on_load:
        db.clear_db_songs()

    import deejay
    from deejay import bumper

    queue_updates = db.QueueMPDSyncer()
    queue_updates.add_filter(bumper.filter_bumps)
    queue_updates.start()

    song_updates = db.SongMPDSyncer()
    song_updates.add_filter(bumper.filter_bumps)
    song_updates.start()

    deejay.load_personality()

    manager = restless.APIManager(app, flask_sqlalchemy_db=db.db)

    #FIXME: copypaste
    manager.create_api(
        db.Artist,
        methods=['GET'],
        url_prefix=api_prefix,
        collection_name='artists',
        postprocessors={
            'GET_MANY': [emberify('artists', db.Artist)],
            'GET_SINGLE': [emberify('artist', db.Artist, many=False)]
        },
        results_per_page=None
    )
    manager.create_api(
        db.Song,
        methods=['GET'],
        url_prefix=api_prefix,
        collection_name='songs',
        postprocessors={
            'GET_MANY': [emberify('songs', db.Song)],
            'GET_SINGLE': [emberify('song', db.Song, many=False)]
        },
        results_per_page=None
    )
    manager.create_api(
        db.Album,
        methods=['GET'],
        url_prefix=api_prefix,
        collection_name='albums',
        postprocessors={
            'GET_MANY': [emberify('albums', db.Album)],
            'GET_SINGLE': [emberify('album', db.Album, many=False)]
        },
        results_per_page=None
    )
    manager.create_api(
        db.Queue,
        methods=['GET'],
        url_prefix=api_prefix,
        collection_name='queue',
        postprocessors={
            'GET_MANY': [emberify('queue', db.Queue)],
            'GET_SINGLE': [emberify('queue', db.Queue, many=False)]
        },
        results_per_page=None
    )


if __name__ == '__main__':
    init()
    admin_setup(app)
    if settings.debug:
        from flask_debugtoolbar import DebugToolbarExtension
        toolbar = DebugToolbarExtension(app)
    babel = Babel(app)
    db_adapter = SQLAlchemyAdapter(db.db,  db.User)
    user_manager = UserManager(db_adapter, app)
    manager = Manager(app)

    class SocketIOServer(Command):
        def run(self):
            socketio.run(app)

    manager.add_command("runserver", SocketIOServer())
    manager.run()
