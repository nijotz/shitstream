#!flask/bin/python

import base64
import datetime
import os
import socket
import time
from flask import Flask, jsonify, send_file
from flask.ext.socketio import SocketIO, emit
from lxml import html
from mpd import MPDClient
import requests
from downloaders.youtube import regex as youtube_regex,\
    download as download_youtube_url
import settings

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


# Quick and dirty way to get a new mpd client connection on every request.  It
# times out if I make a global one.  The mpdc variable will be available to any
# function that is wrapped by @mpd and will be fresh instance of MPDClient.
def mpd(func):
    def fn_wrap(*args, **kwargs):
        mpdc = MPDClient()

        # Try connecting a few times, sometimes MPD can get flooded
        attempts = 0
        connected = False
        while connected == False and attempts < 4:
            try:
                mpdc.connect(settings.mpd_server, settings.mpd_port)  #FIXME: make configurable
                connected = True
            except socket.error:
                connected = False
            attempts += 1
            time.sleep(0.5)

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

# I don't want to deal with replicating the MPD database and dealing with sync
# issues, and MPD doesn't expose any kind of unique IDs for
# songs/albums/artists, so I just say fuckit and base32 encode names and make
# that the slug.  Albums are identified by 'artist/-/album'.  Songs are the
# URI, which is something MPD keeps unique, it's the songs file location.
# Artists are just identified by their name.
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
                'albums': set(),
                'non_album_songs': set()
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
    album_names = set()
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

def decode_album_code(code):
    return  decode(code).split('/-/')

@app.route('/api/v1.0/albums/<album_code>')
@mpd
def get_album_json(album_code):
    artist_name, album_name = decode_album_code(album_code)
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
@mpd
def get_playlist_json(playlist_code):
    if playlist_code == 'current':
        playlist = mpdc.playlistinfo()
    else:
        return {}

    songs = [
        {
            'id': get_playlist_song_code(playlist_code, song.get('id')),
            'pos': song.get('pos'),
            'song': get_song_code(song.get('file')),
            'playlist': playlist_code
        }
        for song in playlist
    ]

    song_ids = [ song.get('id') for song in songs ]

    return jsonify({
        'playlist': {
            'id': playlist_code,
            'songs': song_ids,
            'current_song_pos': mpdc.currentsong().get('pos')
        },

        'playlist_songs': songs
    })

def get_playlist_song_code(playlist_code, song_id):
    return encode('{}/-/{}'.format(playlist_code, song_id))

def decode_playlist_song_code(code):
    return decode(code).split('/-/')

@app.route('/api/v1.0/playlistSongs/<playlist_song_code>', methods=['DELETE'])
@mpd
def del_song_from_playlist(playlist_song_code):
    playlist_code, song_id = decode_playlist_song_code(playlist_song_code)
    if playlist_code == 'current':
        mpdc.deleteid(song_id)
    else:
        mpdc.playlistdelete(decode(playlist_code), song_id)

    return jsonify({'status': 'OK'})  #FIXME: Not sure what to return from DELETEs

@app.route('/api/v1.0/playlists/<playlist_code>/queue_song/<song_code>')
@mpd
def add_song_to_playlist(playlist_code, song_code):
    if playlist_code == 'current':
        songid = mpdc.addid(decode(song_code))
        if not mpdc.currentsong():
            mpdc.playid(songid)
    else:
        mpdc.playlistadd(decode(playlist_code), decode(song_code))

    return jsonify({'status': 'OK'}) #FIXME: Not sure what to return from DELETEs

@app.route('/api/v1.0/playlists/<playlist_code>/queue_album/<album_code>')
@mpd
def add_album_to_playlist(playlist_code, album_code):
    artist_name, album_name = decode(album_code).split('/-/')
    if playlist_code == 'current':
        songs = mpdc.search('album', album_name, 'artist', artist_name)
        firstsongid = None
        for song in songs:
            songid = mpdc.addid(song.get('file'))
            if not firstsongid:
                firstsongid = songid
        if not mpdc.currentsong():
            mpdc.playid(firstsongid)
    else:
        raise Exception

    return jsonify({'status': 'OK'})

@socketio.on('connect', namespace='/api/v1.0/add_url/')
def add_url():
    emit('response', {'msg': 'Connected'});


@socketio.on('add_url', namespace='/api/v1.0/add_url/')
@mpd
def add_url(msg):
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
    if uri[0] == '/':
        uri = uri[1:]

    # Add song to MPD
    emit('response', {'msg': 'Adding song to music database'})
    job = mpdc.update(uri)
    added = False
    while not added:
        cur_job = mpdc.status().get('updating_db')
        if (cur_job and cur_job <= job):
            emit('response', {'msg': 'Music database still updating'})
            time.sleep(1)
        else:
            added = True
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
    page = requests.get('http://store.local:9000/status.xsl')
    tree = html.fromstring(page.text)
    elem = tree.xpath('//td[text()="Current Listeners:"]/following-sibling::td')
    return jsonify({'listeners':elem[0].text})

if __name__ == '__main__':
    socketio.run(app)
