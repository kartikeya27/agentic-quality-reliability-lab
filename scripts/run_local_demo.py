#!/usr/bin/env python3
"""One-command, localhost-only QA proof. No Docker/Ollama/Kubernetes/accelerator account.

External platform scripts are preserved, never run by this command. This is an
offline demo, not evidence of a production accelerator model or actual Grafana/KWOK.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'

PLATFORMS = {
    'docker_prometheus_grafana': ('docker-compose.yml', 'observability/prometheus.yml', 'observability/grafana/dashboards/agent-quality.json', 'scripts/verify_docker_stack.sh'),
    'kubernetes_kind': ('k8s/deployment.yaml', 'scripts/verify_k8s_kind.sh'),
    'ollama': ('src/agent_quality_lab/llm.py', 'scripts/verify_ollama_live.sh'),
    'nim': ('src/agent_quality_lab/llm.py', 'scripts/verify_nim_live.sh'),
    'nemo_guardrails': ('nemo/guardrails/config.yml', 'scripts/verify_nemo_live.sh'),
    'kwok': ('scripts/kwok_failure_experiment.sh',),
    'gpu': ('scripts/verify_gpu_nim.sh', 'scripts/verify_gpu_residency.py'),
    'github_actions': ('.github/workflows/quality.yml', '.github/workflows/model-inference-manual.yml'),
    'qa_productivity': ('scripts/productivity_experiment.py', 'docs/EXPERIMENT_PROTOCOL.md'),
}


def call(name: str, command: list[str], env: dict) -> dict:
    print(f'\n▶ {name}: {" ".join(command)}', flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    (ART / f'local-demo-{name}.log').write_text(result.stdout[-30000:] + '\n=== STDERR ===\n' + result.stderr[-12000:])
    print((result.stdout + '\n' + result.stderr)[-2200:], flush=True)
    return {'status': 'VERIFIED_OFFLINE' if result.returncode == 0 else 'FAILED',
            'return_code': result.returncode, 'log': f'artifacts/local-demo-{name}.log'}


def read(name: str) -> dict:
    try:
        return json.loads((ART / name).read_text())
    except (FileNotFoundError, ValueError):
        return {}


def main() -> int:
    ART.mkdir(exist_ok=True)
    (ART / 'local-demo-report.json').unlink(missing_ok=True)
    env = dict(os.environ, AQ_MODE='deterministic', AQ_ENABLE_FAULTS='0')
    proof = {'generated_at': datetime.now(timezone.utc).isoformat(),
             'scope': 'Host-local Python tests and localhost HTTP. No external services used.',
             'checks': {}, 'platform_files': {}, 'external_verified': False}
    for platform, paths in PLATFORMS.items():
        proof['platform_files'][platform] = {'included': all((ROOT / p).is_file() for p in paths),
                                             'evidence_level': 'SOURCE_FILES_ONLY_NOT_LIVE_VERIFICATION'}
    steps = [
        ('offline', ['bash', 'scripts/verify_local.sh']),
        ('simulations', [sys.executable, 'scripts/verify_local_simulations.py']),
        ('gpu_detection', [sys.executable, '-m', 'agent_quality_lab', 'gpu-diag']),
        ('external_preflight_only', [sys.executable, 'scripts/audit_integrations.py', '--preflight-only']),
    ]
    for name, command in steps:
        proof['checks'][name] = call(name, command, env)
        if name == 'offline' and proof['checks'][name]['status'] == 'FAILED':
            break
    if not (ART / 'productivity-observations.csv').exists():
        proof['checks']['productivity_template'] = call('productivity_template', [sys.executable, 'scripts/productivity_experiment.py', '--template'], env)
    else:
        proof['checks']['productivity_template'] = {'status': 'PRESERVED', 'note': 'Existing user observations not overwritten'}

    eq = read('eval-report.json').get('summary', {})
    policy = read('local-policy-fixtures.json')
    sched = read('local-scheduling-simulation.json')
    trace = read('requirements-traceability.json')
    backend = read('backend-http-contract.json')
    proof['evidence'] = {
        'golden_pass_rate': eq.get('pass_rate'), 'model_used_rate': eq.get('model_used_rate'),
        'local_policy_fixtures_passed': policy.get('all_passed'), 'synthetic_node_reschedule_passed': sched.get('passed'),
        'traceability_passed': trace.get('offline_gate_passed'),
        'localhost_model_adapter_contract_passed': backend.get('verified'),
    }
    gate_ok = (proof['checks'].get('offline', {}).get('return_code') == 0 and
               proof['checks'].get('simulations', {}).get('return_code') == 0 and
               all(p['included'] for p in proof['platform_files'].values()) and
               trace.get('offline_gate_passed') is True and backend.get('verified') is True and
               eq.get('model_used_rate') == 0)
    proof['overall'] = 'VERIFIED_OFFLINE' if gate_ok else 'FAILED'
    proof['important_limitations'] = [
        'Local dashboard is not Grafana; /metrics is Prometheus exposition, not a Prometheus server.',
        'Mocked Ollama/NIM HTTP contract tests do not run a model.',
        'Static rule checks are not execution of NeMo Guardrails SDK.',
        'Virtual node-loss example is not a KWOK/Kubernetes cluster.',
        'accelerator GPU requires an actual accelerator GPU host; cannot be emulated as hardware proof.',
        'GitHub Actions files are included, but remote success requires a pushed repository.',
        'QA productivity improvement requires real manual versus model-assisted human timing data.',
    ]
    (ART / 'local-demo-report.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('\n' + '='*55 + f'\nLOCAL DEMO: {proof["overall"]}\nSee artifacts/local-demo-report.json\n' + '='*55)
    return 0 if gate_ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
