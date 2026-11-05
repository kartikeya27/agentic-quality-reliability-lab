# 10-minute accelerator-aligned live demonstration

**What this proves:** engineering a multi-layer quality/reliability harness for a toy incident-triage agent. **What it does not prove:** a accelerator production deployment, CUDA expertise, verified NIM runtime, or real organizational time savings.

## Start the no-cloud interview demonstration

```bash
bash run-local.sh
```

Show **http://127.0.0.1:8000/dashboard** first: the real local API, Prometheus-format `/metrics`, golden/advanced results, requirement traceability and nine honest platform-verification statuses. This dashboard runs without Docker and is **not Grafana**. Toggle to `/docs` for FastAPI contracts and enter a synthetic incident. The remaining original live accelerator/KWOK experiments are *optional* and should never be described as executed unless their real reports pass.

## Minute 0–1: architecture

Show `README.md`: a synthetic incident enters a typed agent; a deterministic or opt-in LLM decision is checked, a read-only runbook tool is called, a trace and telemetry are written, and a failure uses a visible safe fallback. The `mode`, `model_used`, and `fallback_used` fields prevent false confidence.

## Minute 1–3: layered test harness

```bash
python -m pytest -q
python -m agent_quality_lab eval
python -m agent_quality_lab advanced --repeats 3
```

Open `artifacts/eval-report.md` and `artifacts/advanced-report.json`. Explain goldens, negative inputs, prompt-injection attempts, three repeated passes per case, runbook attribution, tool trace correctness, and explicitly scoped limits of hallucination detection.

## Minute 3–4: failure injection

```bash
python -m agent_quality_lab chaos
python -m agent_quality_lab inference-chaos
cat artifacts/inference-chaos-report.json
```

Describe simulated tool timeout/error/latency and simulated NIM upstream 503, network timeout and invalid model schema. Confirm the agent logs a fallback rather than counting the rules baseline as model inference.

## Minute 4–5: flaky detection and test optimization

```bash
python -m agent_quality_lab flaky
python -m agent_quality_lab select --budget 6
python -m agent_quality_lab efficiency --budget 6
```

Point out empirical execution time and test count reduction; explain that tags, not source code branches, define selection coverage, and reduced test sets can miss regressions. Do not call the measured change an "AI-generated improvement".

## Minute 5–7: service + observability

```bash
python -m agent_quality_lab serve
```

Open `/docs`, then from another terminal run `python -m agent_quality_lab load`. With Docker, show the extended Grafana dashboard with p95/p99 latency, flaky tests, regression count, pass rate and risk-tag coverage. If panels say "No data", show how a corresponding report is generated and explain why missing data should not appear as zero.

## Minute 7–8: NeMo and NIM pathways

Point to `nemo/guardrails/config.yml`, `nemo_adapter.py`, and `tests/test_nim_nemo_contracts.py`. Explain the split between local mocked protocol tests and *optional* actual NeMo SDK/NIM endpoint commands in `docs/COMPLETE_VERIFICATION.md`. If an Ollama model is available, show `model-experiment` and `nemo-smoke` live; otherwise describe them as unverified optional integrations.

## Minute 8–9: failure at simulated Kubernetes scale

Show `scripts/kwok_failure_experiment.sh`, its isolation precautions and the sample sequence: four virtual nodes, 60 fake pods, delete one node, explicitly remove affected fake pods, scale up to 63, collect scheduler state. If KWOK is not installed, do not claim to have run it. Emphasize no containers are executed in KWOK.

## Minute 9–10: risks and engineering ownership

Outline what you'd add to production: approved GPU cluster, NIM server-side DCGM telemetry, real fault domains, auth/TLS and secret management, load test governance, chaos test guardrails, labeled datasets reviewed by product SMEs, and trend-based regression policies.

**Closing line:** "I built a reproducible AI-agent QA lab that validates correctness, tool attribution, adversarial behavior, inference fallbacks and regression risk. The default CI path is deterministic and falsifiable. The real model, NeMo, KWOK and accelerator GPU layers are separately enabled and gated rather than simulated as successes." 
