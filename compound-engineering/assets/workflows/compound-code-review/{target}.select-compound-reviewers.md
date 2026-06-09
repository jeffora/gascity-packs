Select the Compound Engineering conditional code-review lanes.

Read the review context from workflow root metadata
`gc.build.code_review_context_path`. Preserve the stock CE reviewer-selection
intent by selecting conditional lanes with model judgment over the context
bundle, diff, changed files, PR metadata, and prior comments. Do not use simple
keyword matching.

Always keep these Gas City lanes active: correctness, testing,
maintainability, project standards, agent-native parity, learnings research,
and gap analysis.

For each conditional lane, record whether it is selected or skipped:

- security
- performance
- API contract
- data migration
- reliability
- adversarial
- previous comments
- Julik frontend races
- Swift iOS
- deployment verification

Write the reviewer manifest to
`{{artifact_root}}/code-review/reviewer-selection.json`. Update workflow root
metadata with:

- `gc.build.reviewer_selection_path=<manifest path>`
- `gc.build.selected_reviewers=<comma-separated always-on plus selected conditional keys>`
- `gc.build.skipped_reviewers=<comma-separated skipped conditional keys>`
- `gc.build.reviewer_selection_status=ready`

Close with `gc.outcome=pass` only after the manifest exists and all conditional
keys appear exactly once as selected or skipped.

Do not invoke provider-native subagents. This Gas City lane performs the CE
reviewer-selection step.
