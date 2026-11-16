"""No GPU/network needed; synthetic-only P1/P2 orchestration contract tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pipeline_p1p2 as p

SEM={"nodes":[{"name":"Alpha","kind":"leaf","parent":None},
              {"name":"Beta","kind":"leaf","parent":None}],
     "edges":[{"from":"Alpha","to":"Beta","direction":"forward"}]}

class Adapter:
    def to_geometry(self, v116, image_path):
        return {"boxes":[{"bbox":[0,0,30,40]},{"bbox":[100,0,130,40]}],
                "wires":[{"id":"w0","points":[[42,20],[88,20]],
                          "trace_verified":True,"bus_group_id":"bus_0",
                          "arrow_direction":"forward"}]}

def ocr(image,**kwargs):
    return [{"text":"Alpha","bbox":[1,1,25,10]},
            {"text":"Beta","bbox":[101,1,125,10]}]

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.image=Path(self.tmp.name)/"synthetic.png"
        self.image.write_bytes(b"synthetic test image bytes")
    def tearDown(self):
        self.tmp.cleanup()
    def test_pipeline_candidate_safe(self):
        report=p.process_figure({},self.image,adapter=Adapter(),
            infer=lambda prompt,image:json.dumps(SEM),ocr_engine=ocr)
        self.assertEqual(report["edge_candidates"],1)
        self.assertEqual(report["grounded_count"],2)
        self.assertFalse(report["source_verified"])
        self.assertEqual(report["pass_90"],"NOT_EVALUABLE")
        self.assertNotIn("bbox",json.dumps(report))
        self.assertNotIn("Alpha",json.dumps(report))
    def test_bad_semantic_abstains(self):
        report=p.process_figure({},self.image,adapter=Adapter(),
            infer=lambda prompt,image:'{"nodes":[],"edges":[],"bbox":[]}',
            max_retries=1,ocr_engine=ocr)
        self.assertFalse(report["semantic_valid"])
        self.assertEqual(report["attempts"],2)
    def test_no_llm_coordinates(self):
        bad={**SEM,"nodes":[{"name":"Alpha","kind":"leaf","parent":None,"bbox":[0,0,1,1]}]}
        report=p.process_figure({},self.image,adapter=Adapter(),
            infer=lambda prompt,image:json.dumps(bad),max_retries=0,ocr_engine=ocr)
        self.assertFalse(report["semantic_valid"])
    def test_ollama_host_restricted(self):
        for host in ("https://127.0.0.1:11434","http://example.com:11434",
                     "http://127.0.0.1:11434/api/chat"):
            with self.assertRaises(ValueError):
                p._local_host(host)
    def test_ollama_content_is_string_and_image_separate(self):
        calls=[]
        class Client:
            def __init__(self,host): calls.append(host)
            def chat(self,**kwargs):
                calls.append(kwargs)
                return {"message":{"content":json.dumps(SEM)}}
        import sys,types
        fake=types.ModuleType("ollama");fake.Client=Client
        with patch.dict(sys.modules,{"ollama":fake}):
            text=p.local_ollama_infer("local","http://127.0.0.1:11434")("prompt",b"pixels")
        self.assertEqual(json.loads(text),SEM)
        msg=calls[1]["messages"][0]
        self.assertEqual(msg["content"],"prompt")
        self.assertEqual(msg["images"],["cGl4ZWxz"])
    def test_multi_figure_sanitized(self):
        out=p.run_figures([{"v116":{},"image":str(self.image)}]*2,
            adapter=Adapter(),infer=lambda prompt,image:json.dumps(SEM),
            ocr_engine=ocr)
        self.assertEqual(len(out["figures"]),2)
        self.assertEqual([x["edge_candidates"] for x in out["figures"]],[1,1])
    def test_no_exception_details_leaked(self):
        out=p.run_figures([{"v116":{},"image":"/private/not-existing"}],
            adapter=Adapter(),infer=lambda prompt,image:json.dumps(SEM),
            ocr_engine=ocr)
        self.assertNotIn("/private/",json.dumps(out))
        self.assertEqual(out["figures"][0]["status"],"needs_review")

if __name__=="__main__": unittest.main()
