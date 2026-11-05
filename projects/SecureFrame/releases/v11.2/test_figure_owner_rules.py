"""Synthetic-only tests."""
import unittest
from figure_owner_rules import assign_owner

class RoutingTests(unittest.TestCase):
    def test_single_owner(self):
        result = assign_owner([{"id":"f1","title":"Example diagram"}],
                              [{"name":"Chapter A"}],
                              [{"pattern":"Example","owner_topic":"Chapter A"}])
        self.assertEqual(result[0]["candidate_owner"], "Chapter A")
        self.assertEqual(result[0]["status"], "needs_review")
    def test_conflict(self):
        result = assign_owner([{"id":"f1","title":"Example"}],
                              [{"name":"A"},{"name":"B"}],
                              [{"pattern":"Example","owner_topic":"A"},
                               {"pattern":"Example","owner_topic":"B"}])
        self.assertTrue(result[0]["conflict"])
        self.assertIsNone(result[0]["candidate_owner"])

if __name__ == "__main__":
    unittest.main()
