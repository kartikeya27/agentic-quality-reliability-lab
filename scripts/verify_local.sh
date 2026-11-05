#!/usr/bin/env bash
# Safe default: all tests are deterministic and require no external model or Docker.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts
python -m agent_quality_lab.readiness --out artifacts/readiness-report.json
python -m pytest -q --cov=agent_quality_lab --cov-report=term-missing --cov-report=json:artifacts/coverage.json --junitxml=artifacts/pytest-results.xml
python -m agent_quality_lab eval --min-pass-rate 1.0
python -m agent_quality_lab advanced --min-pass-rate 1.0
python -m agent_quality_lab chaos
python -m agent_quality_lab inference-chaos
python -m agent_quality_lab flaky
python -m agent_quality_lab select --budget 6
python -m agent_quality_lab efficiency --budget 6
python -m agent_quality_lab mutation --budget 6
python scripts/verify_api_http.py
python scripts/verify_backend_http_contract.py
python scripts/verify_perf_slo.py
python -m agent_quality_lab bug-cycle
python -m agent_quality_lab traceability
printf '\nOFFLINE EVIDENCE VERIFIED. Files saved in artifacts/.\n'
