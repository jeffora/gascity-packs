Review the plan with the installed Compound Engineering coherence reviewer
persona.

Check for internal contradictions, unresolved references, terminology drift, and ambiguity that would make implementers diverge. Return findings in the build review artifact format consumed by synthesis.

Read the review context from workflow root metadata
`gc.build.plan_review_context_path`. Write this lane's report to
`<artifact_root>/plan-review/coherence-review.md` and close with
`gc.outcome=pass`, `design_review.coherence_verdict=approve|iterate`, and
`design_review.coherence_report_path=<artifact path>`.

Do not invoke provider-native subagents. You are the Gas City lane for this persona.
