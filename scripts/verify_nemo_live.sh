#!/usr/bin/env bash
# Real NeMo Guardrails SDK call using locally configured Ollama; requires optional extra.
set -euo pipefail
cd "$(dirname "$0")/.."
export AQ_MODE=ollama
export AQ_MODEL="${AQ_MODEL:-llama3.2:1b}"
command -v ollama >/dev/null || { echo 'ollama is not installed' >&2; exit 2; }
python -c 'import nemoguardrails' || { echo "Install NeMo optional dependency: python -m pip install -e '.[nemo]'" >&2; exit 2; }
ollama list | grep -Fq "$AQ_MODEL" || { echo "Pull the model: ollama pull $AQ_MODEL" >&2; exit 2; }
python -m agent_quality_lab.readiness --probe-model --require-model --out artifacts/nemo-ollama-readiness.json
python -m agent_quality_lab nemo-smoke --out artifacts/nemo-live-smoke.json
python -m agent_quality_lab nemo-policy-eval --out artifacts/nemo-policy-eval.json
printf 'NeMo SDK + local model responses executed; policy result uses refusal-string heuristics and requires human review.\n'
