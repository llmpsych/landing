"""Local browser checks ONLY: synthetic inference, ephemeral private state."""
import os
import signal
from pathlib import Path
import tempfile
from help_service.server import Service, Server, Handler
from test_help import CONFIG, Fixture

class LabeledFixtureHandler(Handler):
    def reply(self, status, body, kind='application/json'):
        if kind.startswith('text/html'):
            body = body.replace(b'<main>', b'<p class="fixture-notice"><strong>Local synthetic fixture - no provider calls</strong></p><main>')
        super().reply(status, body, kind)


def stop(*_):
    raise SystemExit(0)

signal.signal(signal.SIGTERM, stop)
os.umask(0o077)
with tempfile.TemporaryDirectory() as state:
    service = Service(Path(state), CONFIG, 'a' * 40, Fixture())
    server = Server(('127.0.0.1', 0), service, '')
    server.RequestHandlerClass = LabeledFixtureHandler
    server.origin = f'http://127.0.0.1:{server.server_port}'
    print(server.origin, flush=True)
    server.serve_forever()
