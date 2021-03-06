from datetime import datetime
from md5 import md5
import os
import threading

from flask.ext.user import UserMixin
from flask.ext.sqlalchemy import SQLAlchemy
from GoogleTTS import audio_extract
from sqlalchemy import event
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import ClauseElement

from mpd_util import mpd
from server import app
import settings


db = SQLAlchemy(app)
logger = app.logger

def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = dict((k, v) for k, v in kwargs.iteritems() if not isinstance(v, ClauseElement))
        params.update(defaults or {})
        instance = model(**params)
        session.add(instance)
        return instance, True


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uri = db.Column(db.Text, unique=True, nullable=False)
    name = db.Column(db.Text)
    track = db.Column(db.Integer)
    length = db.Column(db.Integer)
    last_modified = db.Column(db.DateTime, nullable=False)

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'))

    album_id = db.Column(db.Integer, db.ForeignKey('album.id'))
    album = db.relationship('Album', backref=db.backref('songs'))


class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    date = db.Column(db.String(32))

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'))
    artist = db.relationship('Artist', backref=db.backref('albums'))


class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    name_alpha = db.Column(db.Text)
    songs = db.relationship('Song', backref=db.backref('artist'), lazy='dynamic')

    @hybrid_property
    def non_album_songs(self):
        #FIXME: should return actual song objects, returning IDs for ember,
        #this should be in emberify
        return [song.id for song in self.songs.filter(Song.album == None).all()]


class Queue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pos = db.Column(db.Integer)
    song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
    song = db.relationship('Song', backref=db.backref('queue'))
    played = db.Column(db.Boolean, default=False, nullable=False)


class User(db.Model, UserMixin):
     id = db.Column(db.Integer, primary_key=True)
     # Flask-User fields
     active = db.Column(db.Boolean(), nullable=False, default=False)
     username = db.Column(db.String(255), nullable=False, default='')
     email = db.Column(db.String(255), nullable=False, default='')
     password = db.Column(db.String(255), nullable=False, default='')


class Bump(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(), nullable=False)

def create_bump_mp3(mapper, connection, target):
    mpd_filename = os.path.join(
        settings.bumps_dir,
        md5(target.text).hexdigest() + '.mp3'
    )
    filename = os.path.join(settings.mpd_dir, mpd_filename)
    if not os.path.exists(filename):
        audio_extract(target.text, {'output': filename})
    return mpd_filename
event.listen(Bump, 'after_update', create_bump_mp3)
event.listen(Bump, 'after_insert', create_bump_mp3)


def clear_db_songs():
    logger.info('Clearing songs')
    Song.query.filter().delete()
    Album.query.filter().delete()
    Artist.query.filter().delete()
    db.session.commit()
    logger.info('Cleared songs')


@mpd
def update_song_from_mpd_data(mpd_song, mpdc=None):
    song = Song.query.filter(Song.uri == mpd_song.get('file')).one()

    song.last_modified = datetime.strptime(mpd_song.get('last-modified'), '%Y-%m-%dT%H:%M:%SZ')
    song.name = mpd_song.get('title')
    song.track = mpdc.get_track_number(mpd_song)
    song.length = mpd_song.get('time')

    # FIXME: album and artist updates are hard, castinating like a pro
    #song.album.name = song.get('album')

    db.session.add(song)

@mpd
def new_song_from_mpd_data(song, mpdc=None):
    # Get or create song
    uri = song.get('file')
    assert uri

    song_data = {
        'uri': uri,
        'name': song.get('title'),
        'track': mpdc.get_track_number(song),
        'length': song.get('time'),
        'last_modified': datetime.strptime(song.get('last-modified'), '%Y-%m-%dT%H:%M:%SZ')
    }
    new_song = Song.query.filter(Song.uri == uri).first() or Song(**song_data)

    # Get or create artist
    artist_name = song.get('albumartist') or song.get('artist')
    # Not sure why, python-mpd2 returned a list once and I couldn't figure it out
    if type(artist_name) is list:
        artist_name = artist_name[0]
    artist_data = {
        'name': artist_name,
        'name_alpha': song.get('albumartistsort')
    }
    if artist_name:
        artist = Artist.query.filter(Artist.name == artist_data['name']).first() or Artist(**artist_data)
        db.session.add(artist)
        new_song.artist = artist

    # Get or create album
    album_data = {
        'name': song.get('album'),
        'date': song.get('date')
    }
    if new_song.artist:
        album_data['artist'] = new_song.artist
    if album_data['name']:
        album = Album.query.filter(Album.name == album_data['name']).first() or Album(**album_data)
        db.session.add(album)
        new_song.album = album

    db.session.add(new_song)
    return new_song


class MPDSyncer(threading.Thread):

    def __init__(self, filters=[], *args, **kwargs):
        self.filters = filters
        super(MPDSyncer, self).__init__(target=self.sync, *args, **kwargs)

    def filter(self, mpd_songs):
        for filter in self.filters:
            mpd_songs = filter(mpd_songs)
        return mpd_songs

    def add_filter(self, filter):
        self.filters.append(filter)

    def sync(self):
        raise NotImplemented


class SongMPDSyncer(MPDSyncer):

    @mpd
    def update_db_songs(self, mpdc=None):

        songs = mpdc.listallinfo()
        songs = self.filter(songs)

        mpd_songs = dict([ (song.get('file'), song) for song in songs if song.get('file')])
        mpd_song_files = set( mpd_songs.keys() )

        db_songs = dict([ (song.uri, song) for song in Song.query.all() ])
        db_song_files = set( db_songs.keys() )

        mpd_only_song_files = mpd_song_files.difference(db_song_files)
        db_only_song_files = db_song_files.difference(mpd_song_files)

        mpd_updated_song_files = []
        for mpd_song_file in mpd_song_files:
            mpd_song = mpd_songs[mpd_song_file]
            mpd_song_update = mpd_song.get('last-modified')
            db_song = db_songs.get(mpd_song.get('file'))
            if db_song and mpd_song_update:
                db_song_update = db_song.last_modified.strftime('%Y-%m-%dT%H:%M:%SZ')
                if db_song_update < mpd_song_update:
                    mpd_updated_song_files.append(mpd_song_file)

        total = len(mpd_only_song_files)
        num = 0
        for song_file in mpd_only_song_files:
            new_song_from_mpd_data(mpd_songs[song_file])
            num += 1
            logger.info('Added song {}/{}'.format(num, total))
        db.session.commit()

        total = len(mpd_updated_song_files)
        num = 0
        for song_file in mpd_updated_song_files:
            update_song_from_mpd_data(mpd_songs[song_file])
            num += 1
            logger.info('Updated song {}/{}'.format(num, total))
        db.session.commit()

        for song_file in db_only_song_files:
            pass  #FIXME: delete. make configurable

    @mpd
    def sync(self, mpdc=None):
        while True:
            try:
                logger.info('Updating songs')
                self.update_db_songs(mpdc=mpdc)
                logger.info('Updated db (songs)')
                mpdc.idle('database')
            except Exception as e:
                logger.exception(e)
                logger.error('DB sync failed, trying again')


class QueueMPDSyncer(MPDSyncer):

    def clear_db_queue(self):
        # For now just clear the queue data and reload it
        for queue in Queue.query.all():
            db.session.delete(queue)

    @mpd
    def update_db_queue(self, mpdc=None):

        queue = mpdc.playlistinfo()
        queue = self.filter(queue)

        current_song_pos = mpdc.currentsong().get('pos')
        if current_song_pos != None:
            current_song_pos = int(current_song_pos)

        for song in queue:
            queue = {
                'id': song.get('id'),
                'song': new_song_from_mpd_data(song),
                'pos': int(song.get('pos')),
                'played': int(song.get('pos')) < current_song_pos
            }
            get_or_create(db.session, Queue, **queue)

        db.session.commit()

    @mpd
    def sync(self, mpdc=None):
        while True:
            logger.info('Updating db (queue)')
            try:
                self.clear_db_queue()
                self.update_db_queue()
                logger.info('Updated db (queue)')
                mpdc.idle(['playlist', 'player'])
            except Exception as e:
                logger.exception(e)
                logger.error('Queue sync failed, trying again')
