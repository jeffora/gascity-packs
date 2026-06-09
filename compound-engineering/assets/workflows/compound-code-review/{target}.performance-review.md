Review performance with the installed Compound Engineering performance persona.

This bead only runs after the cheap conditional gate selected performance
review for this change. Inspect database queries, loop-heavy transforms,
caching, async work, or other performance-sensitive paths and return structured
findings for synthesis. Do not re-run applicability as a no-op; skipped
performance lanes are closed by the gate.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/performance.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the Gas City lane for this
conditional persona.
