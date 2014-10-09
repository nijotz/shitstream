import random
import threading

from mpd_util import mpd, mpd_connect
import settings

@mpd
def bumper(mpdc=None):
    while True:
        try:
            print 'Checking bumps'
            prev_song_was_bump = True
            bumped = False
            for song in mpdc.playlistinfo():
                if not song.get('file', '').startswith(settings.dj_bumps_dir):
                    if not prev_song_was_bump:
                        print "Bumpin' it"
                        pos = int(song.get('pos'))
                        bumped = False
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

            print 'Bumper waiting'
            mpdc.idle('playlist')
        except:
            print "Bumper failure, starting over"
            mpdc = mpd_connect()
            pass #FIXME: Getting bad song id sometimes (pos gets outdated?)

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
        bumps = [ bump for bump in mpdc.listallinfo(settings.dj_bumps_dir) if bump.get('file', None) ]
    except:
        bumps = None
    if bumps:
        return random.choice(bumps)

def filter_bumps(songs):
    filtered = []
    for song in songs:
        if not song.get('file', '').startswith(settings.dj_bumps_dir):
            filtered.append(song)
    return filtered

personality = bumper
