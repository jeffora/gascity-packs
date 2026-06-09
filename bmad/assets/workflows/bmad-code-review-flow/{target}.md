Finalize the BMAD code-review expansion.

Use the installed `bmad-code-review` skill as guidance for the final report.
Verify the latest loop verdict from the apply-bmad-review-findings lane.

Approval path:

- Confirm `code_review.verdict=done` on the apply-bmad-review-findings lane.
- Confirm the synthesized review report exists at workflow root metadata
  `gc.build.code_review_report_path`.
- Confirm the review fix summary exists at workflow root metadata
  `gc.build.review_fix_summary_path`.
- Update workflow root metadata:
  - `gc.build.code_review_status=approved`
  - `gc.build.code_review_approved_at=<UTC timestamp>`
- Close this expansion target with `gc.outcome=pass`,
  `code_review.verdict=done`, and
  `code_review.report_path=<review fix summary path>`.

Failure path:

- If unresolved required findings remain, do not approve the expansion.
- Update workflow root metadata with `gc.build.code_review_status=failed`.
- Close with `gc.outcome=fail`, `code_review.report_path=<review fix summary
  path>`, and a concise `gc.failure_reason` that points at the blocking
  finding.
