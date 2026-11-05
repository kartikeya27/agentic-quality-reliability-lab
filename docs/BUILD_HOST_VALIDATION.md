# Reproducible offline verification evidence

The repository's standard local-first command is `bash run-local.sh --check-only` (or `make demo-check` after installing the Python package). It writes `artifacts/local-demo-report.json` on the machine where it is executed.

## Build-host observations

An independent Linux x86_64 environment with Python 3.13 executed the current project and observed:

- **64 passing automated Pytest checks**.
- **16 of 16** offline golden evaluation cases passing, with `model_used_rate = 0.0` (deterministic baseline).
- **8 of 8** advanced offline evaluation cases passing.
- **18 of 18** offline requirement-to-executed-test traceability entries passing.
- A real loopback FastAPI process with successful `/api/health`, `/api/triage`, `/metrics`, `/dashboard`, and `/api/evidence` HTTP checks.
- **4 of 4** local static guardrail policy fixtures passing; not NeMo Guardrails SDK execution.
- A successful toy Python virtual-node failure/rescheduling simulation; not KWOK execution.
- Local NIM/Ollama HTTP protocol contract tests against synthetic servers; no actual model used.
- Explicit preflight showing Docker, Kubernetes, KWOK, Ollama, NIM and accelerator GPU were **not verified** in this environment.

These observations do **not** mean the user's Mac has completed the checks. The project does **not** claim any CUDA benchmark, production AI quality score, human QA productivity improvement, or successful external runtime execution without real corresponding evidence.

Sample machine-generated summary: [examples/build_host_offline_evidence.json](../examples/build_host_offline_evidence.json). For a live Mac result, run the local launcher and inspect `artifacts/local-demo-report.json`.
