"""Synthetic-only diagram flow tests; no internal source data."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import diagram_flow_analyzer as d

def block(i,kind="leaf",parent=None):
    return {"id":i,"label":"Synthetic "+i,"kind":kind,"parent":parent}
def flow(a,b,direction="forward",evidence="visible_arrow",typ="data"):
    return {"from":a,"to":b,"direction":direction,"flow_type":typ,
            "signal":"","evidence":evidence,"note":"observed"}
def doc(blocks=None,flows=None):
    return {"blocks":blocks if blocks is not None else [block("a"),block("b")],
            "flows":flows if flows is not None else [flow("a","b")]}

class Tests(unittest.TestCase):
    def test_flow_narrative(self):
        x=d.validate(doc())
        md=d.report_markdown(x,"synthetic")
        self.assertIn("Synthetic a → Synthetic b",md)
        self.assertIn("NOT_EVALUABLE",md)
        self.assertIn("NOT VERIFIED",md)
    def test_reverse(self):
        md=d.report_markdown(d.validate(doc(flows=[flow("a","b","reverse")])),"synthetic")
        self.assertIn("Synthetic b → Synthetic a",md)
    def test_unknown_abstains(self):
        s=d.aggregate(d.validate(doc(flows=[flow("a","b","unknown")])))
        self.assertEqual(s["flow_candidate_count"],0)
        self.assertEqual(s["flow_abstained_count"],1)
    def test_text_only_abstains(self):
        s=d.aggregate(d.validate(doc(flows=[flow("a","b",evidence="text_only")])))
        self.assertEqual(s["flow_candidate_count"],0)
    def test_container_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            d.validate(doc([block("a","container"),block("b")],[flow("a","b")]))
    def test_port_endpoint(self):
        x=d.validate(doc([block("a","port"),block("b")],[flow("a","b")]))
        self.assertEqual(d.aggregate(x)["flow_candidate_count"],1)
    def test_parent_container(self):
        self.assertEqual(len(d.validate(doc([block("a","container"),block("b",parent="a")],[]))["blocks"]),2)
    def test_parent_cycle_rejected(self):
        with self.assertRaises(ValueError):
            d.validate(doc([block("a","container","b"),block("b","container","a")],[]))
    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):d.validate(doc([block("a"),block("a")],[]))
    def test_unknown_ref(self):
        with self.assertRaises(ValueError):d.validate(doc(flows=[flow("a","missing")]))
    def test_extra_fields(self):
        x=doc();x["flows"][0]["bbox"]=[0,0,1,1]
        with self.assertRaises(ValueError):d.validate(x)
    def test_aggregate_no_labels(self):
        s=d.aggregate(d.validate(doc()))
        self.assertNotIn("Synthetic",json.dumps(s))
        self.assertFalse(s["auto_approval"])
        self.assertFalse(s["llm_coordinates_used"])
    def test_no_mutation(self):
        x=doc();original=copy.deepcopy(x)
        d.report_markdown(d.validate(x),"test")
        self.assertEqual(x,original)
    def test_loopback(self):
        d._loopback("http://127.0.0.1:11434")
        for bad in ("https://127.0.0.1:11434","http://example.com",
                    "http://localhost:11434/api"):
            with self.assertRaises(ValueError):d._loopback(bad)
    def test_sdk_image_separate(self):
        class Client:
            def __init__(self,host):self.host=host
            def chat(self,**kwargs):
                msg=kwargs["messages"][0]
                assert isinstance(msg["content"],str)
                assert isinstance(msg["images"],list)
                return {"message":{"content":json.dumps(doc())}}
        import sys,types
        fake=types.ModuleType("ollama");fake.Client=Client
        with patch.dict(sys.modules,{"ollama":fake}):
            self.assertEqual(len(d.infer(b"image","gemma","http://127.0.0.1:11434")["flows"]),1)
    def test_write_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            img=Path(td)/"a.png";img.write_bytes(b"synthetic")
            j=Path(td)/"in.json";j.write_text(json.dumps(doc()))
            out=Path(td)/"output"
            argv=["--image",str(img),"--input-json",str(j),"--out-dir",str(out)]
            self.assertEqual(d.main(argv),0)
            self.assertEqual(d.main(argv),1)
            self.assertTrue((out/"flow_analysis.md").exists())
    def test_no_flows(self):
        s=d.aggregate(d.validate(doc(flows=[])))
        self.assertEqual(s["flow_candidate_count"],0)
if __name__=="__main__":unittest.main()
