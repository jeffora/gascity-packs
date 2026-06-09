Apply required Superpowers spec-review feedback to the requirements artifact.

If the review approved the artifact, perform a no-op pass and record that no
changes were needed. If the review found required issues, update only the
requirements/spec artifact and any companion brainstorming notes needed to
resolve them. Preserve traceability to the original target and do not add
unrequested scope.

For every attempt, write an apply summary and, when the artifact changed, a
diff. Close with `gc.outcome=pass`, `design_review.output_path=<apply-summary
path>`, and metadata stating whether required changes were applied. Do not set
`design_review.verdict`; the approval lane owns the loop verdict.

Do not invoke provider-native subagents. This Gas City lane owns the spec
feedback pass.
