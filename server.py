#!flask/bin/python
import base64
import datetime
from sets import Set
from flask import Flask, jsonify, send_file
from mpd import MPDClient

app = Flask(__name__)

def mpd(func):
    def fn_wrap(*args, **kwargs):
        mpdc = MPDClient()
        mpdc.connect("store.local", 6600)

        # Set 'mpdc' in the global context, making sure not to overwrite an
        # existing global
        glob = func.func_globals
        sentinel = object()  # a unique default to see if existing variable
            # space was taken (can't test against None)
        oldvalue = glob.get('mpdc', sentinel)
        glob['mpdc'] = mpdc

        try:
            return func(*args, **kwargs)
        finally:
            if oldvalue is sentinel:
                # old variable space was not taken, just clear it
                del glob['mpdc']
            else:
                glob['mpdc'] = oldvalue

    fn_wrap.func_name = func.func_name
    return fn_wrap

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
@mpd
def get_artists():

    songs = mpdc.listallinfo()
    artists = {}

    for song in songs:
        for tag in ['albumartistsort', 'albumartist', 'artist']:
            artist = song.get(tag)
            if artist:
                break
        if not artist:
            continue  #TODO

        artist_code = get_artist_code(artist)
        if not artists.get(artist_code):
            artists[artist_code] = {
                'name': artist,
                'albums': Set(),
                'non_album_songs': Set()
            }

        album = song.get('album')
        if album:
            album_code = get_album_code(album, artist)
            artists[artist_code]['albums'].add(album_code)
        else:
            artists[artist_code]['non_album_songs'].add(
                get_song_code(song.get('title'))
            )

    artists = [
        {
            'id': key,
            'name': value['name'],
            'albums': list(value['albums']),
            'non_album_songs': list(value['non_album_songs'])
        }
        for key, value in artists.iteritems()
    ]

    return jsonify({ 'artists': artists })


@app.route('/api/v1.0/artists/<artist_code>')
def get_artist_json(artist_code):
    return jsonify({ 'artist': get_artist(artist_code) })

def get_artist_code(artist_name):
    return encode(artist_name)

@mpd
def get_artist(artist_code):

    artist_name = decode(artist_code)
    album_names = Set()
    non_album_songs = []
    artist_songs = mpdc.search('artist', artist_name)

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

@mpd
def get_song(song_code):
    song_uri = decode(song_code)
    result = mpdc.lsinfo(song_uri)
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
    return encode(str(artist_name) + '/-/' + str(album_name))  #FIXME

@app.route('/api/v1.0/albums/<album_code>')
@mpd
def get_album_json(album_code):
    artist_name, album_name = decode(album_code).split('/-/')
    songs = mpdc.search('album', album_name, 'artist', artist_name)
    song_codes = []
    for song in songs:
        for tag in ['albumartistsort', 'albumartist', 'artist']:
            if song.get(tag) == artist_name:
                song_codes.append(encode(song.get('file')))
                break

    return jsonify({
        'album': {
            'id': album_code,
            'name': album_name,
            'artist': encode(artist_name),
            'songs': song_codes
        }
    })

@app.route('/api/v1.0/playlists/<playlist_code>')
def get_playlist_json(playlist_code):
    return jsonify({ 'playlist': get_playlist(playlist_code) })

@mpd
def get_playlist(playlist_code):
    if playlist_code == 'current':
        playlist = mpdc.playlistinfo()
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

@app.route('/api/v1.0/playlists/<playlist_code>/queue_song/<song_code>')
@mpd
def add_song_to_playlist(playlist_code, song_code):
    if playlist_code == 'current':
        mpdc.addid(decode(song_code))
        mpdc.play()
    else:
        mpdc.playlistadd(decode(playlist_code), decode(song_code))

    return jsonify({'status': 'OK'})

@app.route('/api/v1.0/playlists/<playlist_code>/queue_album/<album_code>')
@mpd
def add_album_to_playlist(playlist_code, album_code):
    artist_name, album_name = decode(album_code).split('/-/')
    if playlist_code == 'current':
        songs = mpdc.search('album', album_name, 'artist', artist_name)
        for song in songs:
            mpdc.addid(song.get('file'))
    else:
        raise Exception

    return jsonify({'status': 'OK'})

if __name__ == '__main__':
    app.run(debug = True)
