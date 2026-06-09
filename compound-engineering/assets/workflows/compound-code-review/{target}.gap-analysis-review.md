Run the Compound Engineering gap-analysis review lane.

Use the assigned coherence-review role to compare the implementation result
against the approved requirements, plan, decomposition, and implementation
summary. Flag only missing delivered behavior, contradicted requirements,
untested required acceptance criteria, or implementation work that drifted from
the approved plan.

Write findings with concrete artifact, file, or command references so the
synthesis lane can merge them with the rest of the code-review findings.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/gap-analysis.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents or upstream plugin runtime commands.
