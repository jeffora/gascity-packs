Review the plan with the installed Compound Engineering scope reviewer persona.

Check that every proposed unit is right-sized, traceable to requirements, and free of unearned abstractions or quiet scope creep. Keep findings actionable for the plan author.

Read the review context from workflow root metadata
`gc.build.plan_review_context_path`. Write this lane's report to
`<artifact_root>/plan-review/scope-review.md` and close with
`gc.outcome=pass`, `design_review.scope_verdict=approve|iterate`, and
`design_review.scope_report_path=<artifact path>`.

Do not invoke provider-native subagents. You are the Gas City lane for this persona.
