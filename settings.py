import ConfigParser

config = ConfigParser.ConfigParser()

config.read('shitstream.conf')

def config_get(section, key, default):
    try:
        return config.get(section, key, default)
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        return default

mpd_server = config_get('mpd', 'server', 'localhost')
mpd_port = config_get('mpd', 'port', 6600)
download_dir = config_get('downloaders', 'download_dir', 'music/in')
mpd_dir = config_get('mpd', 'music_dir', 'music')
