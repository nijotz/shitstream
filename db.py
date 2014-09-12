from flask.ext.sqlalchemy import SQLAlchemy

import settings
from server import app, mpd


app.config['SQLALCHEMY_DATABASE_URI'] = settings.db_uri
db = SQLAlchemy(app)


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uri = db.Column(db.Text, unique=True, nullable=False)
    date = db.Column(db.String(32))
    name = db.Column(db.Text)
    track = db.Column(db.Integer)

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'))
    artist = db.relationship('Artist', backref=db.backref('songs', lazy='dynamic'))

    album_id = db.Column(db.Integer, db.ForeignKey('album.id'))
    album = db.relationship('Album', backref=db.backref('songs', lazy='dynamic'))


class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    date = db.Column(db.String(32))

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'))
    artist = db.relationship('Artist', backref=db.backref('albums', lazy='dynamic'))


class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    alpha_name = db.Column(db.Text)


@mpd
def update_db(mpdc=None):
    songs = mpdc.listallinfo()
    for song in songs:
        uri = song.get('file')
        if not uri:
            continue

        if Song.query.filter_by(uri=song.get('file')).all():
            continue

        new_song = Song()
        new_song.uri = uri
        new_song.name = song.get('title')
        new_song.date = song.get('date')
        try:
            track = int(song.get('track'))
        except:
            track = None
        new_song.track = track

        db.session.add(new_song)
        print 'New song'

    db.session.commit()
