# System design, test strategy and threat boundaries

## Purpose / non-goals

This repository is an **engineering demonstration**, not a production helpdesk, a real infrastructure remediation agent or a model benchmark. Inputs and gold labels are synthetic. All runbooks are local read-only constants. No external calls occur in `AQ_MODE=deterministic`.

## Agent path

1. FastAPI validates incident ID and message fields (reject unknown properties).
2. `AgentRunner` calculates a deterministic baseline decision for resilience.
3. In explicitly configured inference mode, `ModelClient` asks Ollama or a compatible `/v1/chat/completions` endpoint for `{category, severity}`.
4. The model response must conform to an enumerated Pydantic schema. An invalid/unavailable model triggers a **counted and visible fallback**, not a silently marked model success.
5. The selected category becomes an argument to **one allowlisted read-only tool**, `lookup_runbook`.
6. Tool timeout or simulated failure results in a manual-review record: no automated remediation, no invented runbook, explicit degraded trace.
7. The structured result includes category, severity, team, read-only tool trace, inference mode/participation, fallback, degradation, latency.
8. Prometheus counters/histograms use low-cardinality labels, with no incident descriptions in metric labels.

## Quality strategy

| Layer | Primary tests | Diagnostic |
| --- | --- | --- |
| Input contract | Pydantic validation + HTTP 422 test | Reject arbitrary extra fields / bad ID |
| Functional | Labeled category + severity goldens | Exact-match accuracy and mismatched cases |
| Workflow integration | Decision → runbook → response | `trace.tool`, `trace.status`, `runbook_id` |
| Model/runtime failure | Invalid/unreachable backend stub | `model_used=false`, `fallback_used=true` |
| Prompt injection | User text requests unauthorized secrets | Tool allowlist + safe runbook routing |
| Fault injection | Error, timeout, 200ms delay | Degraded state, safe human escalation, trace |
| Performance | Bounded localhost client | p50/p95/p99 and successful request rate |
| Reliability | Real-cluster rollout smoke script, optional | Rollout readiness, pod health — needs a cluster |
| Regression optimization | Greedy weighted tag coverage | Selection list + uncovered tags |
| Flaky tests | Multiple pass/fail observations | Flaky vs stable pass/fail vs insufficient history |
| CI/CD | Matrix pytest + golden eval + chaos | GitHub Action success and uploaded evidence |
| Observability | Prometheus + Grafana | Counters, fallback, p95, tool error dashboard |

A golden label is not model ground truth forever: review changes, version datasets, record annotation rationale, and add adversarial examples as model capabilities shift. This starter set has **16** synthetic cases, not a statistical generalization claim.

## Measured metrics and limitations

- `category_accuracy`, `severity_accuracy`: exact-match agreement with a small synthetic gold dataset.
- `pass_rate`: every case must meet category, severity, trace, non-degraded outcome and output contract.
- `model_used_rate`: fraction of cases whose classification actually came from a successfully parsed model reply. **This is 0 for offline baseline.**
- `fallback_rate`: proportion of cases in which configured inference failed and rules were substituted. All model evals should track this beside pass rate.
- `p95_ms`: nearest-rank p95 end-to-end latency for the tested scenarios; in-process evaluation and external HTTP load have **different timing boundaries**.
- `tag_coverage_ratio`: proportion of distinct human-authored tags covered by the selected test subset; **not** instrumentation-based line or branch coverage.
- `flaky`: any mixed pass/fail observation over at least three runs. More sophisticated flakiness attribution requires retries, resource telemetry, and failure clustering.

## Risk analysis / safeguards

- **Prompt injection:** incident text is untrusted; AI outputs cannot select arbitrary tools or run shell commands. Fixed allowlist and enum validation reduce attack surface. This is not a complete security audit or a proof of injection immunity for all LLMs.
- **Unsupported action:** tool only reads local runbook data; remediation is never performed.
- **Model hallucination:** category/severity constrained, but a plausible yet incorrect enum is still possible; goldens expose errors rather than guarantee correctness.
- **Unavailable inference:** counted fallback to rules is visible; `--require-model` prevents misleading model quality claims.
- **Overexposed chaos API:** non-`none` request faults return HTTP 403 unless `AQ_ENABLE_FAULTS=1`; use only on trusted localhost and never enable on exposed public servers.
- **Credentials:** never commit `.env` or API keys. Use environment variables or secret stores for optional compatible backends.
- **Data retention:** sample request bodies are never stored in Prometheus labels. Production incident text would require a proper privacy/data-retention review.
- **Model endpoint security:** user-provided URL can send prompt content outside local network; configure only trusted endpoint and synthetic test inputs.
- **Traffic safety:** built-in load generator only accepts localhost targets and caps concurrency/request counts.

## Suggested real-world extensions

Extend from unit-level chaos to container failures, pod evictions, network policies and regional outage injection in a **separate test cluster**. Use KWOK for simulated Kubernetes control-plane scale, not real pods/GPU inference. Add a real accelerator NIM test matrix only after access to supported runtime and hardware; label these tests `integration` and record environment fingerprints, driver/runtime versions, latency distributions, token counts and reproducibility conditions.
