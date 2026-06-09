Research prior learnings with the installed Compound Engineering learnings
researcher.

Search the review context and local documentation for applicable past findings,
solutions, and conventions related to the touched modules. Preserve useful
unstructured learnings for synthesis. If no relevant knowledge base exists or
no applicable learning is found, write a no-op artifact that says so.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/learnings-research.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the Gas City lane for this CE
agent.
