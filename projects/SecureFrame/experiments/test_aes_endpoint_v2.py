"""Synthetic-only endpoint v2 regression."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from aes_endpoint_v2 import adjudicate,render_local

def block(i,kind="leaf"):
    return {"id":i,"label":i,"kind":kind,"parent":None,
            "x":0.1,"y":0.1,"w":0.2,"h":0.1}
def edge(a,b):
    return {"from":a,"to":b,"direction":"forward","label":""}

class Tests(unittest.TestCase):
    def test_invalid_annotation_abstains(self):
        raw={"blocks":[block("a","annotation"),block("b")],
             "connections":[edge("a","b")]}
        original=copy.deepcopy(raw)
        render,rejected,summary=adjudicate(raw)
        self.assertEqual(summary["abstained_edge_count"],1)
        self.assertEqual(render["connections"],[])
        self.assertEqual(raw,original)
    def test_container_abstains(self):
        _,_,s=adjudicate({"blocks":[block("a","container"),block("b")],
                          "connections":[edge("a","b")]})
        self.assertEqual(s["abstain_reason_counts"]["non_endpoint_kind"],1)
    def test_explicit_port_allowed(self):
        r,_,s=adjudicate({"blocks":[block("a","port"),block("b")],
                          "connections":[edge("a","b")]})
        self.assertEqual(s["rendered_edge_count"],1)
        self.assertEqual(r["blocks"][0]["kind"],"leaf")
        self.assertTrue(s["llm_coordinates_used"])
    def test_unknown_ref_abstains(self):
        _,_,s=adjudicate({"blocks":[block("a")],
                          "connections":[edge("a","missing")]})
        self.assertEqual(s["abstain_reason_counts"]["invalid_reference"],1)
    def test_no_overwrite(self):
        raw={"blocks":[block("a")],"connections":[]}
        with tempfile.TemporaryDirectory() as d:
            render_local(raw,d)
            with self.assertRaises(FileExistsError):render_local(raw,d)
            summary=json.loads((Path(d)/"reconstruction_v2_summary.json").read_text())
            self.assertNotIn("blocks",summary)
            self.assertFalse(summary["auto_approval"])
    def test_invalid_block_rejected(self):
        with self.assertRaises(ValueError):
            adjudicate({"blocks":[block("a","unknown")],"connections":[]})
    def test_mixed_edges_only_valid_rendered(self):
        r,rejected,s=adjudicate({"blocks":[block("a"),block("b"),block("c","annotation")],
                                "connections":[edge("a","b"),edge("c","b")]})
        self.assertEqual(len(r["connections"]),1)
        self.assertEqual(len(rejected),1)
        self.assertEqual(s["edge_count"],2)
if __name__=="__main__":unittest.main()
