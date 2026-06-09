Prepare the Compound Engineering code-review context.

Resolve the implementation summary, changed files, diff base, requirements, plan, decomposition output, and artifact root. Write a compact context bundle for the review lanes.

Create `{{artifact_root}}/code-review/` if needed. Write:

- Review context: `{{artifact_root}}/code-review/context.md`
- Synthesized report path: `{{artifact_root}}/code-review/review-report.md`
- Review-fix summary path: `{{artifact_root}}/code-review/apply-summary.md`

Record those paths on the workflow root as:

- `gc.build.code_review_context_path`
- `gc.build.code_review_report_path`
- `gc.build.review_fix_summary_path`
- `gc.build.code_review_status=ready`

Close this setup step with `gc.outcome=pass` only after the context file exists
and the root metadata points at all three paths.

Do not invoke provider-native subagents or upstream plugin runtime commands.
This graph stage is the delegation mechanism.
