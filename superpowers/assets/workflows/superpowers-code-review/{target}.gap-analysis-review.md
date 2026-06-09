Run the Superpowers gap-analysis review lane.

Use the installed verification guidance to check whether the implementation
actually satisfies the approved requirements, plan, decomposition, and claimed
test evidence. Flag missing behavior, unverified acceptance criteria, drift from
the plan, and test claims that were not proven by commands or artifacts.

Write concrete findings that the feedback-processing lane can resolve in one
pass with file, artifact, command, or requirement references.

Read the code-review context from workflow root metadata
`gc.build.code_review_context_path`. Write the gap-analysis report to workflow
root metadata path `gc.build.gap_analysis_report_path`, which should be
`<artifact_root>/gap-analysis-report.md`.

Close with `gc.outcome=pass`, `code_review.gap_verdict=approve|iterate`,
`code_review.gap_report_path=<gap-analysis report path>`, and
`code_review.output_path=<gap-analysis report path>`.

Use the exact claimed bead id when updating metadata. Do not pass freeform notes
or additional positional arguments to `bd update`; unquoted words can resolve to
unrelated beads. Use this command shape:

```bash
bd update "$CLAIMED_BEAD_ID" \
  --set-metadata 'gc.outcome=pass' \
  --set-metadata 'code_review.gap_verdict=approve' \
  --set-metadata 'code_review.gap_report_path=<gap-analysis report path>' \
  --set-metadata 'code_review.output_path=<gap-analysis report path>'
bd close "$CLAIMED_BEAD_ID" --reason 'Gap-analysis review approved with no required findings.'
```

Do not set `code_review.verdict` or `code_review.report_path`; the
process-code-review lane owns those approval-check fields.

Do not invoke provider-native subagents or upstream plugin runtime commands.
