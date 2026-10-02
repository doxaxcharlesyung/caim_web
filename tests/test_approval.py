import unittest
from unittest.mock import patch

from app.approval import OWNER_APPROVER_USERNAMES, validate_reviewers


class ApprovalRuleTests(unittest.TestCase):
    @patch("app.approval.can_approve_own_content", return_value=True)
    @patch(
        "app.approval.available_reviewers",
        return_value=[{"id": 10, "username": "charles.yung"}, {"id": 20, "username": "francis.lau"}],
    )
    def test_owner_can_select_themselves(self, available_reviewers, can_approve_own_content):
        self.assertEqual(validate_reviewers(10, ["10"]), [10])

    @patch("app.approval.can_approve_own_content", return_value=False)
    @patch(
        "app.approval.available_reviewers",
        return_value=[{"id": 20, "username": "francis.lau"}],
    )
    def test_non_owner_cannot_select_themselves(self, available_reviewers, can_approve_own_content):
        with self.assertRaisesRegex(ValueError, "other than the content creator"):
            validate_reviewers(10, ["10"])

    def test_allowlist_contains_only_the_two_owner_approvers(self):
        self.assertEqual(OWNER_APPROVER_USERNAMES, {"charles.yung", "francis.lau"})


if __name__ == "__main__":
    unittest.main()
