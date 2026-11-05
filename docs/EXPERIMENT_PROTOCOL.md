# Real QA effort: manual versus AI-assisted experiment

**Hypothesis (not a claim):** AI assistance reduces hands-on QA task time without lowering confirmed defect detection or increasing false positives.

Pick at least four similarly sized synthetic QA tasks from this project: test case design, a mock flaky test investigation, reproducing a synthetic API failure, reviewing an agent output or proposing a regression set. Define the same expected outcome and acceptance criteria for both manual and AI sessions. Use independent variants to reduce learning effects, and counterbalance method order across tasks.

Time real human effort (minutes), not only model API latency. Capture the number of defects confirmed by a reviewer, false positives, who reviewed, whether this was the first or second attempt, and whether the AI run actually used an LLM rather than a rules fallback. Use no real customer data.

```bash
make productivity-template
# Fill artifacts/productivity-observations.csv: two observations per task_id.
# Columns: task_id,method,minutes,valid_defects,false_positives,reviewer,order,model_used,notes
# method=manual or ai; model_used=true for real AI runs.
make productivity-report
```

The report computes total human minutes, average/median paired minutes saved, percent change, confirmed defects and false positives. Positive speedup is **not** assumed: slower or less accurate AI results are legitimate findings. This small paired demonstration is observational, not definitive causal evidence; order, reviewer and task complexity may confound results. Do not turn `ollama-vs-baseline.json` latency numbers into human productivity claims.
