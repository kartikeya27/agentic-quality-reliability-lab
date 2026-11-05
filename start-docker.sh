#!/usr/bin/env bash
# Docker-first local demonstration for macOS Apple Silicon and other Docker hosts.
# Docker Desktop is expected to be installed and started by the operator.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo 'Docker CLI not available. Start Docker Desktop or use: bash run-local.sh' >&2
  exit 2
fi
if ! docker info >/dev/null 2>&1; then
  echo 'Docker Desktop is not ready. Open Docker Desktop and confirm `docker info` succeeds.' >&2
  exit 2
fi
if ! docker compose version >/dev/null 2>&1; then
  echo 'Docker Compose plugin not found. Update Docker Desktop.' >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.10+ is needed for host-side QA verification. Use python.org or Homebrew.' >&2
  exit 2
fi
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install -e '.[dev]'

printf '\n[1/3] Python quality gates\n'
python -m pytest -q
printf '\n[2/3] Docker image build, monitoring services, live HTTP verification\n'
bash scripts/verify_docker_stack.sh
printf '\n[3/3] Actual endpoint summary\n'
python - <<'PY'
import json
from pathlib import Path
p=Path('artifacts/docker-stack-report.json')
d=json.loads(p.read_text())
print('Docker stack verification:', 'PASS' if d.get('verified') is True else 'FAIL')
for name, ok in d.get('checks',{}).items(): print(f'  {"PASS" if ok else "FAIL"}: {name}')
PY
printf '\nApp / API:    http://127.0.0.1:8000/docs\n'
printf 'QA dashboard: http://127.0.0.1:8000/dashboard\n'
printf 'Prometheus:   http://127.0.0.1:9090/targets\n'
printf 'Grafana:      http://127.0.0.1:3000\n'
printf '\nStop later with: docker compose down\n'
