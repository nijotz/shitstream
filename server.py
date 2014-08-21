#!flask/bin/python
import base64
import datetime
from sets import Set
from flask import Flask, jsonify, send_file
from mpd import MPDClient

app = Flask(__name__)

mpd = MPDClient()
mpd.connect("localhost", 6600)


def encode(string):
    return base64.b32encode(string).replace('=', '-')

def decode(string):
    return base64.b32decode(string.replace('-', '='))

@app.route('/')
def index():
    return send_file('templates/index.html')

@app.route('/api/v1.0/artists')
def artists():
    artist_names = mpd.list("artist")
    artists = [
        {
            'id': encode(name),
            'name': name
        }
        for name in artist_names
        if name
    ]
    return jsonify({ 'artists': artists })

@app.route('/api/v1.0/artists/<artist_code>')
def artist(artist_code):

    artist_name = decode(artist_code)
    album_names = Set()
    non_album_songs = []
    artist_songs = mpd.search('artist', artist_name)

    for song in artist_songs:
        album = song.get('album')
        if album:
            album_names.add(album)
        else:
            non_album_songs.append(song)
        song['uri'] = song.get('file')

    albums = [
        {
            'id': encode(name),
            'name': name
        }
        for name in album_names
        if name
    ]

    return jsonify({
        'albums': albums,
        'non_album_songs': non_album_songs
    })

@app.route('/api/v1.0/queue/<junk>')
@app.route('/api/v1.0/queue')
def queue(junk=None):
    queue = mpd.playlistinfo()

    current = mpd.currentsong().get('pos')
    for song in queue:
        if song.get('pos') == current:
            song['playing'] = True
        else:
            song['playing'] = False

        song['length'] = str(datetime.timedelta(
            seconds=int(song['time'] or 0)))

    return jsonify({ 'queue': queue })

if __name__ == '__main__':
    app.run(debug = True)
