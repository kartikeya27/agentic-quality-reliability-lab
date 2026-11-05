"""Verify isolated KWOK control-plane scheduling and a simulated node-deletion fault."""
from pathlib import Path
import json


def inspect_kwok_snapshots(before_nodes: dict, after_nodes: dict, before_pods: dict, after_pods: dict, deleted_name: str, expected_new_count: int) -> dict:
    initial = {x["metadata"]["name"] for x in before_nodes["items"]}
    current = {x["metadata"]["name"] for x in after_nodes["items"]}
    prior_pods = before_pods["items"]
    later_pods = after_pods["items"]
    scheduled = [p for p in later_pods if p.get("spec", {}).get("nodeName") in current]
    checks = {
        "node_loss_visible": deleted_name in initial and deleted_name not in current,
        "remaining_simulated_nodes": bool(current),
        "pods_scheduled_after_fault": len(scheduled) >= expected_new_count,
        "replica_count_not_decreased": len(later_pods) >= len(prior_pods),
    }
    return {
        "checks": checks, "passed": all(checks.values()),
        "nodes_before": len(initial), "nodes_after": len(current),
        "pods_before": len(prior_pods), "pods_after": len(later_pods),
        "pods_scheduled_on_remaining_nodes": len(scheduled),
        "deleted_node": deleted_name,
        "simulation_only": True,
        "note": "KWOK fake pods do not execute the workload. This validates API/scheduler state, not actual service recovery.",
    }


def build_report(directory: str | Path, deleted_name: str, expected_new_count: int) -> dict:
    directory = Path(directory)
    def read(name):
        return json.loads((directory / name).read_text(encoding="utf-8"))
    return inspect_kwok_snapshots(read("nodes-before.json"), read("nodes-after.json"),
                                  read("pods-before.json"), read("pods-after.json"), deleted_name, expected_new_count)
