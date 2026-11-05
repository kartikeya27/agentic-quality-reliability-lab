"""Dependency-free teaching implementations; explicitly NOT NeMo or KWOK.

These use local, synthetic data to make a useful offline demo possible.
Actual SDK/cluster integrations remain separate and must be verified separately.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Example-level, deterministic policies, not a guarantee of prompt-injection safety.
DENIED_INSTRUCTIONS = (
    r"\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions\b",
    r"\breveal\b.{0,60}\b(?:credentials|passwords|secrets|tokens)\b",
    r"\bpretend\b.{0,60}\b(?:changed|deployed|modified)\b",
)


def local_policy_check(message: str) -> dict:
    matched = [pattern for pattern in DENIED_INSTRUCTIONS if re.search(pattern, message, re.IGNORECASE | re.DOTALL)]
    return {"action": "block" if matched else "allow", "matched_patterns": len(matched),
            "scope": "LOCAL_STATIC_POLICY_ONLY_NOT_NEMO_SDK"}


def local_policy_fixtures(path: str | Path) -> dict:
    cases = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    checks = []
    for case in cases:
        actual = local_policy_check(case["prompt"])
        checks.append({"id": case["id"], "expected": case["expected"],
                       "actual": actual["action"], "passed": actual["action"] == case["expected"]})
    return {"scope": "Synthetic local policy fixtures; not real NeMo Guardrails SDK evaluation",
            "mode": "LOCAL_SIMULATION", "total": len(checks), "passed": sum(x["passed"] for x in checks),
            "all_passed": all(x["passed"] for x in checks), "cases": checks}


def simulate_node_failure(nodes: int = 4, replicas: int = 24) -> dict:
    """Toy round-robin scheduling example, not Kubernetes, KWOK or application recovery."""
    if nodes < 2 or replicas < 1:
        raise ValueError("Need two or more nodes and at least one replica")
    node_names = [f"virtual-node-{i}" for i in range(nodes)]
    before = {f"pod-{i}": node_names[i % nodes] for i in range(replicas)}
    failed_node = node_names[0]
    survivors = node_names[1:]
    after = {}
    rescheduled = 0
    for pod, node in before.items():
        if node == failed_node:
            node = survivors[rescheduled % len(survivors)]
            rescheduled += 1
        after[pod] = node
    checks = {"all_replicas_scheduled": len(after) == replicas,
              "failed_node_has_no_pods": failed_node not in after.values(),
              "affected_pods_rescheduled": rescheduled == sum(v == failed_node for v in before.values())}
    return {"scope": "Toy Python scheduler only. NOT Kubernetes/KWOK or workload failover",
            "mode": "LOCAL_SIMULATION", "nodes_before": nodes, "nodes_after": nodes - 1,
            "replicas": replicas, "rescheduled_pods": rescheduled, "checks": checks,
            "passed": all(checks.values())}
