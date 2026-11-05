"""Spin up a REAL local uvicorn process and verify API contract/Prometheus exposition."""
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


def verify_api() -> dict:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, AQ_MODE='deterministic', AQ_ENABLE_FAULTS='0', AQ_ARTIFACT_DIR='artifacts')
    process = subprocess.Popen([sys.executable, '-m', 'agent_quality_lab', 'serve', '--port', str(port)],
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f'http://127.0.0.1:{port}'
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError('uvicorn exited before startup')
            try:
                health = httpx.get(url + '/api/health', timeout=2)
                if health.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError('uvicorn HTTP health check timed out')
        response = httpx.post(url + '/api/triage', json={'incident_id':'VERIFY-HTTP', 'message':'Database query failed'}, timeout=5)
        response.raise_for_status()
        metrics = httpx.get(url + '/metrics', timeout=5)
        metrics.raise_for_status()
        dashboard = httpx.get(url + '/dashboard', timeout=5)
        dashboard.raise_for_status()
        evidence = httpx.get(url + '/api/evidence', timeout=5)
        evidence.raise_for_status()
        checks = {
            'browser_dashboard_real_http': 'Local Quality Dashboard' in dashboard.text,
            'dashboard_claims_no_grafana': 'not Grafana' in dashboard.text,
            'evidence_endpoint_real_http': evidence.json().get('scope', '').startswith('Real local Python'),
            'real_http_server_started': health.json()['status'] == 'ok',
            'post_triage_contract': response.json()['runbook_id'] == 'RB-DATABASE-02',
            'prometheus_metrics_http': 'aq_triage_requests_total' in metrics.text and 'aq_qa_pass_ratio' in metrics.text,
            'inference_was_not_faked': response.json()['model_used'] is False,
        }
        return {'generated_at':datetime.now(timezone.utc).isoformat(), 'checks': checks, 'verified':all(checks.values()),
                'scope':'actual local Python FastAPI/uvicorn HTTP, not Docker/Kubernetes/accelerator inference'}
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()


if __name__ == '__main__':
    p=Path('artifacts/api-http-report.json')
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        report=verify_api()
    except Exception as exc:
        report={'verified':False,'reason':f'{type(exc).__name__}: {exc}'}
    p.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not report['verified']:
        raise SystemExit('Local HTTP integration FAILED')
