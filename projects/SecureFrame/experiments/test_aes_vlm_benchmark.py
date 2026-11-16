"""Synthetic-only tests for local VLM benchmark. No model downloads or GPU."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from aes_vlm_benchmark import check_host,parse_response,run,write_report

def block(i,kind="leaf"):
    return {"id":i,"label":"Synthetic "+i,"kind":kind,"parent":None,
            "x":0.1,"y":0.1,"w":0.2,"h":0.1}
def edge(a,b):
    return {"from":a,"to":b,"direction":"forward","label":""}

class Client:
    def __init__(self,text):self.text=text;self.calls=[]
    def chat(self,**kw):
        self.calls.append(kw)
        return {"message":{"content":self.text},"eval_count":20,"eval_duration":1000000000}

class Tests(unittest.TestCase):
    def test_loopback(self):
        for host in ("http://localhost:11434","http://127.0.0.1:11434"):
            self.assertEqual(check_host(host),host)
    def test_reject_remote(self):
        for host in ("https://localhost:11434","http://example.com:11434",
                     "http://localhost:11434/api","http://u:p@localhost:11434"):
            with self.assertRaises(ValueError):check_host(host)
    def test_valid_counts(self):
        obj={"blocks":[block("a"),block("b")],"connections":[edge("a","b")]}
        self.assertEqual(parse_response(json.dumps(obj))["rendered"],1)
    def test_abstain_container(self):
        obj={"blocks":[block("a","container"),block("b")],
             "connections":[edge("a","b")]}
        s=parse_response(json.dumps(obj))
        self.assertEqual(s["abstained"],1)
        self.assertEqual(s["non_endpoint"],1)
    def test_bad_json(self):
        with self.assertRaises(json.JSONDecodeError):parse_response("not json")
    def test_no_raw_data_in_report(self):
        obj={"blocks":[block("a")],"connections":[]}
        c=Client(json.dumps(obj))
        rows=run(b"private synthetic bytes",["model-A"],c)
        self.assertEqual(rows[0]["status"],"schema_pass")
        self.assertEqual(rows[0]["tokens_per_sec"],20)
        self.assertEqual(type(c.calls[0]["messages"][0]["content"]),str)
        self.assertIsInstance(c.calls[0]["messages"][0]["images"],list)
        self.assertNotIn("Synthetic",json.dumps(rows))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"report.csv"
            write_report(rows,path)
            with self.assertRaises(FileExistsError):write_report(rows,path)
            self.assertEqual(len(list(csv.DictReader(path.open()))),1)
    def test_error_sanitized(self):
        c=Client("bad raw SECRET")
        rows=run(b"x",["model-A"],c)
        self.assertEqual(rows[0]["status"],"error")
        self.assertNotIn("SECRET",json.dumps(rows))
    def test_each_model_invoked(self):
        c=Client(json.dumps({"blocks":[],"connections":[]}))
        rows=run(b"image",["qwen","gemma","internvl"],c)
        self.assertEqual(len(c.calls),3)
        self.assertEqual(len(rows),3)
if __name__=="__main__":unittest.main()
