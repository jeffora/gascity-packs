Apply required BMAD code-review findings.

Read the synthesized BMAD review report and resolve required findings in this
single lane. Preserve traceability to the review lane, story id, acceptance
criteria, file anchors, and severity.

Read the synthesized report from `gc.build.code_review_report_path`. Write the
review-fix summary to `gc.build.review_fix_summary_path`, which should be
`{{artifact_root}}/code-review/apply-summary.md`.

Use implementation target {{implementation_target}} for any code changes.
Close this lane only after the implementation summary and BMAD review artifact
record changed files, tests run, resolved findings, and blockers. If there are
no required fixes, record a no-op review-fix artifact instead of editing code.

If the synthesized report approves the implementation with no required fixes,
perform a no-op pass, update workflow root metadata with
`gc.build.code_review_status=approved`, and close with
`code_review.verdict=done`. If required fixes remain after processing, update
workflow root metadata with `gc.build.code_review_status=draft` and close with
`code_review.verdict=iterate`.

Always close with `gc.outcome=pass`,
`code_review.report_path=<review fix summary path>`, and
`code_review.output_path=<review fix summary path>`.

Do not invoke provider-native subagents. This graph lane is the delegation
mechanism.
