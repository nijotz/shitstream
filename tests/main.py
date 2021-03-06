import os.path
import sys

parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)

import server
import unittest
import json
from jsonschema import validate


server.init()

def json_schema_test(schema_file):
    def json_schema_test_decorator(function):
        def wrapper(*args, **kwargs):
            schema_string = open(schema_file).read()
            schema = json.loads(schema_string)

            return_value = function(*args, **kwargs)
            if return_value.status_code != 200:
                print return_value.data
                assert return_value.status_code == 200
            json_data = json.loads(return_value.data)
            validate(json_data, schema)
        return wrapper
    return json_schema_test_decorator


class MainTestCase(unittest.TestCase):

    def setUp(self):
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()

    def tearDown(self):
        pass

    @json_schema_test('tests/fixtures/artists.schema.json')
    def test_artists(self):
        return self.client.get('/api/v1.0/artists')

    @json_schema_test('tests/fixtures/artist.schema.json')
    def test_artist(self):
        return self.client.get('/api/v1.0/artists/1')

    @json_schema_test('tests/fixtures/album.schema.json')
    def test_album(self):
        return self.client.get('/api/v1.0/albums/1')

    @json_schema_test('tests/fixtures/queue.schema.json')
    def test_queue(self):
        return self.client.get('/api/v1.0/queue')


class AddURLTestCase(unittest.TestCase):

    def setUp(self):
        server.app.config['TESTING'] = True
        self.namespace = '/api/v1.0/add_url/'
        self.client = server.socketio.test_client(server.app, namespace=self.namespace)

    def tearDown(self):
        pass

    def process_event(self, received=None):
        if not received or not len(received):
            if not getattr(self, '_received', None):
                self._received = self.client.get_received(self.namespace)
            received = self._received
        if len(received) > 0:
            return received.pop(0)
        return None

    def test_no_url(self):
        self.client.get_received(self.namespace)
        self.client.emit('add_url', {'url':''}, namespace=self.namespace)
        received = self.client.get_received(self.namespace)
        assert received[0]['args'][0]['msg'] == 'No URL received'

    def test_bad_url(self):
        self.client.get_received(self.namespace)
        url = 'http://www.shitmusicforshitpeople.com/'
        self.client.emit('add_url', {'url':url}, namespace=self.namespace)

        msg = self.process_event()
        assert msg['args'][0]['msg'] == 'Received URL'
        msg = self.process_event()
        assert msg['args'][0]['msg'] == 'URL does not appear to be valid'

    def test_good_url(self):
        self.client.get_received(self.namespace)
        url = 'https://www.youtube.com/watch?v=dXGa__ECvnM'
        self.client.emit('add_url', {'url':url}, namespace=self.namespace)

        msg = self.process_event()
        assert msg['args'][0]['msg'] == 'Received URL'
        msg = self.process_event()
        assert msg['args'][0]['msg'] == 'URL appears to be valid'
        msg = self.process_event()
        assert msg['args'][0]['msg'] == 'Starting youtube-dl'

        added = False
        while not added:
            msg = self.process_event()
            if msg['args'][0]['msg'] == 'Song added to music database':
                added = True
            else:
                print msg

        msg = self.process_event()
        assert msg['args'][0]['msg'] == 'Adding song to queue'
        msg = self.process_event()
        assert msg['args'][0]['msg'] == 'Song queued'


if __name__ == '__main__':
    unittest.main()
