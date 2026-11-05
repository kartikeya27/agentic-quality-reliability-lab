"""Actual measured comparison: deterministic baseline vs a configured live model.

Only run when the chosen model runtime is accessible. Never attribute any quality
uplift to AI without these paired observations and model_used_rate == 1.
"""
from datetime import datetime, timezone
from .agent import AgentRunner
from .evaluation import evaluate
from .llm import ModelClient


def compare_live_model(cases, model_runner: AgentRunner | None = None) -> dict:
    runner = model_runner or AgentRunner()
    if runner.model.mode == "deterministic":
        raise ValueError("Choose AQ_MODE=ollama or AQ_MODE=nim for a live model experiment")
    before = evaluate(AgentRunner(ModelClient(mode="deterministic")), cases)
    after = evaluate(runner, cases)
    baseline = before["summary"]
    model = after["summary"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {"mode": "deterministic", **baseline},
        "candidate": {"mode": runner.model.mode, "model": runner.model.model, **model},
        "delta": {
            "pass_rate": round(model["pass_rate"] - baseline["pass_rate"], 4),
            "category_accuracy": round(model["category_accuracy"] - baseline["category_accuracy"], 4),
            "p95_latency_ms": round(model["p95_ms"] - baseline["p95_ms"], 2),
        },
        "model_execution_verified": model["model_used_rate"] == 1.0,
        "failed_cases_before": [r["id"] for r in before["cases"] if not r["passed"]],
        "failed_cases_after": [r["id"] for r in after["cases"] if not r["passed"]],
        "interpretation": "Two sequential local dataset runs, NOT a causal evaluation of QA team productivity. Negative deltas are real findings; no uplift is assumed.",
    }
