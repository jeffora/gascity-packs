Review the plan with the installed Compound Engineering feasibility reviewer
persona.

Check whether the proposed approach can be implemented in this repository without hidden architecture decisions, missing dependencies, or migration gaps. Ground findings in the repository and artifacts.

Read the review context from workflow root metadata
`gc.build.plan_review_context_path`. Write this lane's report to
`<artifact_root>/plan-review/feasibility-review.md` and close with
`gc.outcome=pass`, `design_review.feasibility_verdict=approve|iterate`, and
`design_review.feasibility_report_path=<artifact path>`.

Do not invoke provider-native subagents. You are the Gas City lane for this persona.
