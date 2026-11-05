"""Safe, read-only local tools. No actions are carried out against real systems."""
import time

RUNBOOKS: dict[str, dict] = {
    "identity": {"id": "RB-IDENTITY-01", "team": "identity-oncall", "steps": ["Check identity provider status", "Inspect authentication error rates", "Collect sanitized login traces"]},
    "database": {"id": "RB-DATABASE-02", "team": "data-oncall", "steps": ["Check DB connection saturation", "Inspect query latency", "Review recent schema changes"]},
    "deployment": {"id": "RB-DEPLOY-03", "team": "platform-oncall", "steps": ["Inspect rollout status", "Compare release health metrics", "Consider approved rollback procedure"]},
    "network": {"id": "RB-NETWORK-04", "team": "network-oncall", "steps": ["Check DNS resolution", "Review service connectivity", "Inspect packet loss metrics"]},
    "general": {"id": "RB-GENERAL-05", "team": "service-desk", "steps": ["Collect reproducible steps", "Review service logs", "Route to product owner"]},
}

class RunbookTimeout(TimeoutError):
    pass


def lookup_runbook(category: str, fault: str = "none") -> dict:
    if fault == "slow_tool":
        time.sleep(0.20)  # deterministic delay, intentionally small for CI
    elif fault == "timeout":
        raise RunbookTimeout("simulated runbook lookup timeout")
    elif fault == "tool_error":
        raise RuntimeError("simulated tool transport failure")
    if category not in RUNBOOKS:
        raise ValueError("unrecognized category")
    return RUNBOOKS[category]
