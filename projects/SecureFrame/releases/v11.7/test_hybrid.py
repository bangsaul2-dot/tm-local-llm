"""Synthetic-only tests. No proprietary samples."""
import unittest
from hybrid import validate_semantic, fuse, evaluate

class HybridTests(unittest.TestCase):
    def test_no_llm_coordinates(self):
        with self.assertRaises(ValueError):
            validate_semantic({"nodes":[{"name":"A","kind":"leaf","parent":None,"bbox":[0,0,1,1]}],"edges":[]})

    def test_parent_cycle(self):
        with self.assertRaises(ValueError):
            validate_semantic({"nodes":[{"name":"A","kind":"container","parent":"B"},{"name":"B","kind":"container","parent":"A"}],"edges":[]})

    def test_grounded_forward(self):
        semantic={"nodes":[{"name":"Alpha","kind":"leaf","parent":None},{"name":"Beta","kind":"leaf","parent":None}],
                  "edges":[{"from":"Alpha","to":"Beta","direction":"forward"}]}
        geometry={"boxes":[{"bbox":[0,0,30,30]},{"bbox":[100,0,130,30]}],
                  "ocr":[{"text":"Alpha","bbox":[3,3,20,12]},{"text":"Beta","bbox":[103,3,120,12]}],
                  "wires":[{"id":"w1","points":[[30,15],[100,15]],"arrow_direction":"forward","trace_verified":True}]}
        result=fuse(semantic,geometry)
        self.assertEqual(result["edges"][0]["status"],"candidate")
        self.assertTrue(evaluate(result,{"edges":[{"from":"Alpha","to":"Beta","direction":"forward"}]})["pass_90"])
        geometry["wires"][0]["arrow_direction"]="reverse"
        self.assertIn("direction_conflict",fuse(semantic,geometry)["edges"][0]["reasons"])

    def test_untraced_not_approved(self):
        semantic={"nodes":[],"edges":[]}
        self.assertEqual(fuse(semantic,{"boxes":[],"ocr":[],"wires":[]})["edges"],[])

if __name__=="__main__":
    unittest.main()
