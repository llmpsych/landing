"""Local browser checks ONLY: synthetic inference, ephemeral private state."""
import os
import signal
from pathlib import Path
import tempfile
from help_service.server import Service, Server
from test_help import CONFIG, Fixture

def stop(*_):
    raise SystemExit(0)

signal.signal(signal.SIGTERM, stop)
os.umask(0o077)
with tempfile.TemporaryDirectory() as state:
    service = Service(Path(state), CONFIG, 'a' * 40, Fixture())
    server = Server(('127.0.0.1', 0), service, '')
    server.origin = f'http://127.0.0.1:{server.server_port}'
    print(server.origin, flush=True)
    server.serve_forever()
