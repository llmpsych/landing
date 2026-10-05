"""HTTP-level checks use synthetic inference, never a live provider claim."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from help_service.server import Service, Server, Inference, Problem, configuration, release_sha

CONFIG = {'api_key': 'test-only-not-a-credential', 'model': 'test-fixture', 'pilot_code': 'synthetic-pilot-code-at-least-24'}
INTAKE = {'consent': True}


class Fixture:
    """Only injectable in tests; no production config enables this."""
    def __init__(self):
        self.calls = []
        self.fail = False
        self.actions = []

    def __call__(self, session, action, text):
        self.actions.append(action)
        self.calls.append(json.loads(json.dumps(session)))
        if self.fail:
            raise RuntimeError('PRIVATE PROVIDER ERROR MUST NOT LEAK')
        result = {'reply': 'SYNTHETIC FIXTURE: a concrete reflection on ' + text}
        return result


class HelpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.fixture = Fixture()
        self.start()

    def start(self, config=CONFIG):
        self.service = Service(Path(self.temp.name), config, 'a' * 40, self.fixture)
        self.server = Server(('127.0.0.1', 0), self.service, 'https://help.web.llmpsych.1puni.com')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def tearDown(self):
        self.stop()
        self.temp.cleanup()

    def request(self, path, method='GET', body=None, token='', headers=None):
        raw = json.dumps(body).encode() if body is not None else None
        request = Request(self.url + path, data=raw, method=method, headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token,
            **(headers or {})})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            data = response.read()
            return response.status, json.loads(data) if 'application/json' in response.headers['Content-Type'] else data

    def create(self, **overrides):
        status, result = self.request('/api/sessions', 'POST', {**INTAKE, **overrides}, CONFIG['pilot_code'])
        self.assertEqual(status, 201, result)
        return result['token']

    def turn(self, token, version, action, text='SYNTHETIC observation'):
        return self.request('/api/turn', 'POST', {'version': version, 'action': action, 'text': text}, token)

    def test_full_journey_isolation_restart_delete(self):
        token, other = self.create(), self.create()
        self.assertEqual(self.turn(token, 0, 'message', 'PRIVATE MARKER A')[0], 200)
        self.assertEqual(self.turn(token, 0, 'message')[0], 409)
        self.stop()
        self.start()
        status, result = self.request('/api/session', token=token)
        self.assertEqual(result['session']['phase'], 'conversation')
        status, result = self.turn(token, 1, 'finish')
        self.assertEqual(status, 200)
        self.assertEqual(result['session']['phase'], 'complete')
        self.assertEqual(self.fixture.actions, ['converse', 'close'])
        self.assertEqual(self.turn(token, 2, 'message')[0], 409)
        self.assertEqual(self.request('/api/session', token=other)[1]['session']['version'], 0)
        self.assertNotIn('PRIVATE MARKER A', json.dumps(self.request('/api/session', token=other)))
        self.assertEqual(self.request('/api/session', token=CONFIG['pilot_code'])[0], 401)
        self.assertEqual(self.request('/api/session', token='z' * 43)[0], 404)
        self.assertEqual(self.request('/api/session', 'DELETE', {}, token)[0], 200)
        self.assertEqual(self.request('/api/session', token=token)[0], 404)
        self.assertEqual(self.request('/api/session', token=other)[0], 200)
        self.assertNotIn(token.encode(), self.service.db.read_bytes())

    def test_provider_failure_does_not_commit_or_log(self):
        token = self.create()
        self.fixture.fail = True
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status, result = self.turn(token, 0, 'message', 'PRIVATE INPUT MARKER')
        self.assertEqual(status, 502)
        self.assertNotIn('PRIVATE', json.dumps(result) + stdout.getvalue() + stderr.getvalue())
        self.assertEqual(self.request('/api/session', token=token)[1]['session']['version'], 0)
        self.fixture.fail = False
        self.assertEqual(self.turn(token, 0, 'message')[0], 200)

    def test_missing_runtime_health_and_create(self):
        status, health = self.request('/healthz')
        self.assertEqual(status, 200)
        self.assertEqual(health, {'sha': 'a' * 40, 'inference_configured': True})
        self.assertEqual(self.fixture.actions, [])
        self.stop()
        self.start({})
        status, health = self.request('/healthz')
        self.assertEqual(status, 200)
        self.assertEqual(health, {'sha': 'a' * 40, 'inference_configured': False})
        self.assertEqual(self.request('/api/sessions', 'POST', INTAKE, CONFIG['pilot_code'])[0], 503)
        with self.service.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0], 0)

    def test_input_authority_and_storage_boundaries(self):
        self.assertEqual(self.request('/api/sessions', 'POST', INTAKE, 'wrong')[0], 401)
        self.assertEqual(self.request('/api/sessions', 'POST', {**INTAKE, 'consent': False}, CONFIG['pilot_code'])[0], 400)
        self.assertEqual(self.request('/api/sessions', 'POST', {**INTAKE, 'unexpected': 'x'}, CONFIG['pilot_code'])[0], 400)
        token = self.create()
        self.assertEqual(self.turn(token, 0, 'message', 'x' * 17000)[0], 413)
        self.assertEqual(self.request('/api/turn', 'POST', {}, token, {'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('/api/turn', 'POST', {}, token, {'Content-Type': 'text/plain'})[0], 415)
        for path in ['/api/sessions', '/runtime.json', '/server.py', '/../runtime.json', '/sessions.sqlite3', '/?token=secret']:
            self.assertEqual(self.request(path)[0], 404)
        for path in ['/', '/app.js', '/style.css', '/api-docs']:
            self.assertEqual(self.request(path)[0], 200)
        self.service.mutation.acquire()
        try:
            self.assertEqual(self.turn(token, 0, 'message')[0], 503)
            self.assertEqual(self.request('/api/session', token=token)[0], 200)
        finally:
            self.service.mutation.release()
        with self.assertRaises(Problem):
            Service(Path(__file__).resolve().parents[1] / 'private-test', CONFIG)

    def test_expiry_and_persistent_quotas(self):
        token = self.create()
        with self.service.connect() as db:
            db.execute('UPDATE sessions SET expires=?', (time.time() - 1,))
            db.execute('UPDATE quota SET sessions=100')
        self.assertEqual(self.request('/api/session', token=token)[0], 404)
        self.service.purge()
        with self.service.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0], 0)
        self.stop()
        self.start()
        self.assertEqual(self.request('/api/sessions', 'POST', INTAKE, CONFIG['pilot_code'])[0], 429)

    def test_bad_provider_output_and_turn_limits(self):
        token = self.create()
        self.service.inference = lambda *_: {'reply': '', 'shell': 'unauthorized'}
        self.assertEqual(self.turn(token, 0, 'message')[0], 502)
        self.service.inference = self.fixture
        for version in range(12):
            if version == 11:
                self.fixture.fail = True
                self.assertEqual(self.turn(token, version, 'message')[0], 502)
                unchanged = self.service.read(token)
                self.assertEqual(unchanged['version'], 11)
                self.assertEqual(unchanged['phase'], 'conversation')
                self.fixture.fail = False
            status, result = self.turn(token, version, 'message')
            self.assertEqual(status, 200)
            self.assertEqual(len(result['session']['turns']), version + 1)
        self.assertEqual(result['session']['phase'], 'complete')
        self.assertEqual(self.fixture.actions[-1], 'close')
        self.assertEqual(self.turn(token, 12, 'finish')[0], 409)
        self.assertEqual(len(self.fixture.calls), 13)

    def test_failed_attempt_budget_persists_and_stale_is_free(self):
        token = self.create()
        self.fixture.fail = True
        self.assertEqual(self.turn(token, 0, 'finish')[0], 502)
        self.assertEqual(self.service.read(token)['turns'], [])
        with self.service.connect() as db:
            self.assertEqual(db.execute('SELECT calls FROM quota').fetchone()[0], 1)
        self.stop()
        self.start()
        self.fixture.fail = False
        self.assertEqual(self.turn(token, 0, 'message')[0], 200)
        self.assertEqual(self.turn(token, 0, 'message')[0], 409)
        with self.service.connect() as db:
            self.assertEqual(db.execute('SELECT calls FROM quota').fetchone()[0], 2)
            db.execute('UPDATE quota SET calls=300')
        other = self.create()
        self.assertEqual(self.turn(other, 0, 'message')[0], 429)
        self.assertEqual(self.turn(token, 1, 'finish')[0], 429)

    def test_legacy_read_only_and_deletable(self):
        token = self.create()
        old = {'version': 2, 'phase': 'experiment', 'intake': {'difficulty': 'old'},
               'turns': [], 'experiment': {'change': 'old proposal'}}
        with self.service.connect() as db:
            db.execute('UPDATE sessions SET body=? WHERE key=?', (json.dumps(old), self.service.key(token)))
        self.assertEqual(self.service.read(token), old)
        self.assertEqual(self.turn(token, 2, 'message')[0], 409)
        self.assertEqual(self.turn(token, 2, 'followup')[0], 409)
        self.assertEqual(self.service.read(token), old)
        self.assertEqual(self.request('/api/session', 'DELETE', {}, token)[0], 200)

    def test_provider_wire_contract(self):
        captured = []
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, limit):
                return json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': '{"reply":"synthetic"}'}}]}).encode()
        class Opener:
            def open(self, request, timeout):
                captured.append(request)
                self.timeout = timeout
                return Response()
        with patch('help_service.server.build_opener', return_value=Opener()):
            result = Inference(CONFIG)({'turns': []}, 'converse', 'Synthetic')
        self.assertEqual(result['reply'], 'synthetic')
        request = captured[0]
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/chat/completions')
        payload = json.loads(request.data)
        self.assertFalse(payload['store'])
        self.assertNotIn('tools', payload)
        self.assertNotIn(CONFIG['api_key'], request.data.decode())
        self.assertNotIn(CONFIG['pilot_code'], request.data.decode())
        self.assertEqual(payload['max_completion_tokens'], 1800)
        self.assertEqual(set(payload['response_format']['json_schema']['schema']['properties']), {'reply'})
        self.assertEqual(json.loads(payload['messages'][1]['content'])['exchanges_remaining_after_reply'], 11)
        with patch('help_service.server.build_opener', return_value=Opener()):
            Inference(CONFIG)({'turns': []}, 'close', 'Stop here')
        closing_payload = json.loads(captured[-1].data)
        self.assertEqual(json.loads(closing_payload['messages'][1]['content'])['exchanges_remaining_after_reply'], 0)

    def test_reproducible_e2e_checker(self):
        from scripts.check_help import check
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            check(self.url, 'a' * 40, CONFIG['pilot_code'])
        self.assertIn('Synthetic sessions deleted', output.getvalue())
        self.assertNotIn(CONFIG['pilot_code'], output.getvalue())
        with self.service.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0], 0)

    def test_configuration_and_release_identity(self):
        state = Path(self.temp.name)
        self.assertEqual(configuration(state), {})
        config_file = state / 'runtime.json'
        config_file.write_text(json.dumps(CONFIG))
        config_file.chmod(0o644)
        with self.assertRaises(Problem): configuration(state)
        config_file.chmod(0o600)
        self.assertEqual(configuration(state)['model'], 'test-fixture')
        with patch('help_service.server.__file__', '/opt/llmpsych-sites/llp-web-help/releases/' + 'b' * 40 + '/help_service/server.py'):
            self.assertEqual(release_sha(), 'b' * 40)
        self.assertEqual(release_sha(), 'development')


if __name__ == '__main__':
    unittest.main()
