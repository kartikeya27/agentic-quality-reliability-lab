# Reproducible bug lifecycle example

This repository includes `.github/ISSUE_TEMPLATE/defect.yml` and `.github/pull_request_template.md` to demonstrate defect triage, collaboration, fix verification and release-gate evidence.

1. **Detect:** golden-set or chaos CI marks a case failed; store JSON report as a GitHub Actions artifact.
2. **Reproduce:** create an issue using a synthetic incident ID, exact `AQ_MODE` / `AQ_MODEL`, Python/OS version and steps. Include expected/actual category, severity and tool trace.
3. **Triage:** assign severity based on impact and risk, distinguish model error, tool failure and infra/inference outage; no hidden fallback quality metrics.
4. **Fix:** create a branch, add a regression test that fails before the correction, and implement a change with safe tool permissions.
5. **Verify:** run pytest, golden evaluation, chaos suite and any needed model-specific checks. Include evidence in the PR, plus p95/accuracy deltas if relevant.
6. **Close:** link the issue and PR, record residual risks, and retain failing case in the dataset for future regressions.

A user can practice this without a real customer ticket by editing a local synthetic scenario to produce an intentional mismatch. **Do not** commit sensitive production logs or private data.
