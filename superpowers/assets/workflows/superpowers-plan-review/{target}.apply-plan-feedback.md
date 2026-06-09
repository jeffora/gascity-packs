Apply required Superpowers plan-review feedback.

Read the plan-review context from workflow root metadata
`gc.build.plan_review_context_path` and the plan-review report from
`gc.build.plan_review_report_path`. Write the apply summary to workflow root
metadata path `gc.build.plan_review_apply_summary_path`, which should be
`<artifact_root>/plan-review-apply-summary.md`.

Update only the requirements or plan artifacts needed to resolve required
findings. Preserve traceability and avoid adding unrequested scope. If a
finding cannot be resolved safely, record the blocker in the apply summary.

If the review report approves the plan, perform a no-op pass, mark the plan
artifact approved, update workflow root metadata with
`gc.build.plan_status=approved`, and close with `design_review.verdict=done`.
If required changes remain, apply them, keep the plan in draft status, update
workflow root metadata with `gc.build.plan_status=draft`, and close with
`design_review.verdict=iterate`.

Always close with `gc.outcome=pass`, `design_review.verdict=done|iterate`, and
`design_review.output_path=<apply summary path>`.

Do not invoke provider-native subagents. This Gas City lane owns the fix pass.
