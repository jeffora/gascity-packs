Run the BMAD blind hunter review lane.

Use the installed `bmad-code-review` skill as guidance. Inspect the diff without
trusting the implementation report. Find concrete bugs, contract breaks, and
regressions.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/blind-hunter.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-bmad-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the blind hunter lane.
