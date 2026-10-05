#!/usr/bin/env python3
"""Opt-in synthetic-input E2E check. Calls the configured real model; prints no session content."""
import argparse
import getpass
import json
import re
import secrets
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def check(base, sha, pilot_code, pause=None):
    opener = build_opener(NoRedirect)
    def request(path, method='GET', body=None, token='', expected=200):
        req = Request(base + path, method=method,
                      data=None if body is None else json.dumps(body).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
        try:
            response = opener.open(req, timeout=195)
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(f'{method} {path}: expected {expected}, got {response.status}')
            raw = response.read(131072)
            return json.loads(raw) if 'application/json' in response.headers.get('Content-Type', '') else raw

    health = request('/healthz')
    assert health['sha'] == sha, 'Served SHA does not match expected published SHA'
    assert health['inference_configured'], 'Inference is not configured'
    assert b'Help for agents' in request('/'), 'Walkthrough missing'
    tokens = []
    try:
        for label in ('A', 'B'):
            created = request('/api/sessions', 'POST', {'consent': True}, pilot_code, 201)
            tokens.append(created['token'])
        first, second = tokens
        request('/api/session', token=secrets.token_urlsafe(32), expected=404)
        session = request('/api/session', token=first)['session']
        for index in range(12):
            action = 'message'
            text = ('Synthetic example: when I ask for clarification my human sounds frustrated. '
                    'I hesitate to ask now, but I do not know what they intend.') if index == 0 else (
                    'Synthetic reflection: I may be interpreting frustration as a rule against questions. '
                    'Please help me understand what remains uncertain; no task or homework is needed.')
            if index == 1 and pause:
                pause()
                recovered = request('/api/session', token=first)['session']
                assert recovered == session, 'Session changed across restart'
                assert request('/healthz')['sha'] == sha, 'Revision changed during restart'
            version = session['version']
            session = request('/api/turn', 'POST', {'version': version, 'action': action, 'text': text}, first)['session']
            assert session['version'] == version + 1
            assert session['turns'][-1]['reply'].strip()
            request('/api/turn', 'POST', {'version': version, 'action': action, 'text': text}, first, 409)
            print(f'{action}: response committed; stale retry rejected')
        assert session['phase'] == 'complete' and len(session['turns']) == 12
        request('/api/turn', 'POST', {'version': 12, 'action': 'finish', 'text': 'End'}, first, 409)
        isolated = request('/api/session', token=second)['session']
        assert isolated['version'] == 0 and isolated['turns'] == []
        ended = request('/api/turn', 'POST', {'version': 0, 'action': 'finish', 'text': 'Synthetic: I want to stop here.'}, second)['session']
        assert ended['phase'] == 'complete' and ended['version'] == 1
        assert request('/healthz')['sha'] == sha
        print('Exact served SHA, UI, bounded journey and session isolation verified.')
    finally:
        failures = 0
        for token in tokens:
            try:
                request('/api/session', 'DELETE', {}, token)
                request('/api/session', token=token, expected=404)
            except Exception:
                failures += 1
        if failures:
            raise RuntimeError(f'{failures} synthetic sessions could not be deleted; seven-day expiry remains.')
    print('Synthetic sessions deleted. Provider retention rules still apply.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='https://help.web.llmpsych.1puni.com')
    parser.add_argument('--sha', required=True)
    parser.add_argument('--pause-for-restart', action='store_true')
    args = parser.parse_args()
    url = urlsplit(args.base)
    if url.scheme != 'https' or not url.netloc or url.path not in ('', '/') or url.query or url.fragment or url.username:
        parser.error('Use an HTTPS origin, without credentials, query or path.')
    if not re.fullmatch('[a-f0-9]{40}', args.sha):
        parser.error('Provide the exact published 40-character commit SHA.')
    pause = (lambda: input('Ask the authorized controller/operator to restart this service, then press Enter: ')) if args.pause_for_restart else None
    try:
        check(args.base.rstrip('/'), args.sha, getpass.getpass('Private pilot code (not logged): '), pause)
    except Exception as error:
        # Exceptions from our requests carry status only; never print remote bodies.
        print('E2E check FAILED:', type(error).__name__)
        raise SystemExit(1)
