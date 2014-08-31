import os.path
import sys

parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)

import server
import unittest
import json
from jsonschema import validate


def json_schema_test(schema_file):
    def json_schema_test_decorator(function):
        def wrapper(*args, **kwargs):
            schema_string = open(schema_file).read()
            schema = json.loads(schema_string)

            return_value = function(*args, **kwargs)
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
    def test_artists_list(self):
        return self.client.get('/api/v1.0/artists')


class AddURLTestCase(unittest.TestCase):

    def setUp(self):
        server.app.config['TESTING'] = True
        self.client = server.socketio.test_client(server.app, namespace='/api/v1.0/add_url/')

    def tearDown(self):
        pass

    def test_no_url(self):
        self.client.get_received('/api/v1.0/add_url/')
        self.client.emit('add_url', {'url':''}, namespace='/api/v1.0/add_url/')
        received = self.client.get_received('/api/v1.0/add_url/')
        assert received[0]['args'][0]['msg'] == 'No URL received'

    def test_bad_url(self):
        self.client.get_received('/api/v1.0/add_url/')
        url = 'http://www.shitmusicforshitpeople.com/'
        self.client.emit('add_url', {'url':url}, namespace='/api/v1.0/add_url/')

        received = self.client.get_received('/api/v1.0/add_url/')
        msg = received.pop(0)

        assert msg['args'][0]['msg'] == 'Received URL'

        if not len(received):
            received = self.client.get_received('/api/v1.0/add_url/')
        msg = received.pop(0)

        assert msg['args'][0]['msg'] == 'URL does not appear to be valid'


if __name__ == '__main__':
    unittest.main()
