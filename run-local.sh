#!/usr/bin/env bash
# Mac/Linux: one local Python venv; no Docker, Kubernetes, Ollama, CUDA or cloud accounts.
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  command -v python3 >/dev/null || { echo 'Python 3.10+ is required. Install Python from python.org.'; exit 1; }
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/run_local_demo.py
if [[ "${1:-}" == '--check-only' ]]; then
  exit 0
fi
printf '\nOpen this browser URL: http://127.0.0.1:8000/dashboard\n'
printf 'Press Ctrl+C to stop the local app.\n\n'
exec python -m agent_quality_lab serve --host 127.0.0.1 --port 8000
