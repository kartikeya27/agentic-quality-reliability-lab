"""Actual localhost HTTP wiring for Ollama + NIM adapters with synthetic servers.

These are *test doubles*. They prove request/response wiring, not accelerator service or
Ollama model execution. A real live model is required for verification profiles.
"""
import json
import os
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from agent_quality_lab.llm import ModelClient


class Handler(BaseHTTPRequestHandler):
    requests_seen = []

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(length))
        self.requests_seen.append({'path': self.path, 'model': body.get('model'),
                                   'authorized': self.headers.get('Authorization') == 'Bearer test-token'})
        response_text = json.dumps({'category': 'database', 'severity': 'high'})
        if self.path == '/api/chat':
            response = {'message': {'content': response_text}}
        elif self.path == '/v1/chat/completions':
            response = {'choices': [{'message': {'content': response_text}}]}
        else:
            self.send_error(404)
            return
        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        return


@contextmanager
def mock_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_address[1]}'
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def run() -> dict:
    Handler.requests_seen = []
    with mock_server() as base:
        with patch.dict(os.environ, {'AQ_OLLAMA_URL': base, 'AQ_MODEL': 'synthetic-ollama'}):
            a = ModelClient('ollama').complete_json('Database query failed')
        with patch.dict(os.environ, {'AQ_NIM_BASE_URL': base + '/v1',
                                      'AQ_NIM_API_KEY': 'test-token', 'AQ_NIM_MODEL': 'synthetic/nim'}):
            b = ModelClient('nim').complete_json('Database query failed')
    checks = {
        'ollama_http_request_parsed': a == {'category': 'database', 'severity': 'high'},
        'nim_http_request_parsed': b == {'category': 'database', 'severity': 'high'},
        'ollama_endpoint_correct': Handler.requests_seen[0]['path'] == '/api/chat',
        'nim_endpoint_correct': Handler.requests_seen[1]['path'] == '/v1/chat/completions',
        'nim_token_sent_to_mock_only': Handler.requests_seen[1]['authorized'],
    }
    return {'checks': checks, 'verified': all(checks.values()),
            'scope': 'Real loopback HTTP to synthetic test doubles; no live Ollama/NIM, no GPU',
            'calls': Handler.requests_seen}


if __name__ == '__main__':
    report = run()
    out = Path('artifacts/backend-http-contract.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if not report['verified']:
        raise SystemExit('Backend HTTP adapter contract failed')
