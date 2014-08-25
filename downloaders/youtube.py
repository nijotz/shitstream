import commands
import re
import sys
import pexpect

regex = re.compile('https?://(www\.)?youtube.com/.*')

version_map = {
    '2014.06.19': {
        'downloading': '(^.*\r\n)*.*Destination:',
        'skipping': '(.*\r\n)*.*Post-process file (?P<file>.*) exists, skipping',
        'percent': '(.*\r\n)*.*\[download\] *(?P<perc>[0-9.]+% of .* at .* ETA [0-9:]*)',
        'downloaded': '(.*\r\n)*\[ffmpeg\] Destination: (?P<file>.*)\r\n'
    }
}

default_version = '2014.06.19'

def download(url, target, emit):

    template = '{}/%(title)s-%(id)s.%(ext)s'.format(target)
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
        emit('response', {'msg': 'Downloading song'})
        downloading = True
        while downloading:

            # Look for percent complete updates or transcoding message
            j = child.expect([
                re.compile(expect['percent']),
                re.compile(expect['downloaded'])
            ])
            if j == 0:
                emit('response', {'msg': child.match.group('perc')})
            elif j == 1:
                emit('response', {'msg': 'Download and conversion finished'})
                downloading = False

    elif i == 1:
        emit('response', {'msg': 'Song already exists, skipping download'})

    filename = child.match.group('file')
    return filename
