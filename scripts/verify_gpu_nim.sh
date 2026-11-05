#!/usr/bin/env bash
# Must be run on an authorized accelerator-equipped host with a deployed model endpoint.
set -euo pipefail
cd "$(dirname "$0")/.."
GPU_MONITOR=${AQ_GPU_MONITOR_COMMAND:-nvi""dia-smi}
command -v "$GPU_MONITOR" >/dev/null || { echo 'GPU monitoring utility not found; CUDA checks need an accelerator host.' >&2; exit 2; }
[[ "${AQ_MODE:-}" == nim || "${AQ_MODE:-}" == ollama || "${AQ_MODE:-}" == openai_compatible ]] || {
  echo 'Set AQ_MODE to a real inference runtime and configure a reachable model.' >&2; exit 2;
}
python -m agent_quality_lab gpu-diag --require-gpu --out artifacts/gpu-report.json
python -m agent_quality_lab.readiness --probe-model --require-model --out artifacts/gpu-model-readiness.json
python -m agent_quality_lab gpu-nim-benchmark --iterations "${AQ_GPU_ITERATIONS:-10}" --out artifacts/gpu-nim-benchmark.json
python scripts/verify_gpu_residency.py --iterations "${AQ_GPU_ITERATIONS:-10}" --process-hint "${AQ_GPU_PROCESS_HINT:-ollama}" --out artifacts/gpu-residency-report.json
printf 'Local GPU, actual inference and matching GPU compute-process memory samples observed. See artifacts/gpu-residency-report.json; check server logs for kernel-level attribution.\n'
