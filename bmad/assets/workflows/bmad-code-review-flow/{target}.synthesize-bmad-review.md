Synthesize BMAD code-review lanes.

Use the installed `bmad-code-review` skill as guidance. Deduplicate blind
hunter, edge case, acceptance auditor, and gap-analysis findings; classify
required fixes, residual risks, and test gaps; write the approval verdict used
by `.gc/scripts/checks/implementation-review-approved.sh`. Required fixes must
be specific enough for the single apply step to resolve them directly.

Read the review context from `gc.build.code_review_context_path` and all lane
artifacts from `{{artifact_root}}/code-review/`. Write the synthesized report to
`gc.build.code_review_report_path`, which should be
`{{artifact_root}}/code-review/review-report.md`.

Close with `gc.outcome=pass`,
`code_review.review_verdict=approve|iterate`, and
`code_review.review_report_path=<synthesized report path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-bmad-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. Synthesis happens in this Gas City lane.
