"""Low-cardinality telemetry, with no user text or incident IDs in metric labels."""
from prometheus_client import Counter, Histogram

REQUESTS = Counter("aq_triage_requests_total", "Triage requests", ["mode", "category", "status"])
LATENCY = Histogram("aq_triage_latency_seconds", "Triage end-to-end latency in seconds", ["mode"], buckets=(0.005, 0.02, 0.05, 0.1, 0.25, 0.5, 1, 3, 10, 30, 60))
FALLBACK = Counter("aq_model_fallback_total", "Model inference fallback count", ["mode"])
TOOL_FAILURE = Counter("aq_tool_failures_total", "Runbook tool errors", ["reason"])
