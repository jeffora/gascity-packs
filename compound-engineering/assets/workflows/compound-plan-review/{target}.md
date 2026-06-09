Finalize the Compound Engineering plan-review expansion.

Verify the latest synthesized verdict is approved, record the review report path on the parent build step, and close this expansion target. If the loop exhausted attempts or has unresolved required findings, record a failing review outcome with the report path.

Use workflow root metadata `gc.build.plan_review_report_path` and
`gc.build.plan_review_apply_summary_path`. On success, update the workflow root
with `gc.build.plan_review_status=approved` and
`gc.build.plan_review_approved_at=<UTC timestamp>`, then close with
`gc.outcome=pass`.
