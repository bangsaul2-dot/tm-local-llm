"""Synthetic-only integration tests: endpoint angle, 11/12/13 px and 4-wire bus."""
import unittest
from adapter_contract import adaptive_snap
from hybrid_fusion import fuse_grounded

def fixture(offset=12, tangent=False):
    nodes=[{"name":"Alpha","kind":"leaf","bbox":[0,0,30,40]},
           {"name":"Beta","kind":"leaf","bbox":[100,0,130,40]}]
    semantic={"edges":[{"from":"Alpha","to":"Beta","direction":"forward"}]}
    wires=[]
    for i in range(4):
        y=10+i*5
        points=[[30+offset,y],[100-offset,y]]
        if tangent and i==0:
            points=[[30+offset,y-2],[30+offset,y],[100-offset,y]]
        wires.append({"id":f"w{i}","points":points,"bus_group_id":"bus_0",
                      "arrow_direction":"forward","trace_verified":True,
                      "arrowhead_tip":[75,y],"arrowhead_base":[70,y]})
    return semantic,{"wires":wires},nodes

class AngleIntegrationTests(unittest.TestCase):
    def test_four_wire_candidate_preserved(self):
        output=fuse_grounded(*fixture(12))
        edge=output["edges"][0]
        self.assertEqual(edge["status"],"candidate")
        self.assertEqual(edge["wire_ids"],["w0","w1","w2","w3"])
        self.assertEqual(edge["bus_group_ids"],["bus_0"])
        self.assertEqual(edge["review_state"],"needs_review")
        self.assertFalse(edge["source_verified"])

    def test_boundary_11_12_13(self):
        nodes=[{"name":"Alpha","kind":"leaf","bbox":[0,0,30,40]}]
        for distance, expected in [(11,"matched"),(12,"matched"),(13,"unmatched")]:
            with self.subTest(distance=distance):
                self.assertEqual(adaptive_snap([30+distance,20],nodes,
                    incoming_vector=[-1,0])["status"],expected)

    def test_tangent_abstains(self):
        nodes=[{"name":"Alpha","kind":"leaf","bbox":[0,0,30,40]}]
        self.assertEqual(adaptive_snap([42,20],nodes,
            incoming_vector=[0,1])["status"],"ambiguous_angle")

    def test_zero_length_segment_abstains(self):
        semantic,geometry,nodes=fixture()
        geometry["wires"][0]["points"]=[[42,10],[42,10]]
        output=fuse_grounded(semantic,geometry,nodes)
        self.assertEqual(output["wires"][0]["a_status"],"ambiguous_angle")
        self.assertNotIn("w0",output["edges"][0]["wire_ids"])

    def test_angle_failure_blocks_unverified_edge(self):
        semantic,geometry,nodes=fixture()
        for w in geometry["wires"]:
            w["points"]=[[42,10],[42,10]]
        output=fuse_grounded(semantic,geometry,nodes)
        self.assertEqual(output["edges"][0]["status"],"ambiguous")
        self.assertIn("endpoint_angle_unverified",output["edges"][0]["reasons"])

if __name__=="__main__":
    unittest.main()
