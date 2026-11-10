"""Synthetic regression tests for V11.7.1. No customer data."""
import unittest
from hybrid_bus import validate_semantic, ground_nodes, snap_endpoint, fuse, evaluate

def fixture(arrows=None, bus_id="bus1"):
    arrows = arrows or ["forward", "forward", "forward"]
    semantic = {
        "nodes": [{"name": "Alpha", "kind": "leaf", "parent": None},
                  {"name": "Beta", "kind": "leaf", "parent": None}],
        "edges": [{"from": "Alpha", "to": "Beta", "direction": "forward"}]}
    geometry = {
        "boxes": [{"bbox": [0, 0, 30, 30]}, {"bbox": [100, 0, 130, 30]}],
        "ocr": [{"text": "Alpha", "bbox": [3, 3, 22, 12]},
                {"text": "Beta", "bbox": [103, 3, 120, 12]}],
        "wires": [{"id": "wire_%02d" % i, "points": [[30, 12+i*4], [100, 12+i*4]],
                   "arrow_direction": arrow, "trace_verified": True,
                   "bus_group_id": bus_id}
                  for i, arrow in enumerate(arrows)]}
    return semantic, geometry

class HybridBusTests(unittest.TestCase):
    def test_three_parallel_wires_one_logical_edge(self):
        semantic, geometry = fixture()
        output = fuse(semantic, geometry)
        self.assertEqual(output["edges"][0]["status"], "candidate")
        self.assertEqual(len(output["edges"][0]["wire_ids"]), 3)
        self.assertEqual(output["edges"][0]["bus_group_ids"], ["bus1"])
        self.assertFalse(output["edges"][0]["source_verified"])

    def test_conflicting_arrow_abstains(self):
        semantic, geometry = fixture(["forward", "reverse", "forward"])
        edge = fuse(semantic, geometry)["edges"][0]
        self.assertEqual(edge["status"], "ambiguous")
        self.assertIn("direction_conflict_between_wires", edge["reasons"])

    def test_unknown_arrow_abstains(self):
        semantic, geometry = fixture(["forward", "unknown", "forward"])
        self.assertEqual(fuse(semantic, geometry)["edges"][0]["status"], "ambiguous")

    def test_no_auto_approval(self):
        semantic, geometry = fixture()
        edge = fuse(semantic, geometry)["edges"][0]
        self.assertEqual(edge["review_state"], "needs_review")
        self.assertEqual(edge["evidence_status"], "candidate")

    def test_llm_coordinates_rejected(self):
        semantic, _ = fixture()
        semantic["nodes"][0]["bbox"] = [0, 0, 30, 30]
        with self.assertRaises(ValueError):
            validate_semantic(semantic)

    def test_empty_gt_not_evaluable(self):
        semantic, geometry = fixture()
        self.assertFalse(evaluate(fuse(semantic, geometry), {"edges": []})["pass_90"])

    def test_synthetic_gt_pass(self):
        semantic, geometry = fixture()
        result = evaluate(fuse(semantic, geometry),
                          {"edges": [{"from": "Alpha", "to": "Beta", "direction": "forward"}]})
        self.assertTrue(result["pass_90"])

    def test_competitor_snap_abstains(self):
        nodes = [{"name": "A", "kind": "leaf", "bbox": [0,0,10,10]},
                 {"name": "B", "kind": "leaf", "bbox": [10,0,20,10]}]
        self.assertEqual(snap_endpoint([10,5], nodes)["status"], "ambiguous_endpoint")

    def test_container_endpoint_blocked(self):
        semantic, geometry = fixture()
        semantic["nodes"][0]["kind"] = "container"
        self.assertEqual(fuse(semantic, geometry)["edges"][0]["status"], "ambiguous")

    def test_ocr_tokens_merged(self):
        semantic, geometry = fixture()
        semantic["nodes"][0]["name"] = "Alpha Unit"
        semantic["edges"][0]["from"] = "Alpha Unit"
        geometry["ocr"][0] = {"text": "Alpha", "bbox": [3,3,18,12]}
        geometry["ocr"].append({"text": "Unit", "bbox": [19,3,29,12]})
        self.assertEqual(ground_nodes(semantic, geometry)[0]["grounding"], "grounded")

if __name__ == "__main__":
    unittest.main()
