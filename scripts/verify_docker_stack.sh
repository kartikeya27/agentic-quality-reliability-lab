#!/usr/bin/env bash
# Builds, starts, and probes real Docker services. Leaves them running for dashboard viewing.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Docker CLI missing.' >&2; exit 2; }
docker info >/dev/null || { echo 'Docker daemon is not running.' >&2; exit 2; }
mkdir -p artifacts
# This smoke checks the deterministic container stack; external LLM is verified separately.
export AQ_MODE=deterministic
docker compose config --quiet
python -m agent_quality_lab eval --out artifacts/eval-report.json
python -m agent_quality_lab advanced --out artifacts/advanced-report.json
python -m agent_quality_lab flaky
python -m agent_quality_lab select --budget 6
python -m agent_quality_lab efficiency --budget 6
python -m agent_quality_lab mutation --budget 6
docker compose up --build -d
python scripts/verify_stack_http.py --out artifacts/docker-stack-report.json
printf '\nDocker + Prometheus + Grafana integration verified. Open http://127.0.0.1:3000\n'
