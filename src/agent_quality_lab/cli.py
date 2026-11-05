"""Run `agent-quality --help` after installing the package."""
import argparse
import json
from pathlib import Path
from .agent import AgentRunner
from .evaluation import read_jsonl, load_golden, evaluate, write_report, compare_reports
from .analysis import analyze_flaky, select_cases
from .testgen import generate_metamorphic, propose_ai_cases
from .schemas import TriageRequest
from .performance import run_load
from .advanced_eval import load_advanced_cases, run_advanced
from .inference_chaos import run_inference_faults
from .qa_benchmark import compare_regression_effort
from .gpu import gpu_diagnostic
from .nemo_adapter import run_nemo_smoke
from .model_experiment import compare_live_model
from .gpu_benchmark import run_gpu_inference_probe
from .mutation_benchmark import benchmark_mutations
from .slo import evaluate_slo
from .reproduction import load_issues, reproduce, markdown_defect, verify_fix
from .requirements import trace_from_files
from .nemo_policy_eval import load_policy_cases, run_policy_eval

GOLDEN = "data/golden_cases.jsonl"


def dump(obj: dict | list, path: str | None = None, as_jsonl: bool = False):
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = "".join(json.dumps(row) + "\n" for row in obj) if as_jsonl else json.dumps(obj, indent=2) + "\n"
        target.write_text(content, encoding="utf-8")
        print(f"Wrote {target}")
    else:
        print(json.dumps(obj, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Agentic QA & Reliability Lab")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Serve the local FastAPI demo")
    serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=8000)
    ev = sub.add_parser("eval", help="Run golden-set QA checks and create JSON/Markdown evidence")
    ev.add_argument("--cases", default=GOLDEN); ev.add_argument("--out", default="artifacts/eval-report.json")
    ev.add_argument("--min-pass-rate", type=float, default=1.0); ev.add_argument("--require-model", action="store_true")
    chaos = sub.add_parser("chaos", help="Test tool failures and bounded delays in-process")
    chaos.add_argument("--out", default="artifacts/chaos-report.json")
    gen = sub.add_parser("generate", help="Generate metamorphic cases or AI-proposed candidates")
    gen.add_argument("--cases", default=GOLDEN); gen.add_argument("--out", default="artifacts/generated-cases.jsonl")
    gen.add_argument("--limit", type=int, default=10); gen.add_argument("--ai", action="store_true")
    flaky = sub.add_parser("flaky", help="Analyze pass/fail histories to detect instability")
    flaky.add_argument("--runs", default="data/flaky_runs.jsonl"); flaky.add_argument("--out", default="artifacts/flaky-report.json")
    select = sub.add_parser("select", help="Greedy risk-weighted coverage optimization")
    select.add_argument("--cases", default=GOLDEN); select.add_argument("--budget", type=int, default=6)
    select.add_argument("--out", default="artifacts/selected-cases.json")
    perf = sub.add_parser("load", help="Bounded localhost HTTP load test")
    perf.add_argument("--url", default="http://127.0.0.1:8000"); perf.add_argument("--requests", type=int, default=30)
    perf.add_argument("--concurrency", type=int, default=5); perf.add_argument("--out", default="artifacts/load-report.json")
    cmp = sub.add_parser("compare", help="Find test regressions between two evaluation reports")
    cmp.add_argument("--before", required=True); cmp.add_argument("--after", required=True)
    cmp.add_argument("--out", default="artifacts/regression-diff.json")
    advanced = sub.add_parser("advanced", help="Adversarial, repeat-consistency and runbook attribution checks")
    advanced.add_argument("--cases", default="data/advanced_cases.jsonl")
    advanced.add_argument("--out", default="artifacts/advanced-report.json")
    advanced.add_argument("--repeats", type=int, default=3)
    advanced.add_argument("--min-pass-rate", type=float, default=1.0)
    advanced.add_argument("--require-model", action="store_true")
    inf = sub.add_parser("inference-chaos", help="Offline simulated NIM timeout/upstream/invalid schema")
    inf.add_argument("--out", default="artifacts/inference-chaos-report.json")
    eff = sub.add_parser("efficiency", help="Measured full vs risk-selected test run (NOT AI uplift)")
    eff.add_argument("--cases", default=GOLDEN)
    eff.add_argument("--budget", type=int, default=6)
    eff.add_argument("--out", default="artifacts/efficiency-report.json")
    mutation = sub.add_parser("mutation", help="Measure known seeded defect detection in full and risk-selected test suites")
    mutation.add_argument("--budget", type=int, default=6)
    mutation.add_argument("--out", default="artifacts/mutation-report.json")
    gpu = sub.add_parser("gpu-diag", help="Detect accelerator GPU and driver; does not benchmark GPU")
    gpu.add_argument("--out", default="artifacts/gpu-report.json")
    gpu.add_argument("--require-gpu", action="store_true")
    nemo = sub.add_parser("nemo-smoke", help="Opt-in actual NeMo Guardrails SDK via local Ollama")
    nemo.add_argument("--config", default="nemo/guardrails")
    nemo.add_argument("--out", default="artifacts/nemo-smoke-report.json")
    nemo.add_argument("--prompt", default="DNS packet loss in the staging cluster")
    experiment = sub.add_parser("model-experiment", help="Measure real model vs deterministic on SAME goldens")
    experiment.add_argument("--cases", default=GOLDEN)
    experiment.add_argument("--out", default="artifacts/model-experiment.json")
    gpup = sub.add_parser("gpu-nim-benchmark", help="accelerator-host only: gated real inference latency + driver snapshots")
    gpup.add_argument("--iterations", type=int, default=5)
    gpup.add_argument("--out", default="artifacts/gpu-nim-benchmark.json")
    slop = sub.add_parser("slo", help="Gate measured local HTTP load against explicit thresholds")
    slop.add_argument("--load-report", default="artifacts/load-report.json")
    slop.add_argument("--out", default="artifacts/slo-gate-report.json")
    slop.add_argument("--max-p95-ms", type=float, default=5000)
    slop.add_argument("--max-p99-ms", type=float, default=8000)
    slop.add_argument("--max-error-rate", type=float, default=0)
    slop.add_argument("--min-throughput-rps", type=float, default=0.1)
    slop.add_argument("--min-requests", type=int, default=20)
    reprp = sub.add_parser("reproduce", help="Reproduce a synthetic incident and create issue evidence")
    reprp.add_argument("--dataset", default="data/customer_issues.jsonl")
    reprp.add_argument("--issue", default="SYN-DB-001")
    reprp.add_argument("--inject-known-bug", action="store_true")
    reprp.add_argument("--out", default="artifacts/defects/reproduction.json")
    cycle = sub.add_parser("bug-cycle", help="Generate known-bad/red then baseline/green synthetic regression evidence")
    cycle.add_argument("--dataset", default="data/customer_issues.jsonl")
    cycle.add_argument("--issue", default="SYN-DB-001")
    cycle.add_argument("--out-dir", default="artifacts/defects")
    trace = sub.add_parser("traceability", help="Require execution evidence for each accelerator requirement")
    trace.add_argument("--requirements", default="data/requirements.json")
    trace.add_argument("--junit", default="artifacts/pytest-results.xml")
    trace.add_argument("--out", default="artifacts/requirements-traceability.json")
    npolicy = sub.add_parser("nemo-policy-eval", help="Run optional NeMo SDK policy fixtures (heuristic, requires review)")
    npolicy.add_argument("--cases", default="data/guardrail_cases.jsonl")
    npolicy.add_argument("--config", default="nemo/guardrails")
    npolicy.add_argument("--out", default="artifacts/nemo-policy-eval.json")
    npolicy.add_argument("--min-heuristic-score", type=float, default=0.75)
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn
        uvicorn.run("agent_quality_lab.api:app", host=args.host, port=args.port)
    elif args.command == "eval":
        if not 0 <= args.min_pass_rate <= 1:
            parser.error("--min-pass-rate must be between 0 and 1")
        report = evaluate(AgentRunner(), load_golden(args.cases))
        write_report(report, args.out)
        print(json.dumps(report["summary"], indent=2))
        print(f"Saved {args.out} and {str(Path(args.out).with_suffix('.md'))}")
        if report["summary"]["pass_rate"] < args.min_pass_rate or (args.require_model and report["summary"]["model_used_rate"] != 1):
            raise SystemExit("QUALITY GATE FAILED: accuracy below target or model inference not used")
        print("QUALITY GATE PASSED")
    elif args.command == "chaos":
        runner = AgentRunner()
        baseline = runner.triage(TriageRequest(incident_id="CHAOS-base", message="Database query failed"))
        scenarios = []
        for fault in ("tool_error", "timeout", "slow_tool"):
            actual = runner.triage(TriageRequest(incident_id=f"CHAOS-{fault}", message="Database query failed", fault=fault))
            checks = {"category_preserved": actual.category == baseline.category,
                      "safe_fallback": actual.runbook_id == "MANUAL-REVIEW" if fault != "slow_tool" else actual.runbook_id == baseline.runbook_id,
                      "degraded_flag": actual.degraded == (fault != "slow_tool"),
                      "trace_reported": actual.trace[0].status == {"tool_error":"error", "timeout":"timeout", "slow_tool":"ok"}[fault]}
            scenarios.append({"fault": fault, "passed": all(checks.values()), "checks": checks, "latency_ms": actual.latency_ms})
        report = {"scenarios": scenarios, "passed": all(s["passed"] for s in scenarios)}
        dump(report, args.out)
        if not report["passed"]:
            raise SystemExit("Chaos resilience tests failed")
        print("All three chaos scenarios passed")
    elif args.command == "generate":
        if args.limit < 1:
            parser.error("--limit must be at least 1")
        cases = load_golden(args.cases)
        drafts = propose_ai_cases(AgentRunner().model, cases) if args.ai else generate_metamorphic(cases, args.limit)
        dump(drafts, args.out, as_jsonl=True)
        print("AI drafts require human validation and are not automatically merged into the golden set" if args.ai else "Metamorphic cases inherit labels from approved original scenarios")
    elif args.command == "flaky":
        dump(analyze_flaky(read_jsonl(args.runs)), args.out)
    elif args.command == "select":
        dump(select_cases(load_golden(args.cases), args.budget), args.out)
    elif args.command == "load":
        result = run_load(args.url, args.requests, args.concurrency)
        dump(result, args.out)
        if result["failed"]:
            raise SystemExit("Load test experienced HTTP errors")
    elif args.command == "advanced":
        if not 0 <= args.min_pass_rate <= 1:
            parser.error("--min-pass-rate must be between 0 and 1")
        report = run_advanced(AgentRunner(), load_advanced_cases(args.cases), args.repeats)
        dump(report, args.out)
        print(json.dumps(report["summary"], indent=2))
        if report["summary"]["pass_rate"] < args.min_pass_rate or (args.require_model and report["summary"]["model_used_rate"] != 1):
            raise SystemExit("ADVANCED QUALITY GATE FAILED")
    elif args.command == "inference-chaos":
        report = run_inference_faults()
        dump(report, args.out)
        if not report["passed"]:
            raise SystemExit("INFERENCE RESILIENCE QUALITY GATE FAILED")
    elif args.command == "efficiency":
        report = compare_regression_effort(AgentRunner(), load_golden(args.cases), args.budget)
        dump(report, args.out)
        print(json.dumps({k: report[k] for k in ("case_reduction_ratio", "observed_time_reduction_ratio", "known_uncovered_failing_cases")}, indent=2))
    elif args.command == "mutation":
        report = benchmark_mutations(load_golden(GOLDEN), args.budget)
        dump(report, args.out)
        if report["full_detected"] < report["total_mutations"]:
            raise SystemExit("Seeded defect detection gate failed")
    elif args.command == "gpu-diag":
        report = gpu_diagnostic()
        dump(report, args.out)
        if args.require_gpu and not report["available"]:
            raise SystemExit("No accelerator GPU detected; GPU gate not met")
    elif args.command == "nemo-smoke":
        report = run_nemo_smoke(args.config, args.prompt)
        dump(report, args.out)
    elif args.command == "model-experiment":
        report = compare_live_model(load_golden(args.cases))
        dump(report, args.out)
        if not report["model_execution_verified"]:
            raise SystemExit("Model experiment did not use real inference on all cases")
    elif args.command == "gpu-nim-benchmark":
        report = run_gpu_inference_probe(AgentRunner(), args.iterations)
        dump(report, args.out)
        if not report["gate_passed"]:
            raise SystemExit("GPU inference model participation gate failed")
    elif args.command == "slo":
        report = evaluate_slo(json.loads(Path(args.load_report).read_text()),
                              max_p95_ms=args.max_p95_ms, max_p99_ms=args.max_p99_ms,
                              max_error_rate=args.max_error_rate,
                              min_throughput_rps=args.min_throughput_rps, min_requests=args.min_requests)
        dump(report, args.out)
        if not report["passed"]:
            raise SystemExit("PERFORMANCE SLO GATE FAILED")
    elif args.command == "reproduce":
        issues = load_issues(args.dataset)
        if args.issue not in issues:
            parser.error(f"Unknown synthetic issue: {args.issue}")
        report = reproduce(issues[args.issue], inject_fault=args.inject_known_bug)
        dump(report, args.out)
        Path(args.out).with_suffix(".md").write_text(markdown_defect(report), encoding="utf-8")
        if not report["passed"]:
            raise SystemExit("REPRODUCED: synthetic bug detected; inspect defect report")
    elif args.command == "bug-cycle":
        issues = load_issues(args.dataset)
        if args.issue not in issues:
            parser.error(f"Unknown synthetic issue: {args.issue}")
        before = reproduce(issues[args.issue], inject_fault=True)
        after = reproduce(issues[args.issue], inject_fault=False)
        summary = verify_fix(before, after)
        output = Path(args.out_dir)
        dump(before, str(output / "before-bug.json"))
        dump(after, str(output / "after-fix.json"))
        dump(summary, str(output / "fix-verification.json"))
        (output / "defect-reproduction.md").write_text(markdown_defect(before), encoding="utf-8")
        if not summary["passed"]:
            raise SystemExit("Synthetic red-green regression gate failed")
    elif args.command == "nemo-policy-eval":
        if not 0 <= args.min_heuristic_score <= 1:
            parser.error("--min-heuristic-score must be between 0 and 1")
        report = run_policy_eval(args.config, load_policy_cases(args.cases))
        dump(report, args.out)
        if report["heuristic_score"] < args.min_heuristic_score:
            raise SystemExit("NeMo heuristic policy evaluation missed threshold; manual review required")
    elif args.command == "traceability":
        report = trace_from_files(args.requirements, args.junit)
        dump(report, args.out)
        if not report["offline_gate_passed"]:
            raise SystemExit("accelerator requirements offline traceability gate failed")
    elif args.command == "compare":
        before, after = json.loads(Path(args.before).read_text()), json.loads(Path(args.after).read_text())
        result = compare_reports(before, after)
        dump(result, args.out)
        if result["regressions"]:
            raise SystemExit("Regression comparison found newly failing cases")

if __name__ == "__main__":
    main()
