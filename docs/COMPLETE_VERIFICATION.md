# Complete integration verification guide

The default demonstration is **Docker-first** on macOS with Docker Desktop already running. Real model inference, Kubernetes experiments, and hardware-dependent checks are separate optional extensions. No remote service is automatically contacted by the default launcher.

## What runs immediately on your Mac

```bash
cd ~/Downloads/agentic-quality-reliability-lab
docker info
bash start-docker.sh
cat artifacts/docker-stack-report.json
```

A successful report requires `verified: true` plus all individual checks true: FastAPI health/triage, real Prometheus scrape, and Grafana provisioned data source/dashboard. Do not confuse source files or mocked HTTP requests with this live result. If something fails:

```bash
docker compose ps
docker compose logs --tail=100 app prometheus grafana
```

Stop everything with `docker compose down`. The services bind only to localhost on ports 8000, 9090, and 3000.

## Optional extra checks

| System | Verify | Needed on execution host | Evidence |
| --- | --- | --- | --- |
| Kubernetes kind | `make verify-kind` | Docker Desktop, `kind`, `kubectl` | `artifacts/k8s/kind-verification.json` |
| Ollama model | `make verify-ollama` | Installed Ollama, downloaded model | `artifacts/ollama-readiness.json`, evaluation |
| NIM inference | `make verify-nim` | Authorized deployed endpoint, model, access | `artifacts/nim-readiness.json` |
| NeMo Guardrails | `make verify-nemo` | SDK and running local Ollama | `artifacts/nemo-live-smoke.json` |
| KWOK | `make verify-kwok` | Docker, `kwokctl`, `kubectl` | `artifacts/kwok/kwok-report.json` |
| Accelerator GPU | `make verify-gpu` | Compatible GPU Linux host and local inference service | `artifacts/gpu-residency-report.json` |
| Remote CI | `make verify-ci` | Repository pushed to GitHub, workflow run | `artifacts/github-actions-report.json` |
| Human QA productivity | `make productivity-template`, then `make productivity-report` | Real timed paired QA tasks | `artifacts/qa-productivity-report.json` |

### Real local inference without paid services

Ollama is the simplest optional model runtime for Apple Silicon. If you already have it installed, start Ollama and run:

```bash
ollama pull llama3.2:1b
make verify-ollama
```

The deterministic default is not a model benchmark. The real-model verifier rejects silent fallback.

### Authorized NIM-compatible endpoint

Do not use a hosted model without authorization. If you have an actual NIM service, set its documented API base URL and model identifier. Use HTTPS for non-local endpoints. For example:

```bash
export AQ_NIM_BASE_URL='https://YOUR_AUTHORIZED_MODEL_HOST/v1'
export AQ_NIM_MODEL='YOUR_DEPLOYED_MODEL_ID'
export AQ_NIM_AUTHORIZED=1
# Set AQ_NIM_API_KEY securely if this endpoint requires a token.
make verify-nim
```

This checks actual requests and outputs; the service's identity is provided by the operator and is not proven by an OpenAI-compatible JSON response alone. No API key is saved to the result files.

### NeMo guardrails

```bash
python -m pip install -e '.[nemo]'
make verify-nemo
```

This requires a real local inference service. SDK invocation does not establish overall safety or policy accuracy; review false acceptances and false rejections.

### GPU caveat

Apple Silicon does not run CUDA workloads. The hardware-provenance check is optional and requires a compatible accelerator host. Do not label a hosted inference result as proof of local GPU execution. See [GPU host runbook](GPU_HOST_RUNBOOK.md).

### Final audit

```bash
make audit-integrations
cat artifacts/integration-audit.json
```

`VERIFIED` means a real check passed, `BLOCKED` means a prerequisite was absent, and `FAILED` means a check ran unsuccessfully. The project never treats missing infrastructure as success. The real human productivity protocol is documented in [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md).
