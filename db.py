from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property

from mpd_util import mpd
from server import app


db = SQLAlchemy(app)


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
    name = db.Column(db.Text)
    date = db.Column(db.String(32))

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'))
    artist = db.relationship('Artist', backref=db.backref('albums'))


class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True)
    name_alpha = db.Column(db.Text, unique=True)
    songs = db.relationship('Song', backref=db.backref('artist'), lazy='dynamic')

    @hybrid_property
    def non_album_songs(self):
        return self.songs.filter(Song.album == None).all()

@mpd
def update_db(mpdc=None):
    songs = mpdc.listallinfo()
    for song in songs:

        # Add song
        uri = song.get('file')
        if not uri:
            continue

        if Song.query.filter_by(uri=song.get('file')).all():
            continue

        new_song = Song()
        new_song.uri = uri
        new_song.name = song.get('title')
        new_song.date = song.get('date')
        new_song.length = song.get('time')
        try:
            track = int(song.get('track'))
        except:
            track = None
        new_song.track = track

        # Get or create artist
        albumartistsort = song.get('albumartistsort')
        albumartist = song.get('albumartist')
        artist_name = song.get('artist')
        artist = None

        if albumartistsort:
            artist = Artist.query.filter_by(name_alpha=albumartistsort).first()

        if not artist and albumartist:
            artist = Artist.query.filter_by(name=albumartist).first()

        if not artist and artist_name:
            artist = Artist.query.filter_by(name=artist_name).first()

        if not artist:
            for name in [albumartistsort, albumartist, artist_name]:
                if name:
                    artist = Artist()
                    artist.name = name
                    db.session.add(artist)
                    break

        new_song.artist = artist

        # Get or create album
        album_name = song.get('album')
        album = Album.query.filter_by(name=album_name, artist=new_song.artist).first()
        if not album and album_name:
            album = Album()
            album.name = album_name
            album.artist = new_song.artist
            album.date = new_song.date
            new_song.album = album
            db.session.add(album)

        db.session.add(new_song)

    db.session.commit()
