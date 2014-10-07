from md5 import md5
import os
import random
import threading
import time

import db
from GoogleTTS import audio_extract
from mpd_util import mpd
import settings



@mpd
def _deejay(mpdc=None):
    while True:
        print 'Checking bumps'
        prev_song_was_bump = True
        bumped = False
        for song in mpdc.playlistinfo():
            if not song.get('file', '').startswith(settings.bumps_dir):
                if not prev_song_was_bump:
                    print "Bumpin' it"
                    pos = int(song.get('pos'))
                    bump_it(pos, mpdc=mpdc)
                    bumped = True
                    print 'Bumped'
                    break
                else:
                    prev_song_was_bump = False
            else:
                prev_song_was_bump = True

        if bumped:
            continue

        mpdc.idle('playlist')
        print 'Waiting for playlist upate to check bumps'

@mpd
def bump_it(pos, mpdc):
    bump = get_random_bump()
    song_file = create_bump_mp3(bump)
    mpdc.update(song_file)
    #mpdc.idle('database')
    time.sleep(2)  #FIXME: mpdc.idle starts slow sometimes
    mpdc.addid(song_file, pos)

def get_random_bump():
    bumps = [bump.text for bump in db.Bump.query.all()]
    if bumps:
        return random.choice(bumps)
    return 'bump'

def create_bump_mp3(text):
    mpd_filename = os.path.join(settings.bumps_dir, md5(text).hexdigest() + '.mp3')
    filename = os.path.join(settings.mpd_dir, mpd_filename)
    if not os.path.exists(filename):
        audio_extract(text, {'output': filename})
    return mpd_filename


def filter_bumps(songs):
    for song in songs:
        if song.get('file', '').startswith(settings.bumps_dir):
            del(song)
    return songs

deejay = threading.Thread(target=_deejay)
