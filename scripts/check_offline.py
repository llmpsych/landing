"""Bounded publication gate; standard library only, no live provider access."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def offline_audit(event, args):
    # Fail closed on outbound sockets, including accidental provider calls in tests.
    if event in {'socket.connect', 'socket.bind', 'socket.getaddrinfo'}:
        address = args[1] if event != 'socket.getaddrinfo' else (args[0],)
        if not isinstance(address, tuple) or address[0] not in {'127.0.0.1', '::1', 'localhost'}:
            raise RuntimeError('Offline gate forbids non-loopback networking')
    if event == 'socket.sendto':
        raise RuntimeError('Offline gate forbids datagrams')


def main():
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError('Publication gate requires Python 3.14')
    if sys.argv[1:] == ['--tests']:
        sys.path.insert(0, str(ROOT))
        sys.addaudithook(offline_audit)
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
        if suite.countTestCases() == 0:
            raise RuntimeError('No tests discovered')
        return not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
    if sys.argv[1:]:
        raise RuntimeError('Usage: python3.14 -I scripts/check_offline.py')
    # No controller/provider environment, user Python packages, NODE_OPTIONS or proxies.
    with tempfile.TemporaryDirectory(prefix='landing-gate-') as temporary:
        env = {'PATH': os.defpath, 'HOME': temporary, 'TMPDIR': temporary,
               'LANG': 'C.UTF-8', 'TZ': 'UTC'}
        commands = [
            [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--tests'],
            ['node', '--check', 'help_service/web/app.js'],
        ]
        for command in commands:
            print('+ ' + ' '.join(command), flush=True)
            subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=90)
    print('Offline publication checks passed (no live inference or clinical validation).')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f'Offline publication check failed: {error}', file=sys.stderr)
        sys.exit(1)
