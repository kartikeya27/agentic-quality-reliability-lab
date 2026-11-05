#!/usr/bin/env python3
"""Generate a capture template or analyze real, paired QA-task measurements.

This is an observational comparison, not a causal proof that AI helped.
Only user-collected sessions count. No synthetic speedup is inserted.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

FIELDS = ["task_id", "method", "minutes", "valid_defects", "false_positives", "reviewer", "order", "model_used", "notes"]


def template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer=csv.writer(output)
        writer.writerow(FIELDS)
    print(f"Blank, non-fabricated capture sheet: {path}")


def analyze(rows: list[dict]) -> dict:
    by_task: dict[str, dict] = {}
    for idx, row in enumerate(rows, 2):
        if not row.get('task_id') or row.get('method') not in ('manual', 'ai'):
            raise ValueError(f"CSV row {idx}: task_id and method manual/ai required")
        task = by_task.setdefault(row['task_id'].strip(), {})
        method = row['method']
        if method in task:
            raise ValueError(f"Duplicate task/method {row['task_id']} {method}")
        try:
            minutes = float(row['minutes'])
            valid_defects = int(row['valid_defects'])
            false_positives = int(row['false_positives'])
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"CSV row {idx}: invalid minutes/defect counts") from exc
        if not math.isfinite(minutes) or minutes <= 0 or min(valid_defects, false_positives) < 0:
            raise ValueError(f"CSV row {idx}: duration must be positive and counts nonnegative")
        if not row.get('reviewer') or row.get('order') not in ('first', 'second'):
            raise ValueError(f"CSV row {idx}: reviewer and order first/second required")
        if method == 'ai' and row.get('model_used', '').lower() != 'true':
            raise ValueError(f"CSV row {idx}: AI method must have model_used=true observed, no fallback")
        task[method] = dict(minutes=minutes, valid_defects=valid_defects, false_positives=false_positives,
                            reviewer=row['reviewer'], order=row['order'])
    if len(by_task) < 4 or any(set(r) != {'manual', 'ai'} for r in by_task.values()):
        raise ValueError("Need at least 4 tasks with exactly one manual and one real-AI observation each")
    if not all(set(x['order'] for x in v.values()) == {'first','second'} for v in by_task.values()):
        raise ValueError('Each task must record both order values to identify order effects')
    paired = []
    for id, r in sorted(by_task.items()):
        a,b=r['manual'],r['ai']
        paired.append({"task_id":id,"manual_minutes":a['minutes'],"ai_minutes":b['minutes'],
                       "minutes_saved":round(a['minutes']-b['minutes'],4),
                       "manual_valid_defects":a['valid_defects'],"ai_valid_defects":b['valid_defects'],
                       "manual_false_positives":a['false_positives'],"ai_false_positives":b['false_positives']})
    before=sum(x['manual_minutes'] for x in paired)
    after=sum(x['ai_minutes'] for x in paired)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence":"USER_RECORDED_PAIRED_TASK_TIMINGS",
        "paired_tasks":len(paired),
        "minutes_manual":round(before,3), "minutes_ai":round(after,3),
        "total_time_saved_minutes":round(before-after,3),
        "observed_time_change_percent":round(100*(after-before)/before,2),
        "mean_minutes_saved_per_task":round(mean(x['minutes_saved'] for x in paired),3),
        "median_minutes_saved_per_task":round(median(x['minutes_saved'] for x in paired),3),
        "valid_defects_manual":sum(x['manual_valid_defects'] for x in paired),
        "valid_defects_ai":sum(x['ai_valid_defects'] for x in paired),
        "false_positives_manual":sum(x['manual_false_positives'] for x in paired),
        "false_positives_ai":sum(x['ai_false_positives'] for x in paired),
        "tasks":paired,
        "limitations":"Task/order/reviewer effects and learning confound this observational experiment. Compare task complexity and validate findings with a blinded reviewer. Negative or zero benefit is a valid outcome. Results are not production results."
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', action='store_true', help='Write an empty observation CSV, not synthetic data')
    parser.add_argument('--input', default='artifacts/productivity-observations.csv')
    parser.add_argument('--out', default='artifacts/qa-productivity-report.json')
    args=parser.parse_args()
    target=Path(args.input)
    if args.template:
        template(target)
        return
    if not target.is_file():
        parser.error(f'Missing real observation file: {target}. Run --template, then conduct timed QA tasks.')
    with target.open(newline='', encoding='utf-8') as source:
        reader=csv.DictReader(source)
        if set(reader.fieldnames or []) != set(FIELDS):
            parser.error('Missing columns; use --template to create the supported capture sheet')
        result=analyze(list(reader))
    out=Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
