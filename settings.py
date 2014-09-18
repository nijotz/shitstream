import ConfigParser

config = ConfigParser.ConfigParser()

config.read('shitstream.conf')

def config_get(section, key, default, type_method=config.get):
    try:
        return type_method(section, key)
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        return default

mpd_server = config_get('mpd', 'server', 'localhost')
mpd_port = config_get('mpd', 'port', 6600)
mpd_dir = config_get('mpd', 'music_dir', 'music')

icecast_status_url = config_get('icecast', 'url', 'http://localhost:8000/status.xsl')

download_dir = config_get('downloaders', 'download_dir', 'music/in')

debug = config_get('general', 'debug', True, config.getboolean)

db_uri = config_get('db', 'uri', 'sqlite:///test.db')
db_clear_on_load = config_get('db', 'clear_on_load', True, config.getboolean)
