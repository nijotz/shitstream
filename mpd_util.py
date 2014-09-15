import socket
import time
from mpd import MPDClient
import settings

def mpd(func):
    def fn_wrap(*args, **kwargs):
        if not kwargs.get('mpdc'):
            kwargs['mpdc'] = mpd_connect()
        return func(*args, **kwargs)
    fn_wrap.func_name = func.func_name
    return fn_wrap


def mpd_connect(mpdc=None):
    if not mpdc:
        mpdc = MPDClient(use_unicode=True)
    else:
        try:
            mpdc.disconnect()
        except:
            mpdc = MPDClient(use_unicode=True)

    # Try connecting a few times, sometimes MPD can get flooded
    attempts = 0
    connected = False
    while connected == False and attempts < 4:
        try:
            mpdc.connect(settings.mpd_server, settings.mpd_port)
            connected = True
        except socket.error:
            connected = False
        attempts += 1
        time.sleep(0.5)

    return mpdc


