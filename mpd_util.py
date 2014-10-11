import socket
import time
import mpd as mpd_mod
from mpd import MPDClient
import settings


def mpd(func):
    def fn_wrap(*args, **kwargs):
        if not kwargs.get('mpdc'):
            mpdc = MPDClient(use_unicode=True)
            kwargs['mpdc'] = mpdc
        return func(*args, **kwargs)
    fn_wrap.func_name = func.func_name
    return fn_wrap


def mpd_reconnect_wrapper(function):
    from server import app
    logger = app.logger
    def mpd_reconnect_wrapper(self, *args, **kwargs):
        try:
            self.disconnect()
        except mpd_mod.ConnectionError as e:
            pass

        # Try connecting a few times, sometimes MPD can get flooded
        attempts = 0
        connected = False
        while connected == False and attempts < 4:
            try:
                self.connect(settings.mpd_server, settings.mpd_port)
                connected = True
                return function(self, *args, **kwargs)
            except socket.error as e:
                logger.exception(e)
                logger.error('Connection problem to mpd, running again')
                connected = False
            attempts += 1
            time.sleep(0.5)

    return mpd_reconnect_wrapper


def mpd_reconnect(cls):
    for attr_name in mpd_mod._commands:
        command = cls.__dict__.get(attr_name)
        if hasattr(command, '__call__'):
            setattr(cls, attr_name, mpd_reconnect_wrapper(command))

    return cls


def get_track_number(cls, mpd_song):
    try:
        track_str = mpd_song.get('track')
        if track_str.find('/'):
            track = int(track_str.split('/')[0])
        else:
            track = int(track_str)
    except:
        track = None

    return track


mpd_reconnect(MPDClient)
MPDClient.get_track_number = classmethod(get_track_number)
