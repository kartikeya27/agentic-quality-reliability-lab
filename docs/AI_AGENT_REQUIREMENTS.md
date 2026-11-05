# AI agent test engineering — requirement-to-evidence matrix

**Quick offline mode:** `bash run-local.sh` executes the local harness and serves a built-in browser dashboard. In this environment 65 Pytest checks passed. `scripts/verify_local_simulations.py` provides explicitly **non-NeMo** static policy fixtures and **non-KWOK** virtual scheduling; `scripts/verify_backend_http_contract.py` uses localhost inference test doubles. All nine real platform integration configurations remain in the repository; no platform is called live verified solely because its files exist. See [the local Mac guide](../START_HERE_MAC.md).

**Labels:** Implemented/offline verified = executed tests on this build host. Integration available = functional code and verifier exists, but its *real runtime is not proven on this host*. Candidate qualification = must be supported by real work history and education, not by a demo.

| Job requirement | Project implementation | Evidence or outstanding verification |
| --- | --- | --- |
| Use/develop AI-powered QA tools | `testgen.py`, `analysis.py`, `advanced_eval.py`, optional LLM proposals | Offline test suite; AI proposals require actual Ollama/NIM and human review |
| Test generation and flaky test analysis | `testgen.py`, `analysis.py`, `data/flaky_runs.jsonl` | Offline Pytest + generated case reports |
| Defect detection | `mutation_benchmark.py` and six controlled seeded faults | Offline mutation report; not a production defect-detection claim |
| Regression testing and test coverage optimization | `qa_benchmark.py`, risk-tag selector and coverage JSON | Risk-tag coverage != statement/branch code coverage |
| QA strategy, planning, cross-functional requirements | `data/requirements.json`, `requirements.py`, `docs/ARCHITECTURE.md` | 18 offline traceability entries; team collaboration cannot be proven with solo demo |
| Test plan, status, risks and reporting | requirements/quality JSON, `docs/DEFECT_LIFECYCLE.md` | Offline SLO gate, generated reports and dashboard panels |
| Functional/end-to-end agent workflows | `agent.py`, `api.py`, `tools.py`, Pytest API checks | Offline and real localhost HTTP tests |
| Performance, load, reliability | `performance.py`, `slo.py`, `scripts/verify_perf_slo.py` | Real local 30-request SLO test (not a load capacity benchmark) |
| Fault injection and recovery | `inference_chaos.py`, tool fault fixtures, kind and KWOK scripts | Offline fault fixtures verified; live kind/KWOK require runtimes |
| Scalable QA frameworks and agent test harness | `src/agent_quality_lab/`, `tests/`, GitHub workflows | Offline tests; CI awaiting actual pushed and green run |
| Customer issue reproduction and fix verification | `reproduction.py`, synthetic customer issues | Offline red-to-green fixture evidence; no real customer incident access |
| Linux, Python, shell | Python package, bash scripts, Dockerfile, Kubernetes manifests | Local tests passed; Linux CI executes only after push |
| Containers, Kubernetes, cloud-native CI/CD | Docker Compose, kind deployment, GitHub Actions | `make verify-docker`, `verify-kind`, `verify-ci` pending actual execution |
| Model inference runtime experience | `llm.py`, Ollama integration | Local `make verify-ollama` on Mac; no live Ollama on this build host |
| NIM inference | NIM client adapter, contract, retry/fault tests | `make verify-nim` with authorized endpoint and model ID |
| NeMo Guardrails | `nemo/guardrails/`, SDK smoke and heuristic policy assessment | `make verify-nemo`; human review needed for policy efficacy |
| Observability Prometheus/Grafana | telemetry metrics, scrape config and multi-panel dashboards | `make verify-docker` checks actual scraped metric/dashboard HTTP |
| Large-scale failure testing using KWOK / Chaos Monkey-like tooling | isolated `kwokctl` node-loss scheduler experiment | `make verify-kwok` verifies fake node/pod behavior, not real workload availability |
| CUDA-compatible GPU or GPU-accelerated software | accelerator GPU diagnostic and process co-residency sampler | `make verify-gpu` on accelerator Linux host; impossible natively on M1/CUDA |
| Reduced QA effort through AI | empty real-task capture CSV and paired report analyzer | No improvement claim until user records valid human task observations |
| Communication, curiosity, cross-functional teamwork | design/review artifacts, issue template and demo script | Hiring evidence must come from real interviews, work history and collaboration |

All platform statuses must be reproduced by **your runtime**; JSON reports ignored by Git are not magically carried in the ZIP. See [complete verification](COMPLETE_VERIFICATION.md), [Mac start guide](../START_HERE_MAC.md), [GPU runbook](GPU_HOST_RUNBOOK.md), and [human-effort protocol](EXPERIMENT_PROTOCOL.md).
