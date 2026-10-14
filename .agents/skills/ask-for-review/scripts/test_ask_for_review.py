import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ask_for_review


class LinearIssueGroupingTests(unittest.TestCase):
    def test_extracts_issue_key_from_branch_case_insensitively(self):
        pr = {
            "number": 1,
            "headRefName": "feature/eng-123",
            "title": "Add review flow",
            "body": "",
        }

        self.assertEqual(ask_for_review.linear_issue_key(pr), "ENG-123")

    def test_falls_back_to_issue_key_in_body(self):
        pr = {
            "number": 2,
            "headRefName": "feature/review-flow",
            "title": "Add review flow",
            "body": "https://linear.app/pilah/issue/MOB-42/review-flow",
        }

        self.assertEqual(ask_for_review.linear_issue_key(pr), "MOB-42")

    def test_rejects_ambiguous_issue_keys(self):
        pr = {
            "number": 3,
            "headRefName": "feature/review-flow",
            "title": "Add review flow",
            "body": "Related to ENG-123 and MOB-42",
        }

        with self.assertRaises(ask_for_review.UserError):
            ask_for_review.linear_issue_key(pr)

    def test_groups_matching_issue_keys_and_keeps_unlinked_prs_separate(self):
        pull_requests = [
            {"issue_key": "ENG-123", "url": "be", "area": "BE"},
            {"issue_key": "ENG-123", "url": "mobile", "area": "MOB"},
            {"issue_key": "ENG-456", "url": "other-issue", "area": "BE"},
            {"issue_key": None, "url": "unlinked-1", "area": "MOB"},
            {"issue_key": None, "url": "unlinked-2", "area": "BE"},
        ]

        groups = ask_for_review.group_pull_requests(pull_requests)

        self.assertEqual(
            [key for key, _ in groups], ["ENG-123", "ENG-456", None, None]
        )
        self.assertEqual([len(prs) for _, prs in groups], [2, 1, 1, 1])

    def test_message_lists_both_areas_and_pr_links(self):
        pull_requests = [
            {
                "issue_key": "ENG-123",
                "url": "https://github.com/pilah/pilah-be/pull/2",
                "area": "BE",
                "title": "Backend changes",
            },
            {
                "issue_key": "ENG-123",
                "url": "https://github.com/pilah/pilah-mobile/pull/3",
                "area": "MOB",
                "title": "Mobile changes",
            },
        ]

        content = ask_for_review.message_content(
            "ENG-123",
            pull_requests,
            ask_for_review.Member("TrayMachi", "1", "traymachi"),
            [ask_for_review.Member("alghani46", "2", "baller3839")],
        )

        self.assertIn("[MOB] [BE] changes for ENG-123", content)
        self.assertIn("MOB PR: https://github.com/pilah/pilah-mobile/pull/3", content)
        self.assertIn("BE PR: https://github.com/pilah/pilah-be/pull/2", content)


if __name__ == "__main__":
    unittest.main()
