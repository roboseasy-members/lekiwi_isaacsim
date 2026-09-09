"""Local-only browser UI, without Docker socket or additional web dependencies."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit, parse_qs

import core


class App:
    def __init__(self):
        self.key = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.state = {'busy': False, 'operation': '', 'result': None, 'error': None}

    def submit(self, operation, args):
        operations = {
            'export': lambda: core.export_selected(args['episodes'], args['name'], args.get('success_only', False)),
            'inspect': lambda: core.inspect_dataset(args['name']),
        }
        if operation not in operations:
            raise core.UserError('지원하지 않는 작업입니다.')
        with self.lock:
            if self.state['busy']:
                raise core.UserError('현재 작업이 완료된 후 다시 실행하세요.')
            self.state = {'busy': True, 'operation': operation, 'result': None, 'error': None}
        def work():
            result, error = None, None
            try:
                with core.operation_lock():
                    result = operations[operation]()
            except Exception as exc:
                error = core.safe_error(exc)
            finally:
                args.clear()
                with self.lock:
                    self.state.update(busy=False, result=result, error=error)
        threading.Thread(target=work, daemon=False).start()


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # no local paths or access keys in logs

        def host_ok(self):
            return self.headers.get('Host') in ('127.0.0.1:8765', 'localhost:8765')

        def authenticated(self):
            return self.host_ok() and hmac.compare_digest(self.headers.get('X-LeKiwi-Key', ''), app.key)

        def respond(self, code, body, mime='application/json'):
            if mime == 'application/json':
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path)
            assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if not self.host_ok():
                self.respond(403, {'error': '로컬 주소로 접속하세요.'})
                return
            if path.path in assets:
                name, mime = assets[path.path]
                self.respond(200, (Path(__file__).parent / name).read_bytes(), mime)
                return
            if not self.authenticated():
                self.respond(403, {'error': '실행 터미널에 표시된 전체 주소로 접속하세요.'})
                return
            try:
                if path.path == '/api/state':
                    with app.lock:
                        state = dict(app.state)
                    self.respond(200, state)
                elif path.path == '/api/list':
                    self.respond(200, core.inventory())
                elif path.path == '/api/preview':
                    params = parse_qs(path.query)
                    episode = core.episode_path(params['episode'][0])
                    camera = params['camera'][0]
                    if camera not in ('front', 'wrist'):
                        raise core.UserError('카메라를 선택하세요.')
                    image = episode / 'images' / camera / '000000.png'
                    if not image.resolve().is_relative_to(episode.resolve()):
                        raise core.UserError('이미지 경로를 확인하세요.')
                    self.respond(200, image.read_bytes(), 'image/png')
                else:
                    self.respond(404, {'error': '페이지를 찾을 수 없습니다.'})
            except Exception as exc:
                self.respond(400, {'error': core.safe_error(exc)})

        def do_POST(self):
            origin = self.headers.get('Origin')
            if (not self.authenticated() or origin not in ('http://127.0.0.1:8765', 'http://localhost:8765')
                    or self.headers.get('Content-Type') != 'application/json'):
                self.respond(403, {'error': '허용되지 않은 요청입니다.'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 32768:
                    raise core.UserError('요청 크기를 확인하세요.')
                data = json.loads(self.rfile.read(length))
                if urlsplit(self.path).path != '/api/job' or not isinstance(data, dict):
                    raise core.UserError('지원하지 않는 요청입니다.')
                app.submit(data.pop('operation'), data)
                self.respond(202, {'accepted': True})
            except Exception as exc:
                self.respond(400, {'error': core.safe_error(exc)})
    return Handler


def serve():
    app = App()
    server = ThreadingHTTPServer(('0.0.0.0', 8765), make_handler(app))
    print(f'데이터셋 관리: http://127.0.0.1:8765/#{app.key}', flush=True)
    print('종료: 작업 완료 후 이 터미널에서 Ctrl+C. Isaac Sim을 꺼도 이 화면은 유지됩니다.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
