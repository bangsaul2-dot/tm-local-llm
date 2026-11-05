"""Synthetic graph safety tests only."""
import unittest
from graph_safety import check_graph

class GraphSafetyTests(unittest.TestCase):
    def test_candidate_is_never_approved(self):
        graph = {"nodes":[{"id":"A"},{"id":"B"}],
                 "edges":[{"id":"e1","from":"A","to":"B",
                           "from_port_direction":"out","to_port_direction":"in",
                           "evidence_status":"proposed"}]}
        self.assertEqual(check_graph(graph)["approved_edge_count"], 0)

    def test_bad_direction_rejected(self):
        graph = {"nodes":[{"id":"A"},{"id":"B"}],
                 "edges":[{"id":"e1","from":"A","to":"B",
                           "from_port_direction":"in","to_port_direction":"out",
                           "evidence_status":"proposed"}]}
        self.assertIn("invalid_source_port_direction",
                      check_graph(graph)["results"][0]["reasons"])

    def test_unreviewed_claim_not_approved(self):
        graph = {"nodes":[{"id":"A"},{"id":"B"}],
                 "edges":[{"id":"e1","from":"A","to":"B",
                           "from_port_direction":"out","to_port_direction":"in",
                           "evidence_status":"source_verified",
                           "source_ref":"public_example.pdf p.2"}]}
        self.assertEqual(check_graph(graph)["approved_edge_count"], 0)

if __name__ == "__main__":
    unittest.main()
