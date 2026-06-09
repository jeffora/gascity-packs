Apply required Compound Engineering plan-review findings.

Update only the requirements or plan artifacts needed to resolve required findings. Preserve Compound Engineering identifiers and traceability. If findings cannot be resolved safely, record the blocker in the review artifact instead of inventing scope.

Read the synthesized report from `gc.build.plan_review_report_path`. Write the
apply summary to `gc.build.plan_review_apply_summary_path`, which should be
`<artifact_root>/plan-review/apply-summary.md`.

If the synthesized report approves the plan with no required findings, perform
a no-op pass, update workflow root metadata with
`gc.build.plan_review_status=approved`, and close with
`design_review.verdict=done`. If required plan changes remain, update workflow
root metadata with `gc.build.plan_review_status=draft` and close with
`design_review.verdict=iterate`.

Always close with `gc.outcome=pass`,
`design_review.report_path=<apply summary path>`, and
`design_review.output_path=<apply summary path>`.

Do not invoke provider-native subagents. This Gas City lane owns the fix pass.
