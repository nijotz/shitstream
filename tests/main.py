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
        self.app = server.app.test_client()

    def tearDown(self):
        pass

    @json_schema_test('tests/fixtures/artists.schema.json')
    def test_artists_list(self):
        return self.app.get('/api/v1.0/artists')

if __name__ == '__main__':
    unittest.main()
