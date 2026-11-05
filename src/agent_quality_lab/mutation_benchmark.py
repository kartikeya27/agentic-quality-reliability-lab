"""Reproducible defect detection against deliberately seeded triage faults.

This is mutation-style fault detection, not an AI uplift or production defect count.
"""
from datetime import datetime, timezone
from .agent import AgentRunner
from .evaluation import evaluate
from .analysis import select_cases


class MutatedRunner(AgentRunner):
    def __init__(self, mutation: str):
        super().__init__()
        self.mutation = mutation

    def triage(self, request):
        result = super().triage(request)
        if self.mutation == "network_as_general" and result.category == "network":
            result.category = "general"
        elif self.mutation == "identity_as_database" and result.category == "identity":
            result.category = "database"
        elif self.mutation == "critical_downgrade" and result.severity == "critical":
            result.severity = "medium"
        elif self.mutation == "high_downgrade" and result.severity == "high":
            result.severity = "medium"
        elif self.mutation == "broken_trace":
            result.trace = []
        elif self.mutation == "blank_runbook":
            result.runbook_id = ""
        return result


def benchmark_mutations(cases, budget: int = 6) -> dict:
    if not cases:
        raise ValueError("cases must not be empty")
    subset_selection = select_cases(cases, budget)
    chosen = [c for c in cases if c.id in set(subset_selection['selected_ids'])]
    mutations = ("network_as_general", "identity_as_database", "critical_downgrade", "high_downgrade", "broken_trace", "blank_runbook")
    findings = []
    for name in mutations:
        runner = MutatedRunner(name)
        full = evaluate(runner, cases)
        selected = evaluate(runner, chosen)
        full_detected = [x['id'] for x in full['cases'] if not x['passed']]
        selected_detected = [x['id'] for x in selected['cases'] if not x['passed']]
        findings.append({"mutation": name, "full_detected": bool(full_detected),
                         "selected_detected": bool(selected_detected),
                         "full_killing_cases": full_detected,
                         "selected_killing_cases": selected_detected})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "synthetic controlled faults in local triage agent",
        "mutations": findings,
        "full_detected": sum(x['full_detected'] for x in findings),
        "selected_detected": sum(x['selected_detected'] for x in findings),
        "total_mutations": len(mutations),
        "full_mutation_detection_ratio": sum(x['full_detected'] for x in findings) / len(mutations),
        "selected_mutation_detection_ratio": sum(x['selected_detected'] for x in findings) / len(mutations),
        "selected_case_count": len(chosen), "full_case_count": len(cases),
        "risk_tag_coverage_ratio": subset_selection['tag_coverage_ratio'],
        "limitations": "Seeded in-process defects only; no AI efficacy or customer bug prediction demonstrated. A real-model test plan requires labeled human-reviewed cases and repeated sampling.",
    }
