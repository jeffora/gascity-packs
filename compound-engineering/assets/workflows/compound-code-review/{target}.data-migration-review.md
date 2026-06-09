Review data migration risk with the installed Compound Engineering
data-migration persona.

This bead only runs after the cheap conditional gate selected data-migration
review for this change. Inspect migrations, schema dumps, backfills, stored
data shape changes, or explicit data transforms for schema drift,
deploy-window safety, verification, and rollback. Do not re-run applicability
as a no-op; skipped data-migration lanes are closed by the gate.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/data-migration.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the Gas City lane for this
conditional persona.
