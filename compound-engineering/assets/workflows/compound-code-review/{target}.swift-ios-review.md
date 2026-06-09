Review Swift and iOS risk with the installed Compound Engineering Swift iOS
persona.

This bead only runs after the cheap conditional gate selected Swift/iOS review
for this change. Inspect Swift, SwiftUI, UIKit, iOS entitlements, privacy
manifests, Core Data, package manifests, storyboards, XIBs, or semantic project
settings and return structured findings for synthesis. Do not re-run
applicability as a no-op; skipped Swift/iOS lanes are closed by the gate.

Read `gc.build.code_review_context_path` from the workflow root. Write this lane
artifact to `{{artifact_root}}/code-review/swift-ios.md`. Close with
`gc.outcome=pass`, `code_review.review_verdict=approve|iterate`, and
`code_review.lane_report_path=<lane artifact path>`. Do not set
`code_review.verdict` or `code_review.report_path`; the apply-review-findings
lane owns the final loop verdict consumed by the approval check.

Do not invoke provider-native subagents. You are the Gas City lane for this
conditional persona.
