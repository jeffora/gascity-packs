Review agent-native parity with the installed Compound Engineering
agent-native reviewer.

Use the same code-review context as the persona lanes. Verify whether new
features, prompts, tools, or workflows remain accessible to agents through
Gas City primitives. If the stock CE applicability does not reveal relevant
agent-facing surface area, write a no-op artifact that explains why.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/agent-native.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the Gas City lane for this CE
agent.
