from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets" / "scripts"))

import github_reports


class GitHubReportsTests(unittest.TestCase):
    def test_validate_triage_report_accepts_expected_front_matter(self) -> None:
        report = """---
schema: gc.github-issue-triage-report.v1
repo: owner/repo
issue_number: 123
body_hash: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
verdict: reproduced
priority: p1
recommended_next_action: fix
reproduction_artifact_path: logs/repro.txt
reproduction_diff_path: repro.patch
---

Reproduction details.
"""

        parsed = github_reports.validate_triage_report_text(
            report,
            expected_repo="owner/repo",
            expected_issue_number=123,
            expected_body_hash="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )

        self.assertEqual(parsed.verdict, "reproduced")
        self.assertEqual(parsed.recommended_next_action, "fix")

    def test_validate_triage_report_rejects_bad_actions_and_mismatches(self) -> None:
        report = """---
schema: gc.github-issue-triage-report.v1
repo: owner/repo
issue_number: 123
body_hash: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
verdict: needs_info
priority: p2
recommended_next_action: fix
---
"""

        with self.assertRaisesRegex(github_reports.ValidationError, "recommended_next_action"):
            github_reports.validate_triage_report_text(report)
        with self.assertRaisesRegex(github_reports.ValidationError, "repo"):
            github_reports.validate_triage_report_text(report.replace("fix", "ask_reporter"), expected_repo="other/repo")

    def test_validate_triage_report_requires_analysis_body(self) -> None:
        report = """---
schema: gc.github-issue-triage-report.v1
repo: owner/repo
issue_number: 123
body_hash: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
verdict: needs_info
priority: p2
recommended_next_action: ask_reporter
---
"""

        with self.assertRaisesRegex(github_reports.ValidationError, "analysis body"):
            github_reports.validate_triage_report_text(report)

    def test_review_outcome_maps_generic_verdicts_to_comment_outcomes(self) -> None:
        self.assertEqual(github_reports.review_outcome("pass", "none"), "approve")
        self.assertEqual(github_reports.review_outcome("fail", "minor"), "comment")
        self.assertEqual(github_reports.review_outcome("fail", "major"), "request_changes")
        self.assertEqual(github_reports.review_outcome("fail", "blocker"), "block")

        with self.assertRaises(github_reports.ValidationError):
            github_reports.review_outcome("pass", "minor")

    def test_renderers_write_sticky_marker_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            review_path = root / "review.md"
            review_path.write_text(
                "---\n"
                "schema: gc.verdict-report.v1\n"
                "kind: review\n"
                "verdict: fail\n"
                "severity: major\n"
                "findings:\n"
                "  - id: rev-1\n"
                "    severity: major\n"
                "    title: Missing test\n"
                "    evidence: No test.\n"
                "    required_fix: Add one.\n"
                "---\n",
                encoding="utf-8",
            )
            review_comment = github_reports.render_pr_review_comment(
                review_path,
                outcome="request_changes",
                head_sha="abc123",
                artifact_ref="artifact",
                human_approved=True,
            )
            triage_path = root / "triage.md"
            triage_path.write_text(
                "---\n"
                "schema: gc.github-issue-triage-report.v1\n"
                "repo: owner/repo\n"
                "issue_number: 123\n"
                "body_hash: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
                "verdict: needs_info\n"
                "priority: p2\n"
                "recommended_next_action: ask_reporter\n"
                "---\n"
                "\n"
                "## Summary\n"
                "\n"
                "The issue needs a missing reproduction detail.\n"
                "\n"
                "## Evidence\n"
                "\n"
                "- The report did not include the failing command.\n",
                encoding="utf-8",
            )
            triage_comment = github_reports.render_triage_comment(
                triage_path,
                artifact_ref="artifact",
                human_approved=False,
            )
            status_comment = github_reports.render_issue_fix_status(
                state="implementation_started",
                summary="Build is running.",
                run_id="run-1",
                pr_url="https://github.com/owner/repo/pull/9",
                artifact_ref="artifact",
            )

        self.assertIn("<!-- gc:github-pr-review", review_comment)
        self.assertIn("outcome: request_changes", review_comment)
        self.assertIn("human approved", review_comment)
        self.assertIn("<!-- gc:github-issue-triage", triage_comment)
        self.assertIn("sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", triage_comment)
        self.assertIn("needs_info", triage_comment)
        self.assertIn("## Analysis", triage_comment)
        self.assertIn("### Summary", triage_comment)
        self.assertIn("The issue needs a missing reproduction detail.", triage_comment)
        self.assertIn("<!-- gc:github-issue-fix-status", status_comment)
        self.assertIn("implementation_started", status_comment)
        self.assertIn("https://github.com/owner/repo/pull/9", status_comment)

    def test_unapproved_security_triage_comment_redacts_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            triage_path = pathlib.Path(tmp) / "triage.md"
            triage_path.write_text(
                "---\n"
                "schema: gc.github-issue-triage-report.v1\n"
                "repo: owner/repo\n"
                "issue_number: 123\n"
                "body_hash: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
                "verdict: security_sensitive\n"
                "priority: p1\n"
                "recommended_next_action: security_process\n"
                "---\n"
                "\n"
                "## Summary\n"
                "\n"
                "Sensitive exploit detail.\n",
                encoding="utf-8",
            )

            triage_comment = github_reports.render_triage_comment(
                triage_path,
                human_approved=False,
            )

        self.assertIn("security-sensitive details require human approval", triage_comment)
        self.assertNotIn("Sensitive exploit detail", triage_comment)


if __name__ == "__main__":
    unittest.main()
