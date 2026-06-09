Run the BMAD edge case hunter review lane.

Use the BMAD code-review workflow and quick-dev acceptance standard as source guidance. Focus on boundary values, error paths, missing tests, concurrency, lifecycle, and integration edge cases.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/edge-case.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-bmad-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the edge case hunter lane.
