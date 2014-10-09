import random
import threading

from mpd_util import mpd, mpd_connect
import settings

@mpd
def bumper(mpdc=None):
    while True:
        try:
            print 'Checking bumps'
            if should_bump():
                print "Bumpin' it"
                bumped = bump_it()
                print 'Bumped'
            print 'Bumper waiting'
            mpdc.idle(['playlist', 'player'])
        except Exception as e:
            print "Bumper failure, starting over"
            print str(e)
            mpdc = mpd_connect() #FIXME: Getting bad song id sometimes (pos gets outdated?)
            # ohh, queuer identifying song blocks everything.

@mpd
def should_bump(songs=None, current=None, mpdc=None):
    """Checks time between the end of the current song to the end of the last
    bump and returns True if it's been awhile"""

    if not songs:
        songs = mpdc.playlistinfo()
    song_dict = dict([ (int(song.get('pos')), song) for song in songs ])

    if not current:
        current = int(mpdc.currentsong().get('pos'))
    if not current:
        return

    # If the next song is a bump, don't bump
    sorted_songs_pos = sorted(song_dict.keys())
    try:
        next_song = song_dict[sorted_songs_pos[sorted_songs_pos.index(current) + 1]]
    except IndexError:
        # End of the queue
        next_song = {}
    next_song_file = next_song.get('file')
    if next_song_file and next_song_file.startswith(settings.dj_bumps_dir):
        return False

    prev_songs_pos = sorted(sorted_songs_pos, reverse=True)
    prev_songs_pos = prev_songs_pos[prev_songs_pos.index(current):]

    time = 0
    for pos in prev_songs_pos:
        song = song_dict[pos]
        if song.get('file').startswith(settings.dj_bumps_dir):
            break
        time += float(song.get('time'))

    if time > (30 * 60):
        return True

    return False

@mpd
def bump_it(pos=None, mpdc=None):
    if not pos:
        current = mpdc.currentsong()
        if not current:
            return False
        pos = int(current.get('pos')) + 1

    bump = get_random_bump(mpdc=mpdc)

    if bump:
        mpdc.addid(bump.get('file'), pos)
        return True

    return False

@mpd
def get_random_bump(mpdc=None):
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
