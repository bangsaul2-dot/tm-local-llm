import unittest
from adapter_contract import normalize_wire, normalize_geometry, adaptive_snap, arrow_from_tip_base

class AdapterTests(unittest.TestCase):
    def wire(self, **extra):
        return dict(id="w1", points=[[0, 0], [100, 0]], arrow_direction="forward",
                    trace_verified=True, **extra)
    def test_alias(self):
        self.assertEqual(normalize_wire(self.wire(bus_id="bus_0"))["bus_group_id"], "bus_0")
    def test_alias_conflict(self):
        with self.assertRaises(ValueError):
            normalize_wire(self.wire(bus_id="bus_0", bus_group_id="bus_1"))
    def test_tip_forward(self):
        self.assertEqual(arrow_from_tip_base([[0,0],[100,0]],[95,0],[90,0]), "forward")
    def test_tip_reverse(self):
        self.assertEqual(arrow_from_tip_base([[0,0],[100,0]],[5,0],[10,0]), "reverse")
    def test_tip_perpendicular_unknown(self):
        self.assertEqual(arrow_from_tip_base([[0,0],[100,0]],[95,5],[95,0]), "unknown")
    def test_direction_conflict(self):
        wire = normalize_wire(self.wire(arrowhead_tip=[5,0], arrowhead_base=[10,0]))
        self.assertTrue(wire["direction_conflict"])
        self.assertEqual(wire["arrow_direction"], "unknown")
    def test_missing_trace_not_promoted(self):
        w = self.wire(); w.pop("trace_verified")
        self.assertFalse(normalize_wire(w)["trace_verified"])
    def test_adaptive_twelve_pixels(self):
        nodes = [dict(name="A",kind="leaf",bbox=[0,0,100,40])]
        self.assertEqual(adaptive_snap([112,20],nodes)["name"],"A")
    def test_nearby_competitor_abstain(self):
        nodes = [dict(name="A",kind="leaf",bbox=[0,0,100,40]),
                 dict(name="B",kind="leaf",bbox=[120,0,220,40])]
        self.assertEqual(adaptive_snap([110,20],nodes)["status"],"ambiguous_endpoint")
    def test_container_ignored(self):
        nodes = [dict(name="A",kind="container",bbox=[0,0,100,40])]
        self.assertEqual(adaptive_snap([100,20],nodes)["status"],"unmatched")
    def test_tangent_abstains(self):
        nodes = [dict(name="A",kind="leaf",bbox=[0,0,100,40])]
        self.assertEqual(adaptive_snap([112,20],nodes,incoming_vector=[0,1])["status"],"unmatched")
    def test_duplicate_wire(self):
        with self.assertRaises(ValueError):
            normalize_geometry({"wires":[self.wire(),self.wire()]})

if __name__ == "__main__":
    unittest.main()
