#!/usr/bin/env bash
# Actually sends requests to the selected local Ollama model, not a stub.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v ollama >/dev/null || { echo 'Install Ollama from https://ollama.com/download/mac' >&2; exit 2; }
MODEL="${AQ_MODEL:-llama3.2:1b}"
ollama list | grep -Fq "$MODEL" || { echo "Pull the model first: ollama pull $MODEL" >&2; exit 2; }
export AQ_MODE=ollama
export AQ_MODEL="$MODEL"
export AQ_OLLAMA_URL="${AQ_OLLAMA_URL:-http://127.0.0.1:11434}"
python -m agent_quality_lab.readiness --probe-model --require-model --out artifacts/ollama-readiness.json
# Zero minimum accuracy threshold is deliberate: report real quality without hiding poor results.
python -m agent_quality_lab eval --min-pass-rate 0 --require-model --out artifacts/ollama-eval.json
python -m agent_quality_lab advanced --min-pass-rate 0 --require-model --out artifacts/ollama-advanced.json
python -m agent_quality_lab model-experiment --out artifacts/ollama-vs-baseline.json
printf 'Real Ollama execution confirmed; inspect artifacts/ollama-*.json for measured quality.\n'
