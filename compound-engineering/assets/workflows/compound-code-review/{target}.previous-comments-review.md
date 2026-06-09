Review previous PR comments with the installed Compound Engineering previous
comments persona.

This bead only runs after the cheap conditional gate selected previous-comment
review for this change. Verify that existing PR review comments or review
threads have been addressed. Do not re-run applicability as a no-op; skipped
previous-comment lanes are closed by the gate.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/previous-comments.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the Gas City lane for this
conditional persona.
