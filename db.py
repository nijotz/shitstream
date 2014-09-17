from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.expression import ClauseElement

from mpd_util import mpd
from server import app


db = SQLAlchemy(app)


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


def clear_db_songs():
    print 'Clearing songs'
    Song.query.filter().delete()
    Album.query.filter().delete()
    Artist.query.filter().delete()
    db.session.commit()
    print 'Cleared songs'


def new_song_from_mpd_data(song):
    # Get or create song
    uri = song.get('file')
    assert uri

    try:
        track = int(song.get('track'))
    except:
        track = None

    song_data = {
        'uri': uri,
        'name': song.get('title'),
        'track': track,
        'length': song.get('time')
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


@mpd
def update_db_songs(mpdc=None):
    songs = mpdc.listallinfo()
    for song in songs:
        # listallinfo returns directories, ignore them
        if not song.get('file'):
            continue
        new_song_from_mpd_data(song)
    db.session.commit()


def clear_db_queue():
    # For now just clear the queue data and reload it
    for queue in Queue.query.all():
        db.session.delete(queue)


@mpd
def update_db_queue(mpdc=None):
    queue = mpdc.playlistinfo()
    current_song_pos = int(mpdc.currentsong().get('pos'))

    for song in queue:
        queue = {
            'id': song.get('id'),
            'song': Song.query.filter(Song.uri == song.get('file')).one(),
            'pos': int(song.get('pos')),
            'played': int(song.get('pos')) < current_song_pos
        }
        get_or_create(db.session, Queue, **queue)

    db.session.commit()


#FIXME: proper logging instead of print
@mpd
def update_queue_on_change(mpdc=None):
    while True:
        print 'Updating db (queue)'
        clear_db_queue()
        update_db_queue()
        print 'Updated db (queue)'
        mpdc.idle('playlist')

@mpd
def update_songs_on_change(mpdc=None):
    while True:
        print 'Updating db (songs)'
        update_db_songs()
        print 'Updated db (songs)'
        mpdc.idle('database')
