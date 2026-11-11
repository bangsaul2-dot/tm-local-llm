"""Synthetic-only axis-first snap regression gates. No SFT geometry included."""
import unittest
from adapter_contract import adaptive_snap
from hybrid_fusion import fuse_grounded

class AxisSnapRCTests(unittest.TestCase):
    def test_corner_horizontal_uses_x_face(self):
        nodes=[{"name":"A","kind":"leaf","bbox":[0,0,30,40]}]
        out=adaptive_snap([42,-1],nodes,incoming_vector=[-1,0])
        self.assertEqual(out["status"],"matched")
        self.assertEqual(out["axis"],"horizontal")
    def test_top_offset_horizontal_reaches_x_face(self):
        nodes=[{"name":"A","kind":"leaf","bbox":[0,0,30,40]}]
        out=adaptive_snap([42,-12],nodes,incoming_vector=[-1,0])
        self.assertEqual(out["status"],"matched")
        self.assertEqual(out["cross_axis_offset"],12)
    def test_true_tangent_far_from_x_face_abstains(self):
        nodes=[{"name":"A","kind":"leaf","bbox":[0,0,100,40]}]
        self.assertEqual(adaptive_snap([50,-1],nodes,incoming_vector=[1,0])["status"],"unmatched")
    def test_competitor_remains_ambiguous(self):
        nodes=[{"name":"A","kind":"leaf","bbox":[0,0,30,40]},
               {"name":"B","kind":"leaf","bbox":[54,0,84,40]}]
        self.assertEqual(adaptive_snap([42,20],nodes,incoming_vector=[1,0])["status"],"ambiguous_endpoint")
    def test_four_wire_candidate(self):
        nodes=[{"name":"A","kind":"leaf","bbox":[0,0,30,40]},
               {"name":"B","kind":"leaf","bbox":[100,0,130,40]}]
        semantic={"edges":[{"from":"A","to":"B","direction":"forward"}]}
        wires=[]
        for i in range(4):
            y=[-1,5,15,-12][i]
            wires.append({"id":f"w{i}","points":[[42,y],[88,y]],
                          "bus_group_id":"bus_0","arrow_direction":"forward",
                          "trace_verified":True,
                          "arrowhead_tip":[80,y],"arrowhead_base":[75,y]})
        out=fuse_grounded(semantic,{"wires":wires},nodes)
        self.assertEqual(out["edges"][0]["status"],"candidate")
        self.assertEqual(out["edges"][0]["wire_ids"],["w0","w1","w2","w3"])
        self.assertEqual(out["edges"][0]["bus_group_ids"],["bus_0"])
        self.assertFalse(out["edges"][0]["source_verified"])
    def test_boundary(self):
        nodes=[{"name":"A","kind":"leaf","bbox":[0,0,30,40]}]
        for distance, expected in [(11,"matched"),(12,"matched"),(13,"unmatched")]:
            with self.subTest(distance=distance):
                self.assertEqual(adaptive_snap([30+distance,20],nodes,incoming_vector=[-1,0])["status"],expected)

if __name__=="__main__":
    unittest.main()
