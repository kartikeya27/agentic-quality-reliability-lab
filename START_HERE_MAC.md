# Agentic Quality & Reliability Lab — macOS setup

This repository demonstrates AI-agent testing, regression selection, synthetic fault injection, quality reporting, and observability. It uses synthetic data only. Its brand-neutral title and documentation are appropriate for a public engineering portfolio.

## Recommended: Docker Desktop already running

You only need **Docker Desktop** and **Python 3.10+** for this setup. Docker Compose is bundled with recent Docker Desktop installations. You do **not** need to install Prometheus or Grafana separately: their services are created from the Compose configuration. There is no need to install Kubernetes, an AI model runtime, or GPU drivers for the core demonstration.

1. Download and extract `agentic-quality-reliability-lab.zip` (it creates the `agentic-quality-reliability-lab` folder).
2. Open Terminal and check that Docker is ready:

```bash
docker info
docker compose version
python3 --version
```

3. Enter the extracted folder and run the complete setup:

```bash
cd ~/Downloads/agentic-quality-reliability-lab
bash start-docker.sh
```

The script creates `.venv`, installs the Python QA dependencies, runs automated tests, builds the app image, launches three local containers, generates QA reports, and waits for **real HTTP responses** proving app health, Prometheus scraping, and provisioned Grafana panels. All endpoints bind to `127.0.0.1`.

| Service | Local browser URL |
| --- | --- |
| Interactive QA dashboard | http://127.0.0.1:8000/dashboard |
| FastAPI API documentation | http://127.0.0.1:8000/docs |
| Prometheus target status | http://127.0.0.1:9090/targets |
| Grafana dashboard | http://127.0.0.1:3000 |

Check `artifacts/docker-stack-report.json`. The top-level `verified` field must be `true`, and every `checks` entry must also be `true`. If you see `false`, the script exits without claiming verification.

### Common Docker issues

- **Port 8000 already allocated:** Stop a Python server previously started with `bash run-local.sh`. Check with `lsof -nP -iTCP:8000 -sTCP:LISTEN`; then retry `bash start-docker.sh`.
- **Ports 3000 or 9090 occupied:** Use `lsof` with the relevant port to locate an existing service. Stop the conflict or change the `127.0.0.1` port mapping in `docker-compose.yml` and matching URLs in `scripts/verify_stack_http.py`.
- **Container unavailable:** Run `docker compose ps` and `docker compose logs --tail=100 app prometheus grafana`.
- **Grafana dashboard empty:** Generate traffic with `python -m agent_quality_lab load --requests 30 --concurrency 5`, allow a couple of scrape intervals, and refresh the browser. The first scrape can take several seconds.
- **Mac memory limits:** Docker Desktop should have enough RAM allocated for the API, Prometheus, and Grafana. Start with at least 4 GB available to Docker if performance is poor.

To stop the containers:

```bash
docker compose down
```

## Python-only fallback (no Docker required)

```bash
cd ~/Downloads/agentic-quality-reliability-lab
bash run-local.sh
```

This fallback still runs real tests and serves the built-in dashboard, but it does not launch real Prometheus or Grafana services. Use `bash run-local.sh --check-only` to produce reports without starting the web server.

## Optional advanced experiments

The core demo does not need these. If you already have the corresponding runtime, you can execute them separately without modifying the Docker setup:

| Capability | Command | What it proves |
| --- | --- | --- |
| Real local model via Ollama | `make verify-ollama` | Actual model response, not deterministic fallback; requires an Ollama model |
| Kubernetes `kind` | `make verify-kind` | Real containerized pod deployment and replacement; requires kind and kubectl |
| KWOK simulated node loss | `make verify-kwok` | Control-plane behavior; requires kwokctl and kubectl |
| NeMo Guardrails | `make verify-nemo` | Real SDK interaction; requires SDK and local model |
| Authorized NIM endpoint | `make verify-nim` | Actual model API calls; requires configured accessible inference service |
| Accelerator GPU sample | `make verify-gpu` | Only on compatible accelerator hardware; Apple M1 cannot run CUDA |
| GitHub Actions | Push repository | Remote CI execution on the pushed commit |
| Real QA productivity | `make productivity-template` | Records paired real human tasks before making efficiency claims |

The scripts do **not** pretend that unavailable hardware or model services passed. See [complete verification details](docs/COMPLETE_VERIFICATION.md), [requirement traceability](docs/AI_AGENT_REQUIREMENTS.md), and [human measurement protocol](docs/EXPERIMENT_PROTOCOL.md).

**Evidence honesty:** Python and configuration checks can run in any environment, but Docker services, remote CI, actual model runtime, and GPU evidence must be collected where those systems run.
