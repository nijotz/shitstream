#!flask/bin/python

import glob
import os
import socket
import time

from flask import Flask, jsonify, send_file
from flask.ext.conditional import conditional
from flask.ext.socketio import SocketIO, emit
from flask.ext import restless
from lxml import html
from mpd import MPDClient
import requests

import db
from downloaders.youtube import regex as youtube_regex,\
    download as download_youtube_url
from emberify import emberify
import settings


app = Flask(__name__)
if settings.debug:
    app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

api_prefix = '/api/v1.0'


def mpd(func):
    def fn_wrap(*args, **kwargs):
        if not kwargs.get('mpdc'):
            kwargs['mpdc'] = mpd_connect()
        return func(*args, **kwargs)
    fn_wrap.func_name = func.func_name
    return fn_wrap


def mpd_connect(mpdc=None):
    if not mpdc:
        mpdc = MPDClient()
    else:
        try:
            mpdc.disconnect()
        except:
            mpdc = MPDClient()

    # Try connecting a few times, sometimes MPD can get flooded
    attempts = 0
    connected = False
    while connected == False and attempts < 4:
        try:
            mpdc.connect(settings.mpd_server, settings.mpd_port)
            connected = True
        except socket.error:
            connected = False
        attempts += 1
        time.sleep(0.5)

    return mpdc


@app.route('/')
def index():
    return send_file('index.html')

def encode_playlist_song_code(song_position, song_id):
    return '{}.{}'.format(song_position, song_id)

def decode_playlist_song_code(code):
    return [int(x) for x in code.split('.')]

@app.route('/api/v1.0/playlists/<playlist_code>')
@mpd
def get_playlist_json(playlist_code, mpdc=None):
    if playlist_code == 'current':
        playlist = mpdc.playlistinfo()
    else:
        return {}

    song_files = [song.get('file') for song in playlist]
    songs = db.Song.query.filter(db.Song.uri.in_(song_files))
    song_map = dict([(song.uri, song) for song in songs])

    songs = [
        {
            'id': encode_playlist_song_code(song.get('pos'), song.get('id')),
            'pos': song.get('pos'),
            'song': song_map[song.get('file')].id,
            'playlist': playlist_code
        }
        for song in playlist
    ]

    song_ids = [ song.get('id') for song in songs ]
    pos = mpdc.currentsong().get('pos')
    if pos:
        pos = int(pos)

    return jsonify({
        'playlist': {
            'id': playlist_code,
            'songs': song_ids,
            'current_song_pos': pos
        },

        'playlist_songs': songs
    })

@app.route('/api/v1.0/playlistSongs/<playlist_song_code>', methods=['DELETE'])
@mpd
def del_song_from_playlist(playlist_song_code, mpdc=None):
    song_pos, song_id = decode_playlist_song_code(playlist_song_code)
    if int(mpdc.playlistinfo(song_pos)[0].get('id')) == song_id:
        mpdc.delete(song_pos)
    else:
        import ipdb; ipdb.set_trace()
        raise Exception
    return jsonify({'status': 'OK'})  #FIXME: Not sure what to return from DELETEs

#FIXME: This should be a put, couldn't figure out the ember.js side of it
@app.route('/api/v1.0/playlists/<playlist_code>/queue_song/<song_code>')
@mpd
def add_song_to_playlist(playlist_code, song_code, mpdc=None):
    if playlist_code != 'current':
        raise Exception
    song = db.Song.query.filter(db.Song.id == song_code).one()
    songid = mpdc.addid(song.uri)
    if not mpdc.currentsong():
        mpdc.playid(songid)

    return jsonify({'status': 'OK'}) #FIXME: Return new PlaylistSong

@app.route('/api/v1.0/playlists/<playlist_code>/queue_album/<album_code>')
@mpd
def add_album_to_playlist(playlist_code, album_code, mpdc=None):
    if playlist_code != 'current':
        raise Exception
    album = db.Album.query.filter(db.Album.id == album_code).one()
    songs = album.songs
    firstsongid = None
    for song in songs:
        # FIXME: trusts the order in which the songs are returned, doesn't
        # sort by track number.

        # Store the first song of the album, so if nothing is currently
        # playing, we know which song to start with
        songid = mpdc.addid(song.uri)
        if not firstsongid:
            firstsongid = songid

    if not mpdc.currentsong():
        mpdc.playid(firstsongid)

    return jsonify({'status': 'OK'})  #FIXME

@socketio.on('connect', namespace='/api/v1.0/add_url/')
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
@socketio.on('add_url', namespace='/api/v1.0/add_url/')
def add_url_event(msg, mpdc=None):
    in_dir = settings.download_dir
    music_dir = settings.mpd_dir

    if not msg:
        emit('response', {'msg': 'No URL received'})
        return

    url = msg.get('url', None)
    if not url:
        emit('response', {'msg': 'No URL received'})
        return

    emit('response', {'msg': 'Received URL'})

    if not youtube_regex.match(url):
        emit('response', {'msg': 'URL does not appear to be valid'})
        return

    emit('response', {'msg': 'URL appears to be valid'})
    emit('response', {'msg': 'Starting youtube-dl'})

    try:
        filename = download_youtube_url(url, in_dir, emit)
    except Exception as exception:
        emit('response', {'msg': str(exception)})
        emit('disconnect')
        return

    common = os.path.commonprefix([in_dir, music_dir])
    uri = filename.replace(common, '')
    mpdc = mpd_connect()
    if uri[0] == '/':
        uri = uri[1:]

    # Add song to MPD
    emit('response', {'msg': 'Adding song to music database'})
    update_mpd(uri,
        emit('response', {'msg': 'Music database still updating'}))
    emit('response', {'msg': 'Song added to music database'})

    # Add song to Queue
    emit('response', {'msg': 'Adding song to queue'})
    songid = mpdc.addid(uri)
    if not mpdc.currentsong():
        mpdc.playid(songid)
    emit('response', {'msg': 'Song queued'})

    emit('disconnect')

@app.route('/api/v1.0/listeners')
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
    return send_file('tests.html')


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


if __name__ == '__main__':
    db.db.create_all()
    db.update_db()

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
    )

    socketio.run(app)
