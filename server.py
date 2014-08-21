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
    if string:
        return base64.b32encode(string).replace('=', '-')
    return ''

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

@app.route('/api/v1.0/songs/<song_code>')
def get_song_json(song_code):
    return jsonify({ 'song': get_song(song_code) })

def get_song_code(song_uri):
    return encode(song_uri)

def get_song(song_code):
    song_uri = decode(song_code)
    result = mpd.lsinfo(song_uri)
    if result:
        song = result[0]
        song['id'] = get_song_code(song.get('file'))
        song['artist'] = get_artist_code(song.get('artist'))
        song['album'] = get_album_code(song.get('album'), song.get('artist'))
        song['length'] = str(datetime.timedelta(
            seconds=int(song['time'] or 0)))
        return song
    else:
        return {}

def get_album_code(album_name, artist_name):
    encode(str(artist_name) + '/-/' + str(album_name))  #FIXME

@app.route('/api/v1.0/playlists/<playlist_code>')
def get_playlist_json(playlist_code):
    return jsonify({ 'playlist': get_playlist(playlist_code) })

def get_playlist(playlist_code):
    if playlist_code == 'current':
        playlist = mpd.playlistinfo()
    else:
        return {}

    songs = [
        get_song_code(song.get('file'))
        for song in playlist
    ]

    return {
        'id': playlist_code,
        'songs': songs
    }


if __name__ == '__main__':
    app.run(debug = True)
