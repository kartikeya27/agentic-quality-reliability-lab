"""Explicit quality gates for a measured, local HTTP load report.

These are configurable demo thresholds, not measured production SLOs. A passing
report means the tested local scenario met only the supplied limits.
"""
from datetime import datetime, timezone
from math import isfinite


def evaluate_slo(load: dict, *, max_p95_ms: float = 5000.0,
                 max_p99_ms: float = 8000.0, max_error_rate: float = 0.0,
                 min_throughput_rps: float = 0.1, min_requests: int = 20) -> dict:
    if not (0 <= max_error_rate <= 1 and max_p95_ms > 0 and max_p99_ms > 0
            and min_throughput_rps >= 0 and min_requests >= 1):
        raise ValueError("Invalid SLO thresholds")
    required = ("requests", "successful", "failed", "p95_ms", "p99_ms", "throughput_rps")
    if any(key not in load for key in required):
        raise ValueError("Incomplete load report: missing " + ", ".join(k for k in required if k not in load))
    n, success, failed = int(load["requests"]), int(load["successful"]), int(load["failed"])
    if n < 1 or success < 0 or failed < 0 or success + failed != n:
        raise ValueError("Inconsistent request counts")
    for key in ("p95_ms", "p99_ms", "throughput_rps"):
        if not isfinite(float(load[key])) or float(load[key]) < 0:
            raise ValueError(f"Invalid metric: {key}")
    observed = {
        "requests": n,
        "error_rate": failed / n,
        "p95_ms": float(load["p95_ms"]),
        "p99_ms": float(load["p99_ms"]),
        "throughput_rps": float(load["throughput_rps"]),
    }
    checks = {
        "sample_size": n >= min_requests,
        "http_error_rate": observed["error_rate"] <= max_error_rate,
        "p95_latency": observed["p95_ms"] <= max_p95_ms,
        "p99_latency": observed["p99_ms"] <= max_p99_ms,
        "throughput": observed["throughput_rps"] >= min_throughput_rps,
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": all(checks.values()), "checks": checks,
        "observed": observed,
        "limits": {"min_requests": min_requests, "max_error_rate": max_error_rate,
                   "max_p95_ms": max_p95_ms, "max_p99_ms": max_p99_ms,
                   "min_throughput_rps": min_throughput_rps},
        "scope": "Observed HTTP client metrics on the tested local app; not a production SLO, GPU throughput, or capacity proof.",
    }
