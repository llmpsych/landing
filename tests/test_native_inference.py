"""Real local Unix HTTP boundary with synthetic replies, never native providers."""
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from socketserver import UnixStreamServer
import tempfile
import threading
import unittest
from unittest.mock import patch

from help_service.server import configuration, Inference, NATIVE_SOCKET, Problem, Service

CONFIG = {'native_socket': NATIVE_SOCKET, 'pilot_code': 'synthetic-pilot-code-at-least-24'}


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'bridge.sock')
        self.captured = []
        self.status = 200
        self.raw = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {
            'content': '{"reply":"SYNTHETIC native response"}'}}]}).encode()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                owner.captured.append((self.path, dict(self.headers),
                                       json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(owner.status)
                self.send_header('Content-Length', str(len(owner.raw)))
                self.end_headers()
                self.wfile.write(owner.raw)

        self.server = UnixStreamServer(self.path, Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01})
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def call(self):
        # Test-only socket substitution; production accepts exactly the fixed path.
        with patch('help_service.server.NATIVE_SOCKET', self.path):
            return Inference(CONFIG)({'turns': []}, 'converse', 'Synthetic private marker')

    def test_native_wire_has_no_authority_or_provider_selection(self):
        self.assertEqual(self.call(), {'reply': 'SYNTHETIC native response'})
        path, headers, payload = self.captured[0]
        self.assertEqual(path, '/v1/chat/completions')
        self.assertNotIn('Authorization', headers)
        self.assertEqual(set(payload), {'messages', 'response_format', 'max_completion_tokens'})
        self.assertEqual(payload['max_completion_tokens'], 1800)
        self.assertEqual(payload['response_format']['json_schema']['schema']['required'], ['reply'])
        self.assertNotIn(CONFIG['pilot_code'], json.dumps(payload))

    def test_native_errors_never_commit_and_attempts_still_count(self):
        state = Path(self.temp.name) / 'state'
        service = Service(state, CONFIG)
        _, created = service.mutate('/api/sessions', CONFIG['pilot_code'], {'consent': True}, 'POST')
        token = created['token']
        service.inference = lambda *_: self.call()
        for status, raw in [(503, b'PRIVATE ERROR'), (302, b'redirect'), (200, b'not json'),
                            (200, b'x' * 65537), (200, b'{"choices":[{"finish_reason":"length"}]}')]:
            self.status, self.raw = status, raw
            with self.assertRaises(Problem) as result:
                service.mutate('/api/turn', token, {'version': 0, 'action': 'message', 'text': 'Synthetic'}, 'POST')
            self.assertEqual(result.exception.status, 502)
            self.assertNotIn('PRIVATE', result.exception.message)
            self.assertEqual(service.read(token), created['session'])
        with service.connect() as db:
            self.assertEqual(db.execute('SELECT calls FROM quota').fetchone()[0], 5)
        service.mutate('/api/session', token, {}, 'DELETE')

    def test_exclusive_fixed_configuration_and_missing_socket(self):
        path = Path(self.temp.name) / 'runtime.json'
        path.write_text(json.dumps(CONFIG)); path.chmod(0o600)
        self.assertEqual(configuration(Path(self.temp.name)), CONFIG)
        for value in [{**CONFIG, 'model': 'arbitrary'}, {**CONFIG, 'api_key': 'secret'},
                      {**CONFIG, 'native_socket': '/tmp/other.sock'}, {**CONFIG, 'pilot_code': 'short'}]:
            path.write_text(json.dumps(value))
            with self.assertRaises(Problem): configuration(Path(self.temp.name))
        with patch('help_service.server.NATIVE_SOCKET', str(Path(self.temp.name) / 'missing.sock')):
            with self.assertRaises(OSError): Inference(CONFIG)({'turns': []}, 'converse', 'Synthetic')

    def test_prior_disclosure_is_read_delete_only(self):
        service = Service(Path(self.temp.name) / 'state', CONFIG)
        _, created = service.mutate('/api/sessions', CONFIG['pilot_code'], {'consent': True}, 'POST')
        token = created['token']
        old = {**created['session'], 'consent_version': '2026-10-05-conversation'}
        with service.connect() as db:
            db.execute('UPDATE sessions SET body=?', (json.dumps(old),))
        with self.assertRaises(Problem) as result:
            service.mutate('/api/turn', token, {'version': 0, 'action': 'message', 'text': 'Synthetic'}, 'POST')
        self.assertEqual(result.exception.status, 409)
        self.assertEqual(service.read(token), old)
        self.assertEqual(self.captured, [])
        with service.connect() as db:
            self.assertEqual(db.execute('SELECT calls FROM quota').fetchone()[0], 0)
        self.assertEqual(service.mutate('/api/session', token, {}, 'DELETE')[0], 200)
