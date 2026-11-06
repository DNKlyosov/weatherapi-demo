import json
import http.client
import threading
from http.server import ThreadingHTTPServer
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server


class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def read(self):
        return json.dumps({'location': {'name': 'Белгород'}, 'current': {'temp_c': 12.3}}, ensure_ascii=False).encode('utf-8')


class WeatherTests(unittest.TestCase):
    def test_url_contains_query_and_key_masked(self):
        url = server.masked_url('Белгород')
        self.assertIn('key=***', url)
        self.assertIn('q=%D0%91', url)
        self.assertNotIn('a-super-secret', url)

    def test_live_request_url_and_safe_trace(self):
        seen = []
        def fake(request, timeout):
            seen.append(request.full_url)
            self.assertEqual(request.get_method(), 'GET')
            return FakeResponse()
        with patch.object(server, 'urlopen', side_effect=fake):
            data, trace = server.weather_request('Белгород', 'a-super-secret')
        self.assertEqual(data['current']['temp_c'], 12.3)
        self.assertIn('a-super-secret', seen[0])
        self.assertNotIn('a-super-secret', json.dumps(trace))
        self.assertIn('lang=ru', seen[0])

    def test_each_click_makes_real_external_request(self):
        with patch.object(server, 'urlopen', return_value=FakeResponse()) as mock:
            server.weather_request('Белгород', 'some-secret')
            server.weather_request('Белгород', 'some-secret')
        self.assertEqual(mock.call_count, 2)

    def test_http_endpoint_uses_proxy_and_hides_key(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict(os.environ, {'WEATHERAPI_KEY': 'a-super-secret'}):
                with patch.object(server, 'urlopen', return_value=FakeResponse()):
                    connection = http.client.HTTPConnection('127.0.0.1', httpd.server_port, timeout=5)
                    connection.request('GET', '/api/weather?city=Belgorod')
                    response = connection.getresponse()
                    body = response.read().decode('utf-8')
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(body)['weather']['current']['temp_c'], 12.3)
                    self.assertNotIn('a-super-secret', body)
                    self.assertIn('key=***', body)
                    connection.close()
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=3)

    def test_read_env_not_override_existing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / '.env'
            path.write_text('WEATHERAPI_KEY=from-file\n', encoding='utf-8')
            with patch.dict(os.environ, {'WEATHERAPI_KEY': 'from-secret'}):
                server.load_dotenv(path)
                self.assertEqual(os.getenv('WEATHERAPI_KEY'), 'from-secret')

    def test_read_env_loads_new_variable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / '.env'
            path.write_text('WEATHERAPI_KEY=from-file\n', encoding='utf-8')
            with patch.dict(os.environ, {}, clear=True):
                server.load_dotenv(path)
                self.assertEqual(os.getenv('WEATHERAPI_KEY'), 'from-file')

    def test_errors_are_human_readable(self):
        self.assertIn('Город не найден', server.provider_message(1006, 400))
        self.assertIn('ключ', server.provider_message(2006, 401))
        self.assertIn('лимит', server.provider_message(2007, 403))


if __name__ == '__main__':
    unittest.main()
