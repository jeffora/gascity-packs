Run the BMAD gap-analysis review lane.

Use the assigned story self-check role to verify that the implemented story
matches the approved PRD, architecture plan, epics, stories, acceptance
criteria, and implementation summary. Flag missing acceptance coverage,
unverified done criteria, story drift, and required tests that are absent or not
proven.

Write concrete findings with story ids, acceptance criteria, artifact paths, or
file anchors so the synthesis lane can merge them with the other review lanes.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/gap-analysis.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-bmad-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents or upstream BMAD runtime commands.
