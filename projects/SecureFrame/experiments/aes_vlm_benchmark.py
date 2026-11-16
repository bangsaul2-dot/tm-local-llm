"""Offline, non-destructive vision-model benchmark for a public AES diagram.

Model installation is deliberately separate. The script never downloads a model.
Outputs are aggregate-only; raw model replies, labels and coordinates are not saved.
"""
from __future__ import annotations
import argparse
import base64
import csv
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from aes_endpoint_v2 import adjudicate
from aes_qwen_reconstruct import PROMPT

FIELDS=("model","status","blocks","containers","annotations","ports",
        "edges","rendered","abstained","non_endpoint","invalid_reference",
        "latency_sec","tokens_per_sec","image_sha256_prefix","error_type")
def check_host(host):
    u=urlsplit(host)
    if (u.scheme!="http" or u.hostname not in ("localhost","127.0.0.1","::1")
        or u.username or u.password or u.query or u.fragment or u.path not in ("","/")):
        raise ValueError("only loopback Ollama is allowed")
    return host

def parse_response(text):
    """Only JSON object; no markdown fence or repair that could hide failures."""
    if not isinstance(text,str):
        raise TypeError("response must be text")
    obj=json.loads(text)
    _,_,summary=adjudicate(obj)
    kinds={k:sum(b["kind"]==k for b in obj["blocks"])
           for k in ("container","annotation","port")}
    return {"blocks":summary["block_count"],"edges":summary["edge_count"],
            "rendered":summary["rendered_edge_count"],
            "abstained":summary["abstained_edge_count"],
            "non_endpoint":summary["abstain_reason_counts"].get("non_endpoint_kind",0),
            "invalid_reference":summary["abstain_reason_counts"].get("invalid_reference",0),
            "containers":kinds["container"],"annotations":kinds["annotation"],
            "ports":kinds["port"]}

def infer(client,model,image,temperature,seed):
    response=client.chat(model=model,messages=[{
        "role":"user","content":PROMPT,
        "images":[base64.b64encode(image).decode("ascii")]}],
        options={"temperature":temperature,"seed":seed},
        stream=False)
    if isinstance(response,dict):
        msg=response["message"]["content"]
        eval_count=response.get("eval_count")
        eval_duration=response.get("eval_duration")
    else:
        msg=response.message.content
        eval_count=getattr(response,"eval_count",None)
        eval_duration=getattr(response,"eval_duration",None)
    return msg,(round(eval_count*1e9/eval_duration,2)
                if isinstance(eval_count,int) and isinstance(eval_duration,int) and eval_duration>0
                else None)

def run(image,models,client,*,temperature=0.0,seed=42):
    sha=hashlib.sha256(image).hexdigest()[:12]
    rows=[]
    for model in models:
        row={k:None for k in FIELDS}
        row.update(model=model,status="error",image_sha256_prefix=sha)
        t0=time.monotonic()
        try:
            text,tps=infer(client,model,image,temperature,seed)
            row.update(parse_response(text))
            row["tokens_per_sec"]=tps
            row["status"]="schema_pass"
        except Exception as exc:
            # Exception text may contain private model output/path; never print it.
            row["error_type"]=type(exc).__name__
        row["latency_sec"]=round(time.monotonic()-t0,2)
        rows.append(row)
    return rows

def write_report(rows,path):
    target=Path(path)
    with target.open("x",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--image",required=True)
    p.add_argument("--models",nargs="+",required=True)
    p.add_argument("--host",default="http://127.0.0.1:11434")
    p.add_argument("--temperature",type=float,default=0.0)
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--report",required=True)
    a=p.parse_args()
    check_host(a.host)
    from ollama import Client
    rows=run(Path(a.image).read_bytes(),a.models,Client(host=a.host),
             temperature=a.temperature,seed=a.seed)
    write_report(rows,a.report)
    for r in rows:
        # Only aggregate metrics; do not print raw response.
        print(json.dumps(r,ensure_ascii=False))
if __name__=="__main__":
    main()
