Run Superpowers code review with the installed `requesting-code-review` skill.

Review the implementation against the requirements, plan, decomposition, and
test evidence. Write an implementation-review report with pass/fail verdict and
actionable findings. Required fixes must be specific enough for the processing
step to resolve them directly.

Read the code-review context from workflow root metadata
`gc.build.code_review_context_path`. Write the implementation review report to
workflow root metadata path `gc.build.code_review_report_path`, which should be
`<artifact_root>/implementation-review-report.md`.

Close with `gc.outcome=pass`,
`code_review.review_verdict=approve|iterate`,
`code_review.review_report_path=<implementation review report path>`, and
`code_review.output_path=<implementation review report path>`.

Use the exact claimed bead id when updating metadata. Do not pass freeform notes
or additional positional arguments to `bd update`; unquoted words can resolve to
unrelated beads. Use this command shape:

```bash
bd update "$CLAIMED_BEAD_ID" \
  --set-metadata 'gc.outcome=pass' \
  --set-metadata 'code_review.review_verdict=approve' \
  --set-metadata 'code_review.review_report_path=<implementation review report path>' \
  --set-metadata 'code_review.output_path=<implementation review report path>'
bd close "$CLAIMED_BEAD_ID" --reason 'Implementation review approved with no required findings.'
```

Do not set `code_review.verdict` or `code_review.report_path`; the
process-code-review lane owns those approval-check fields.

Do not invoke provider-native subagents. You are the Gas City code review lane.
