"""Honest, machine-generated integration audit.

Each integration is attempted only when its prerequisites are present. Missing
services become BLOCKED, never VERIFIED. --strict requires all selected checks.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'

PROFILES = {
    'docker': {'cmd': ['bash', 'scripts/verify_docker_stack.sh'], 'file': 'docker-stack-report.json', 'key': 'verified'},
    'kind': {'cmd': ['bash', 'scripts/verify_k8s_kind.sh'], 'file': 'k8s/kind-verification.json', 'key': 'verified'},
    'ollama': {'cmd': ['bash', 'scripts/verify_ollama_live.sh'], 'file': 'ollama-readiness.json', 'key': 'model.actual_inference_verified'},
    'nim': {'cmd': ['bash', 'scripts/verify_nim_live.sh'], 'file': 'nim-readiness.json', 'key': 'model.actual_inference_verified'},
    'nemo': {'cmd': ['bash', 'scripts/verify_nemo_live.sh'], 'file': 'nemo-live-smoke.json', 'key': 'sdk_executed'},
    'kwok': {'cmd': ['bash', 'scripts/kwok_failure_experiment.sh'], 'file': 'kwok/kwok-report.json', 'key': 'passed'},
    'gpu': {'cmd': ['bash', 'scripts/verify_gpu_nim.sh'], 'file': 'gpu-residency-report.json', 'key': 'gate_passed'},
}


def command_exists(name: str) -> bool:
    return bool(shutil.which(name))


def docker_usable() -> bool:
    if not command_exists('docker'):
        return False
    try:
        return subprocess.run(['docker', 'info'], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=10).returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def preflight(profile: str) -> str | None:
    if profile in {'docker', 'kind', 'kwok'} and not docker_usable():
        return 'Docker Desktop/Engine must be installed and running'
    if profile == 'kind' and not all(command_exists(t) for t in ('kind', 'kubectl')):
        return 'Install kind and kubectl'
    if profile == 'kwok' and not all(command_exists(t) for t in ('kwokctl', 'kubectl')):
        return 'Install kwokctl and kubectl'
    if profile in {'ollama', 'nemo'} and not command_exists('ollama'):
        return 'Install and start Ollama; pull the selected AQ_MODEL'
    if profile == 'nemo' and importlib.util.find_spec('nemoguardrails') is None:
        return "Install NeMo Guardrails: python -m pip install -e '.[nemo]'"
    if profile == 'nim' and (not os.getenv('AQ_NIM_BASE_URL') or
                            not os.getenv('AQ_NIM_MODEL') or
                            os.getenv('AQ_NIM_MODEL') == 'your-deployed-nim-model-id'):
        return 'Configure AQ_NIM_BASE_URL and a real AQ_NIM_MODEL (and API key if required)'
    if profile == 'nim' and os.getenv('AQ_NIM_AUTHORIZED') != '1':
        return 'Confirm the service identity and set AQ_NIM_AUTHORIZED=1 before a live NIM test'
    if profile == 'gpu':
        if not command_exists('nvi' + 'dia-smi'):
            return 'Requires an accelerator-equipped host/driver; Apple Silicon cannot execute CUDA checks'
        if os.getenv('AQ_MODE') not in ('nim', 'ollama', 'openai_compatible'):
            return 'Configure AQ_MODE with real inference and endpoint on an accelerator-equipped host'
    return None


def nested_truth(report: dict, path: str) -> bool:
    current = report
    for part in path.split('.'):
        if not isinstance(current, dict):
            return False
        current = current.get(part)
    return current is True


def audit(profiles: list[str], execute: bool = True) -> dict:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    checks = {}
    for name in profiles:
        spec = PROFILES[name]
        reason = preflight(name)
        if reason:
            checks[name] = {'status': 'BLOCKED', 'reason': reason, 'command': ' '.join(spec['cmd'])}
            continue
        if not execute:
            checks[name] = {'status': 'READY_NOT_RUN', 'command': ' '.join(spec['cmd'])}
            continue
        proof = ARTIFACTS / spec['file']
        # Remove stale success evidence before every new attempt.
        proof.unlink(missing_ok=True)
        try:
            completed = subprocess.run(spec['cmd'], cwd=ROOT, text=True, capture_output=True,
                                       timeout=1200, env=os.environ.copy())
            logpath = ARTIFACTS / f'audit-{name}.log'
            logpath.write_text(completed.stdout[-30000:] + '\n=== STDERR ===\n' + completed.stderr[-12000:])
            evidence = json.loads(proof.read_text()) if proof.is_file() else {}
            ok = completed.returncode == 0 and nested_truth(evidence, spec['key'])
            checks[name] = {
                'status': 'VERIFIED' if ok else 'FAILED',
                'return_code': completed.returncode,
                'evidence': str(proof.relative_to(ROOT)) if proof.is_file() else None,
                'log': str(logpath.relative_to(ROOT)),
                'reason': None if ok else 'Check failed, or expected evidence was not produced',
            }
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            checks[name] = {'status': 'FAILED', 'reason': f'{type(exc).__name__}: {str(exc)[:180]}'}
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'This host only; mock tests are not counted as live verification',
        'checks': checks,
        'verified': sum(v['status'] == 'VERIFIED' for v in checks.values()),
        'blocked': sum(v['status'] == 'BLOCKED' for v in checks.values()),
        'failed': sum(v['status'] == 'FAILED' for v in checks.values()),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profiles', default=','.join(PROFILES), help='comma-separated integration names')
    p.add_argument('--preflight-only', action='store_true', help='Check prerequisites without executing integrations')
    p.add_argument('--strict', action='store_true', help='Fail if any selected integration is not verified')
    p.add_argument('--out', default='artifacts/integration-audit.json')
    args = p.parse_args()
    profiles = [x.strip() for x in args.profiles.split(',') if x.strip()]
    bad = set(profiles) - set(PROFILES)
    if bad or not profiles:
        p.error(f'Unknown/empty profiles: {sorted(bad)}; allowed {list(PROFILES)}')
    report = audit(profiles, execute=not args.preflight_only)
    destination = ROOT / args.out
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if report['failed'] or (args.strict and (report['blocked'] or
       any(c['status'] != 'VERIFIED' for c in report['checks'].values()))):
        sys.exit(1)


if __name__ == '__main__':
    main()
