Review maintainability with the installed Compound Engineering maintainability
reviewer persona.

Check for unnecessary complexity, wrong-layer changes, type-safety holes, dead code, and unearned abstractions. Return structured findings for synthesis.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/maintainability.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the Gas City lane for this persona.
