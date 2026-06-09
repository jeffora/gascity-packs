Audit BMAD story acceptance.

Compare the implementation against the PRD, architecture, epics/stories, and Given/When/Then acceptance criteria. Check test evidence and flag missing, extra, or misunderstood behavior.

Write the acceptance-audit report under `{{artifact_root}}/bmad-story-development/`
and close with `gc.outcome=pass`,
`bmad_story.acceptance_audit_report_path=<report path>`, and
`bmad_story.acceptance_required_findings=<count>`. If the story cannot be
audited because required artifacts or the worktree are missing, close with
`gc.outcome=fail` instead of inventing a result.

Do not invoke provider-native subagents. You are the acceptance audit lane.
