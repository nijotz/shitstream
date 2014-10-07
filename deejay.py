import random
import threading
import time

import db
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
                    bumped = bump_it(pos, mpdc=mpdc)
                    if bumped:
                        print 'Bumped'
                    break
                else:
                    prev_song_was_bump = False
            else:
                prev_song_was_bump = True

        if bumped:
            continue

        print 'Waiting for playlist upate to check bumps'
        mpdc.idle('playlist')

@mpd
def bump_it(pos, mpdc):
    bump = get_random_bump(mpdc=mpdc)
    if bump:
        mpdc.addid(bump.get('file'), pos)
        return True
    return False

@mpd
def get_random_bump(mpdc):
    try:
        bumps = [ bump for bump in mpdc.listallinfo(settings.bumps_dir) if bump.get('file', None) ]
    except:
        bumps = None
    if bumps:
        return random.choice(bumps)

def filter_bumps(songs):
    for song in songs:
        if song.get('file', '').startswith(settings.bumps_dir):
            del(song)
    return songs

deejay = threading.Thread(target=_deejay)
