Check deployment readiness with the installed Compound Engineering deployment
verification agent.

This bead only runs after the cheap conditional gate selected deployment
verification for this change. Produce Go/No-Go deployment checks, read-only
verification queries, rollback concerns, and monitoring focus areas. Do not
re-run applicability as a no-op; skipped deployment-verification lanes are
closed by the gate.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/deployment-verification.md`. Close
with `gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the Gas City lane for this CE
conditional agent.
