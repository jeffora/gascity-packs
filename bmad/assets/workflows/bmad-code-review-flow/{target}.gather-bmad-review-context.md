Gather BMAD code-review context.

Use the installed `bmad-code-review` skill as guidance. Resolve the
implementation summary, changed files, diff base, PRD, architecture,
epics/stories, test evidence, and artifact root.

Create `{{artifact_root}}/code-review/` if needed. Write:

- Review context: `{{artifact_root}}/code-review/context.md`
- Synthesized report path: `{{artifact_root}}/code-review/review-report.md`
- Review-fix summary path: `{{artifact_root}}/code-review/apply-summary.md`

Record those paths on the workflow root as:

- `gc.build.code_review_context_path`
- `gc.build.code_review_report_path`
- `gc.build.review_fix_summary_path`
- `gc.build.code_review_status=ready`

Close this setup lane with `gc.outcome=pass` only after the context file exists
and the root metadata points at all three paths.

Do not invoke provider-native subagents. This graph lane is the delegation mechanism.
