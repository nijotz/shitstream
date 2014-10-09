import os
import re

import pyechonest.config
import pyechonest.song
import pyechonest.playlist

from downloaders.youtube import search as youtube_search
from mpd_util import mpd, mpd_connect
import settings


pyechonest.config.CODEGEN_BINARY_OVERRIDE = settings.dj_codegen_binary
pyechonest.config.ECHO_NEST_API_KEY = settings.dj_echonest_api_key


@mpd
def queuer(mpdc):
    while True:
        try:
            if should_queue(mpdc=mpdc):
                print 'Should queue, dewin it'
                queue_shit(mpdc=mpdc)
            else:
                print 'Should not queue'
            print 'Queuer waiting'
            mpdc.idle(['playlist', 'player'])
        except Exception as e:
            print 'Queuer failure, starting over:'
            print str(e)
            mpdc = mpd_connect() #FIXME: Getting bad song id sometimes (pos gets outdated?)

@mpd
def should_queue(mpdc):
    current_song = mpdc.currentsong()
    if not current_song:
        return False
    current_pos = int(current_song.get('pos'))
    queue = mpdc.playlistinfo()
    next_songs = filter(lambda x: int(x.get('pos')) >= current_pos, queue)
    timeleft = reduce(lambda x, y: x + float(y.get('time')), next_songs, 0)
    timeleft -= float(mpdc.status().get('elapsed', 0))
    if timeleft < (60 * 10):
        return True
    return False

@mpd
def prev_songs(mpdc, num=5):
    "Get the last songs listened to"

    current_song = mpdc.currentsong()

    if not current_song:
        return []

    current_pos = int(current_song.get('pos'))
    queue = mpdc.playlistinfo()
    queue = filter(lambda x: not x.get('file', '').startswith(settings.dj_bumps_dir), queue)  #FIXME: bumps filter needs dry
    queue_dict = dict([ (int(song.get('pos')), song) for song in queue ])
    sample = []
    i = current_pos
    while len(sample) < num and i >= 0:
        song = queue_dict.get(i)
        if song:
            sample.append(song)
        i -= 1

    return sample

@mpd
def queue_shit(mpdc):
    prev = prev_songs(mpdc=mpdc)
    recs = get_recommendations(prev)
    for song in recs:
        mpdc = mpd_connect(mpdc)  #FIXME:  mpd reconnect

        mpd_songs = mpdc.search('artist', song.artist_name, 'title', song.title)
        if mpd_songs:
            mpdc.add(mpd_songs[0].get('file'))
            continue

        mpd_songs = mpdc.search('artist', song.artist_name)
        if mpd_songs:
            mpdc.add(mpd_songs[0].get('file'))
            continue

        url = youtube_search('{} {}'.format(song.artist_name, song.title))
        if url:
            from server import add_url  #FIXME
            def print_(x):
                print x
            add_url(url, print_)
            

def find_youtube_vide(song):
    pass

def get_recommendations(prev):
    songs = []
    for song in prev:
        more_songs = identify_song(song)
        if more_songs:
            songs.append(more_songs)
    song_ids = [song.id for song in songs]
    if not song_ids:
        print 'No previous songs identified'
        return []
    print 'Identified {} previous songs'.format(len(song_ids))
    result = pyechonest.playlist.static(type='song-radio', song_id=song_ids, results=10)
    return result[5:]  # Does echonest return the five songs I gave it to seed?  Looks like..
    
@mpd
def identify_song(song, mpdc):
    artist = song.get('artist')
    title = song.get('title')

    if not (artist or title):
        return  #TODO: try harder

    results = pyechonest.song.search(artist=artist, title=title)
    if results:
        return results[0]
    print u'No results for: {} - {}'.format(artist,title)

    # try stripping weird characters from the names
    artist = re.sub(r'([^\s\w]|_)+', '', artist)
    title = re.sub(r'([^\s\w]|_)+', '', title)

    results = pyechonest.song.search(artist=artist, title=title)
    if results:
        return results[0]
    print u'No results for: {} - {}'.format(artist,title)

personality = queuer
