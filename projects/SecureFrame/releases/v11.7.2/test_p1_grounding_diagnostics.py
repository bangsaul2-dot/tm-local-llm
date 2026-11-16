"""Synthetic-only tests for privacy-safe grounding diagnostics."""
import json
import unittest
from copy import deepcopy
from p1_grounding_diagnostics import diagnose_grounding

class Tests(unittest.TestCase):
    def test_no_ocr_and_no_leak(self):
        semantic={"nodes":[{"name":"SecretAlpha","kind":"leaf","parent":None}],
                  "edges":[]}
        geometry={"boxes":[{"bbox":[0,0,20,20]}],"ocr":[]}
        grounded=[{"name":"SecretAlpha","kind":"leaf","parent":None,
                   "bbox":None,"box_index":None,"grounding":"needs_review"}]
        before=deepcopy((semantic,geometry,grounded))
        result=diagnose_grounding(semantic,geometry,grounded)
        self.assertEqual(result["unmatched_reason_counts"]["no_ocr_in_boxes"],1)
        self.assertNotIn("SecretAlpha",json.dumps(result))
        self.assertNotIn("bbox",json.dumps(result))
        self.assertEqual((semantic,geometry,grounded),before)
        self.assertFalse(result["auto_approval"])
    def test_low_similarity(self):
        s={"nodes":[{"name":"Alpha","kind":"leaf","parent":None}],"edges":[]}
        g={"boxes":[{"bbox":[0,0,20,20]}],
           "ocr":[{"text":"zzz","bbox":[1,1,10,10]}]}
        n=[{"grounding":"needs_review"}]
        r=diagnose_grounding(s,g,n)
        self.assertEqual(r["unmatched_reason_counts"]["low_text_similarity"],1)
    def test_competing_boxes(self):
        s={"nodes":[{"name":"Alpha","kind":"leaf","parent":None}],"edges":[]}
        g={"boxes":[{"bbox":[0,0,20,20]},{"bbox":[30,0,50,20]}],
           "ocr":[{"text":"Alpha","bbox":[1,1,10,10]},
                  {"text":"Alpha","bbox":[31,1,40,10]}]}
        r=diagnose_grounding(s,g,[{"grounding":"needs_review"}])
        self.assertEqual(r["unmatched_reason_counts"]["competing_boxes"],1)
    def test_container_endpoints_flagged(self):
        s={"nodes":[{"name":"Group","kind":"container","parent":None},
                    {"name":"A","kind":"leaf","parent":"Group"}],
           "edges":[{"from":"Group","to":"A","direction":"unknown"}]}
        g={"boxes":[],"ocr":[]}
        r=diagnose_grounding(s,g,[{"grounding":"needs_review"}]*2)
        self.assertEqual(r["container_endpoint_occurrences"],1)
        self.assertEqual(r["node_kind_counts"],{"leaf":1,"container":1})
    def test_bad_lengths(self):
        with self.assertRaises(ValueError):
            diagnose_grounding({"nodes":[{}],"edges":[]},{"boxes":[],"ocr":[]},[])

if __name__=="__main__":unittest.main()
