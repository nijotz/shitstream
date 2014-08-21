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
def get_artists():
    artist_names = mpd.list("artist")
    artists = [
        get_artist(get_artist_code(artist_name))
        for artist_name in artist_names
        if artist_name
    ]

    return jsonify({ 'artists': artists })


@app.route('/api/v1.0/artists/<artist_code>')
def get_artist_json(artist_code):
    return jsonify({ 'artist': get_artist(artist_code) })

def get_artist_code(artist_name):
    return encode(artist_name)

def get_artist(artist_code):

    artist_name = decode(artist_code)
    album_names = Set()
    non_album_songs = []
    artist_songs = mpd.search('artist', artist_name)

    for song in artist_songs:
        album = song.get('album')
        if album:
            album_names.add(album)
        else:
            song_id = get_song_code(song.get('file'))
            if song_id:
                non_album_songs.append(song_id)

    albums = [
        get_album_code(name, artist_name)
        for name in album_names
        if name
    ]

    return {
        'id': artist_code,
        'name': artist_name,
        'albums': albums,
        'non_album_songs': non_album_songs
    }

def get_album_code(album_name, artist_name):
    encode(str(artist_name) + '/-/' + str(album_name))  #FIXME

@app.route('/api/v1.0/queue/<junk>')
@app.route('/api/v1.0/queue')
def get_queue(junk=None):
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
