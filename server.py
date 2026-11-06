"""Minimal, standard-library HTTP server for the WeatherAPI.com lecture demo.

The upstream API key never reaches the browser. Run: python server.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))
API_ROOT = 'https://api.weatherapi.com/v1/current.json'


def load_dotenv(path: Path = ROOT / '.env') -> None:
    """Load a simple local .env; actual environment variables take priority."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        name, value = name.strip(), value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


def weather_request(city: str, key: str) -> tuple[dict, dict]:
    """Get real provider response; return a trace with the key hidden."""
    normalized = city.strip()

    query = urlencode({'key': key, 'q': normalized, 'lang': 'ru'})
    url = f'{API_ROOT}?{query}'
    request = Request(url, headers={
        'Accept': 'application/json',
        'User-Agent': 'WeatherAPILectureDemo/1.0 (educational application)',
    }, method='GET')
    print(f'[upstream] GET {masked_url(normalized)}', flush=True)
    try:
        with urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode('utf-8'))
            status = response.status
    except HTTPError as error:
        try:
            payload = json.loads(error.read().decode('utf-8'))
            code = payload.get('error', {}).get('code')
        except (ValueError, UnicodeDecodeError):
            code = None
        print(f'[upstream] HTTP {error.code}, code={code}', flush=True)
        raise ProviderFailure(error.code, code) from None
    except (URLError, TimeoutError, OSError):
        print('[upstream] network error', flush=True)
        raise ProviderFailure(502, None) from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        print('[upstream] invalid JSON', flush=True)
        raise ProviderFailure(502, None) from None

    if not isinstance(body, dict) or 'current' not in body or 'location' not in body:
        raise ProviderFailure(502, None)
    print(f'[upstream] HTTP {status}; location={body["location"].get("name", "?")}', flush=True)
    return body, {"method": "GET", "url": masked_url(normalized), "status": status}


def masked_url(city: str) -> str:
    # The API key is intentionally replaced with a placeholder in every trace.
    return API_ROOT + '?key=***&' + urlencode({'q': city, 'lang': 'ru'})


class ProviderFailure(Exception):
    def __init__(self, status: int, code: int | None):
        self.status, self.code = status, code
        super().__init__(f'WeatherAPI returned HTTP {status}')


def provider_message(code: int | None, status: int) -> str:
    if code == 1006:
        return 'Город не найден. Уточните название или добавьте страну.'
    if code in (1002, 2006):
        return 'WeatherAPI.com отклонил API-ключ. Проверьте WEATHERAPI_KEY.'
    if code == 2007:
        return 'Исчерпан лимит запросов WeatherAPI.com для этого ключа.'
    if code in (2008, 2009):
        return 'Доступ к WeatherAPI.com ограничен для этого ключа или тарифа.'
    if status in (502, 503, 504):
        return 'Сервис погоды сейчас недоступен или соединение не удалось.'
    return f'WeatherAPI.com вернул ошибку HTTP {status}.'


class Handler(BaseHTTPRequestHandler):
    server_version = 'WeatherAPILecture/1.0'
    def _write(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https://cdn.weatherapi.com; connect-src 'self'; base-uri 'none'; form-action 'self'; object-src 'none'")
        self.end_headers()
        self.wfile.write(content)

    def _json(self, status: int, value: dict) -> None:
        self._write(status, json.dumps(value, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/index.html': ('index.html', 'text/html; charset=utf-8'),
                 '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
                 '/app.js': ('app.js', 'application/javascript; charset=utf-8'),
                 '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
        if parsed.path in files:
            file_name, mime = files[parsed.path]
            self._write(200, (ROOT / file_name).read_bytes(), mime)
            return
        if parsed.path != '/api/weather':
            self._json(404, {'error': 'Маршрут не найден.'})
            return

        city = parse_qs(parsed.query).get('city', [''])[0].strip()
        if not city or len(city) > 100 or any(ord(ch) < 32 for ch in city):
            self._json(400, {'error': 'Введите название города (до 100 символов).'})
            return
        key = os.getenv('WEATHERAPI_KEY', '').strip()
        if not key or key == 'ВСТАВЬТЕ_СВОЙ_КЛЮЧ':
            self._json(503, {'error': 'API-ключ ещё не настроен. Укажите WEATHERAPI_KEY в .env или секретах Codespaces.', 'code': 'NO_KEY'})
            return
        try:
            weather, provider = weather_request(city, key)
        except ProviderFailure as error:
            client_status = error.status if error.status in (400, 401, 403, 429) else 502
            self._json(client_status, {'error': provider_message(error.code, error.status), 'provider_status': error.status, 'provider_error_code': error.code})
            return
        self._json(200, {
            'weather': weather,
            'trace': {
                'browser': {'method': 'GET', 'url': '/api/weather?' + urlencode({'city': city}), 'status': 200},
                'provider': provider,
                'server_time': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            },
        })

    def log_message(self, format: str, *args: object) -> None:
        # Keep normal request log; the provider key is never part of local URLs.
        print('[local] ' + format % args, flush=True)


if __name__ == '__main__':
    load_dotenv()
    print(f'Погодный сайт: http://localhost:{PORT}', flush=True)
    print('WEATHERAPI_KEY: ' + ('настроен' if os.getenv('WEATHERAPI_KEY') else 'не задан'), flush=True)
    print('Остановить сервер: Ctrl+C', flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
