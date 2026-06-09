Synthesize the Compound Engineering code-review lanes.

Merge correctness, testing, maintainability, standards, CE always-on agent
outputs, selected conditional reviewer outputs, skipped conditional no-op
artifacts, deployment-verification notes, and gap-analysis findings into one
implementation-review report. Count skipped conditional artifacts as coverage
records, not reviewer failures. Deduplicate overlaps, suppress non-actionable
noise, classify required fixes, and write the approval verdict used by
`.gc/scripts/checks/implementation-review-approved.sh`. Required fixes must be
specific enough for the single apply step to resolve them directly.

Read the review context from `gc.build.code_review_context_path` and all lane
artifacts from `{{artifact_root}}/code-review/`. Write the synthesized report to
`gc.build.code_review_report_path`, which should be
`{{artifact_root}}/code-review/review-report.md`.

Close with `gc.outcome=pass`,
`code_review.review_verdict=approve|iterate`, and
`code_review.review_report_path=<synthesized report path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. Synthesis happens in this Gas City lane.
