#!/usr/bin/env python3
"""Offline teaching examples. Reports deliberately say SIMULATED, not accelerator verified."""
import json
from pathlib import Path
from agent_quality_lab.local_extensions import local_policy_fixtures, simulate_node_failure


def main() -> int:
    output = Path('artifacts'); output.mkdir(exist_ok=True)
    policy = local_policy_fixtures('data/guardrail_cases.jsonl')
    scheduler = simulate_node_failure()
    (output / 'local-policy-fixtures.json').write_text(json.dumps(policy, indent=2) + '\n')
    (output / 'local-scheduling-simulation.json').write_text(json.dumps(scheduler, indent=2) + '\n')
    print(f'Local static policy fixtures: {policy["passed"]}/{policy["total"]} (NOT NeMo SDK)')
    print(f'Local scheduling simulation: {scheduler["passed"]} (NOT KWOK)')
    return 0 if policy['all_passed'] and scheduler['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
