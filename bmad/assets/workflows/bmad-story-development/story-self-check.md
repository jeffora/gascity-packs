Run the BMAD story self-check.

Use the installed `bmad-dev-story` skill and quick-dev self-check rules to
verify that every task and acceptance criterion is complete. Record missing work
as required findings.

Write the self-check report under `{{artifact_root}}/bmad-story-development/`
and close with `gc.outcome=pass`,
`bmad_story.self_check_report_path=<report path>`, and
`bmad_story.self_check_required_findings=<count>`. If the story cannot be
checked because required artifacts or the worktree are missing, close with
`gc.outcome=fail` instead of inventing a result.

Do not invoke provider-native subagents. You are the self-check lane.
