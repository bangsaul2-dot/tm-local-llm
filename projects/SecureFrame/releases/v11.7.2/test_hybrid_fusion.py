import unittest
from hybrid_fusion import fuse_grounded

class FusionTests(unittest.TestCase):
    def fixture(self):
        nodes=[{"name":"Alpha","kind":"leaf","bbox":[0,0,30,40]},
               {"name":"Beta","kind":"leaf","bbox":[100,0,130,40]}]
        semantic={"edges":[{"from":"Alpha","to":"Beta","direction":"forward"}]}
        geometry={"wires":[{"id":f"w{i}","points":[[42,10+i*5],[88,10+i*5]],
                            "bus_id":"bus_0","trace_verified":True,
                            "arrow_direction":"forward",
                            "arrowhead_tip":[80,10+i*5],
                            "arrowhead_base":[75,10+i*5]} for i in range(4)]}
        return semantic,geometry,nodes
    def test_four_parallel_wires(self):
        result=fuse_grounded(*self.fixture())
        edge=result["edges"][0]
        self.assertEqual(edge["status"],"candidate")
        self.assertEqual(edge["wire_ids"],["w0","w1","w2","w3"])
        self.assertEqual(edge["bus_group_ids"],["bus_0"])
        self.assertFalse(edge["source_verified"])
    def test_multi_bus_abstains(self):
        s,g,n=self.fixture()
        g["wires"][0]["bus_id"]="bus_1"
        self.assertIn("multiple_bus_groups_require_review",fuse_grounded(s,g,n)["edges"][0]["reasons"])
    def test_arrow_conflict_abstains(self):
        s,g,n=self.fixture()
        g["wires"][0]["arrowhead_tip"]=[75,10]
        g["wires"][0]["arrowhead_base"]=[80,10]
        self.assertIn("arrow_geometry_conflict",fuse_grounded(s,g,n)["edges"][0]["reasons"])
    def test_unknown_arrow_abstains(self):
        s,g,n=self.fixture()
        g["wires"][0].pop("arrowhead_tip")
        g["wires"][0].pop("arrowhead_base")
        g["wires"][0]["arrow_direction"]="unknown"
        self.assertIn("direction_partially_unverified",fuse_grounded(s,g,n)["edges"][0]["reasons"])

if __name__ == "__main__": unittest.main()
