import commands
import re
import sys
import pexpect
from apiclient.discovery import build
import settings

regex = re.compile('https?://(www\.)?youtube.com/.*')

version_map = {
    '2014.06.19': {
        'downloading': '(^.*\r\n)*\[download\] Destination:',
        'skipping': '(.*\r\n)*.*Post-process file (?P<file>.*) exists, skipping',
        'percent': '(.*\r\n)*.*\[download\] *(?P<perc>[0-9.]+% of .* at .* ETA [0-9:]*)',
        'downloaded': '(.*\r\n)*\[(ffmpeg|avconv)\] Destination: (?P<file>.*)\r\n'
    }
}

default_version = '2014.06.19'

def download(url, target, output):

    template = u'{}/%(title)s.%(id)s.%(ext)s'.format(target)
    child = pexpect.spawn("youtube-dl -v --keep --extract-audio --audio-format mp3 \
        --no-post-overwrites -o '{}' ".format(template) + url)
    child.logfile = sys.stdout

    # Get the output expected for this version of youtube-dl
    version = commands.getoutput('youtube-dl --version')
    expect = version_map.get(version)
    if not expect:
        expect = version_map.get(default_version)

    # Either song exists or it is downloaded
    i = child.expect([
        re.compile(expect['downloading']),
        re.compile(expect['skipping']),
    ])

    # youtube-dl is downloading
    if i == 0:
        output('Downloading song')
        downloading = True
        while downloading:

            # Look for percent complete updates or transcoding message
            j = child.expect([
                re.compile(expect['percent']),
                re.compile(expect['downloaded'])
            ])
            if j == 0:
                output(child.match.group('perc'))
            elif j == 1:
                output('Download and conversion finished')
                downloading = False

    elif i == 1:
        output('Song already exists, skipping download')

    filename = child.match.group('file')
    return filename

def search(text):
    youtube = build('youtube', 'v3', developerKey=settings.dj_youtube_api_key)
    response = youtube.search().list(
        q=text,
        part='id,snippet',
        videoCategoryId=10,
        type='video').execute()
    return 'https://www.youtube.com/watch?v=' + response.get('items')[0]['id']['videoId']
