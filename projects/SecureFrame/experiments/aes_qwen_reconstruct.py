"""Local-only Qwen3VL image -> diagram JSON -> SVG reconstruction experiment.

Outputs stay on the Ubuntu machine. Do not upload private JSON/SVG.
No approved SecureFrame modules, DB or Graph are changed.
"""
from __future__ import annotations
import argparse
import base64
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

PROMPT="""Read the supplied technical block diagram IMAGE ONLY.
Return ONE strict JSON object (no markdown) with:
{"blocks":[{"id":"b1","label":"exact visible label","kind":"leaf|container|annotation",
"parent":null,"x":0.1,"y":0.1,"w":0.2,"h":0.1}],
"connections":[{"from":"b1","to":"b2","direction":"forward|reverse|unknown",
"label":""}]}
Coordinates are normalized 0..1 relative to the diagram image. Estimate
visual layout from the IMAGE; do not invent missing text, blocks or arrows.
Use containers for dashed enclosing areas. A connection must correspond
to a visible arrow or wire; do not infer based on AES domain knowledge.
If uncertain, omit a connection rather than fabricate it.
A block's parent is its enclosing container id or null.
Never use a container as a connection endpoint.
Include rotated text if readable. Preserve encryption/decryption distinction.
"""

def validate(obj):
    if not isinstance(obj,dict) or set(obj)!={"blocks","connections"}:
        raise ValueError("invalid top-level keys")
    if not isinstance(obj["blocks"],list) or not isinstance(obj["connections"],list):
        raise ValueError("invalid lists")
    ids={}
    for b in obj["blocks"]:
        if not isinstance(b,dict) or set(b)!={"id","label","kind","parent","x","y","w","h"}:
            raise ValueError("invalid block")
        if not isinstance(b["id"],str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}",b["id"]) or b["id"] in ids:
            raise ValueError("invalid/duplicate id")
        if not isinstance(b["label"],str) or len(b["label"])>200 or b["kind"] not in ("leaf","container","annotation"):
            raise ValueError("invalid label/kind")
        for k in ("x","y","w","h"):
            if type(b[k]) not in (float,int) or not 0<=b[k]<=1:
                raise ValueError("invalid normalized position")
        if b["w"]<=0 or b["h"]<=0 or b["x"]+b["w"]>1.001 or b["y"]+b["h"]>1.001:
            raise ValueError("invalid extent")
        ids[b["id"]]=b
    for b in obj["blocks"]:
        if b["parent"] is not None and (b["parent"] not in ids or ids[b["parent"]]["kind"]!="container" or b["parent"]==b["id"]):
            raise ValueError("invalid parent")
        seen=set(); cur=b["id"]
        while cur is not None:
            if cur in seen:raise ValueError("parent cycle")
            seen.add(cur);cur=ids[cur]["parent"]
    for e in obj["connections"]:
        if not isinstance(e,dict) or set(e)!={"from","to","direction","label"}:
            raise ValueError("invalid edge")
        if e["from"] not in ids or e["to"] not in ids or e["from"]==e["to"]:
            raise ValueError("invalid endpoints")
        if ids[e["from"]]["kind"]!="leaf" or ids[e["to"]]["kind"]!="leaf":
            raise ValueError("container/annotation endpoint forbidden")
        if e["direction"] not in ("forward","reverse","unknown") or not isinstance(e["label"],str) or len(e["label"])>200:
            raise ValueError("invalid edge direction/label")
    return obj

def svg(obj,width=1200,height=900):
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><path d="M0 0 L10 3.5 L0 7 Z" fill="#333"/></marker></defs>',
           '<rect width="100%" height="100%" fill="white"/>']
    ids={b["id"]:b for b in obj["blocks"]}
    for b in sorted(obj["blocks"],key=lambda x:x["kind"]!="container"):
        x,y,w,h=[b[k]*d for k,d in (("x",width),("y",height),("w",width),("h",height))]
        dash=' stroke-dasharray="8 5"' if b["kind"]=="container" else ""
        if b["kind"]!="annotation":
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="none" stroke="#333" stroke-width="2"{dash}/>')
        for i,line in enumerate(b["label"].split("\\n")[:5]):
            lines.append(f'<text x="{x+w/2:.1f}" y="{y+min(h-5,20+18*i):.1f}" font-family="sans-serif" font-size="16" text-anchor="middle">{escape(line)}</text>')
    for e in obj["connections"]:
        a,b=ids[e["from"]],ids[e["to"]]
        ax,ay=(a["x"]+a["w"]/2)*width,(a["y"]+a["h"]/2)*height
        bx,by=(b["x"]+b["w"]/2)*width,(b["y"]+b["h"]/2)*height
        # Approximate straight links only. This is NOT physical-wire tracing.
        start,end=((bx,by),(ax,ay)) if e["direction"]=="reverse" else ((ax,ay),(bx,by))
        arrow=' marker-end="url(#arrow)"' if e["direction"]!="unknown" else ""
        lines.append(f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" x2="{end[0]:.1f}" y2="{end[1]:.1f}" stroke="#333" stroke-width="2"{arrow}/>')
    lines.append("</svg>")
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--image",required=True)
    p.add_argument("--out-dir",required=True)
    p.add_argument("--model",default="qwen3vl-30b-local")
    p.add_argument("--host",default="http://127.0.0.1:11434")
    p.add_argument("--temperature",type=float,default=0)
    p.add_argument("--seed",type=int,default=42)
    a=p.parse_args()
    u=urlsplit(a.host)
    if u.scheme!="http" or u.hostname not in ("localhost","127.0.0.1","::1") or u.username or u.password or u.path not in ("","/") or u.query or u.fragment:
        raise SystemExit("Only localhost Ollama allowed")
    from ollama import Client
    image=Path(a.image).read_bytes()
    response=Client(host=a.host).chat(model=a.model,messages=[{
        "role":"user","content":PROMPT,
        "images":[base64.b64encode(image).decode("ascii")]}],
        options={"temperature":a.temperature,"seed":a.seed},stream=False)
    text=response.message.content if hasattr(response,"message") else response["message"]["content"]
    try:
        obj=validate(json.loads(text))
    except (ValueError,TypeError) as exc:
        # Never dump raw model output or source data.
        raise SystemExit("Model output rejected: "+type(exc).__name__) from None
    out=Path(a.out_dir)
    out.mkdir(parents=True,exist_ok=True)
    for name,body in (("reconstruction.json",json.dumps(obj,ensure_ascii=False,indent=2)),
                      ("reconstruction.svg",svg(obj))):
        target=out/name
        with target.open("x",encoding="utf-8") as f:f.write(body)
    print(json.dumps({"status":"candidate_review","block_count":len(obj["blocks"]),
                      "container_count":sum(b["kind"]=="container" for b in obj["blocks"]),
                      "edge_count":len(obj["connections"]),"auto_approval":False,
                      "source_verified":False,"review_state":"needs_review",
                      "pass_90":"NOT_EVALUABLE"}))
if __name__=="__main__":
    main()
