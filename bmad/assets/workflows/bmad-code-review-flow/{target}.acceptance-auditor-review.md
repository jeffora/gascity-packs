Run the BMAD acceptance auditor review lane.

Compare the implementation against BMAD PRD requirements, architecture decisions, epics/stories, and Given/When/Then acceptance criteria. Flag missing or extra behavior with artifact references.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/acceptance-auditor.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-bmad-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the acceptance auditor lane.
