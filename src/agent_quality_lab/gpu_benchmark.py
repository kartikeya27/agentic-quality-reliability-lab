"""accelerator-host benchmark gate: local driver presence + actual inference participation.

A remote NIM endpoint may be backed by a GPU elsewhere. This checks the local GPU
separately and never asserts that the local GPU executed the remote inference.
"""
from .agent import AgentRunner
from .gpu import gpu_diagnostic
from .schemas import TriageRequest
from .evaluation import percentile


def run_gpu_inference_probe(runner: AgentRunner, iterations: int = 5) -> dict:
    if not 1 <= iterations <= 100:
        raise ValueError("iterations must be 1..100")
    hardware = gpu_diagnostic()
    if not hardware["available"]:
        raise RuntimeError("accelerator GPU not detected on this machine; use an accelerator-equipped Linux host")
    if runner.model.mode not in ("nim", "openai_compatible", "ollama"):
        raise RuntimeError("A real inference mode is mandatory for the GPU probe")
    records = [runner.triage(TriageRequest(incident_id=f"GPU-{n}", message="Database query failed")) for n in range(iterations)]
    post = gpu_diagnostic()
    return {
        "local_gpu_before": hardware, "local_gpu_after": post,
        "mode": runner.model.mode, "model": runner.model.model,
        "iterations": iterations, "model_used": sum(r.model_used for r in records),
        "fallbacks": sum(r.fallback_used for r in records),
        "p50_ms": round(percentile([r.latency_ms for r in records], .5), 2),
        "p95_ms": round(percentile([r.latency_ms for r in records], .95), 2),
        "p99_ms": round(percentile([r.latency_ms for r in records], .99), 2),
        "gate_passed": all(r.model_used and not r.fallback_used for r in records),
        "limitation": "GPU monitor CLI host snapshots + client-observed latency. Does not establish actual model GPU residency; use server DCGM metrics and host logs to verify deployment.",
    }
