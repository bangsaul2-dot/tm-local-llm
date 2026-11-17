"""Offline diagram flow extraction + deterministic evidence-based narrative.

Experimental only. LLM sees original image; no OCR labels or guessed graph
are inserted. Unverified LLM edges never become verified or approved.
"""
from __future__ import annotations
import argparse
import base64
from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

PROMPT = """Inspect ONLY the supplied technical block diagram image.
Return a single strict JSON object (no markdown, no commentary):
{"blocks":[{"id":"b1","label":"exact visible text","kind":"leaf|container|port|annotation","parent":null}],
"flows":[{"from":"b1","to":"b2","direction":"forward|reverse|unknown",
"flow_type":"data|control|key|authentication|unknown",
"signal":"exact visible wire label or empty string",
"evidence":"visible_arrow|visible_wire|text_only|unclear",
"note":"brief observation, not a general technical inference"}]}
Rules:
- Include only visible blocks, labels and directly observable links.
- Use IDs in flows from blocks; parent references a container ID only.
- An external signal can be a port only if it is visibly a signal endpoint.
- Never connect a container or annotation as an endpoint.
- For a container boundary with no visible leaf/port endpoint, omit the link.
- If an arrowhead cannot be seen, use direction unknown.
- If no physical link is visible, omit the flow; do NOT infer an AES link
  from general cryptographic knowledge.
- Preserve distinct encryption and decryption paths.
- Keep exact spelling when readable; do not invent missing labels.
- Flow type unknown if the diagram itself does not establish it.
"""

ALLOWED_KINDS={"leaf","container","port","annotation"}
ALLOWED_DIRECTIONS={"forward","reverse","unknown"}
ALLOWED_TYPES={"data","control","key","authentication","unknown"}
ALLOWED_EVIDENCE={"visible_arrow","visible_wire","text_only","unclear"}

def validate(payload):
    if not isinstance(payload,dict) or set(payload)!={"blocks","flows"}:
        raise ValueError("top_level_schema")
    blocks,flows=payload["blocks"],payload["flows"]
    if not isinstance(blocks,list) or not isinstance(flows,list):
        raise ValueError("list_schema")
    ids={}
    for block in blocks:
        if not isinstance(block,dict) or set(block)!={"id","label","kind","parent"}:
            raise ValueError("block_schema")
        bid=block["id"]
        if not isinstance(bid,str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}",bid) or bid in ids:
            raise ValueError("block_id")
        if (not isinstance(block["label"],str) or not block["label"].strip()
            or len(block["label"])>200 or block["kind"] not in ALLOWED_KINDS):
            raise ValueError("block_fields")
        ids[bid]=block
    for block in blocks:
        parent=block["parent"]
        if parent is not None and (parent not in ids or ids[parent]["kind"]!="container"):
            raise ValueError("invalid_parent")
        visited=set()
        cursor=block["id"]
        while cursor is not None:
            if cursor in visited:
                raise ValueError("parent_cycle")
            visited.add(cursor)
            cursor=ids[cursor]["parent"]
    for flow in flows:
        if not isinstance(flow,dict) or set(flow)!={"from","to","direction","flow_type","signal","evidence","note"}:
            raise ValueError("flow_schema")
        if (flow["from"] not in ids or flow["to"] not in ids or flow["from"]==flow["to"]):
            raise ValueError("flow_reference")
        if ids[flow["from"]]["kind"] not in ("leaf","port") or ids[flow["to"]]["kind"] not in ("leaf","port"):
            raise ValueError("non_endpoint_kind")
        if (flow["direction"] not in ALLOWED_DIRECTIONS or
            flow["flow_type"] not in ALLOWED_TYPES or flow["evidence"] not in ALLOWED_EVIDENCE or
            not isinstance(flow["signal"],str) or len(flow["signal"])>160 or
            not isinstance(flow["note"],str) or len(flow["note"])>300):
            raise ValueError("flow_fields")
    return payload

def classify(payload):
    """Proposals only: no model self-reported evidence counts as verification."""
    ids={b["id"]:b for b in payload["blocks"]}
    candidates=[]
    abstained=[]
    for idx,f in enumerate(payload["flows"]):
        # All directions require human/physical verification; separate visually
        # supported claims from ambiguous/text-only assertions.
        if f["evidence"] not in ("visible_arrow","visible_wire"):
            abstained.append((idx,"no_physical_evidence_claim"))
        elif f["direction"]=="unknown":
            abstained.append((idx,"unknown_direction"))
        else:
            candidates.append((idx,f))
    return ids,candidates,abstained

def _safe(text):
    return str(text).replace("|","\\|").replace("\n"," ").replace("\r"," ")

def report_markdown(payload,figure_id):
    """Local-only report: contains source labels; never upload for internal SFT."""
    ids,candidates,abstained=classify(payload)
    lines=[f"# Diagram Flow Analysis — {_safe(figure_id)}",
           "","**Status: PROPOSAL / NOT VERIFIED**",
           "","Model-observed arrows are NOT physically verified. Every connection requires source review.",
           "","## Block inventory","",
           "| ID | Visible label | Kind | Parent |","|---|---|---|---|"]
    for b in payload["blocks"]:
        lines.append(f'| {_safe(b["id"])} | {_safe(b["label"])} | {b["kind"]} | {_safe(b["parent"] or "-")} |')
    lines.extend(["","## Observed flow candidates (unverified)",""])
    if not candidates:lines.append("No directional flow candidates supported by a model-observed arrow/wire.")
    for idx,f in candidates:
        src,dst=f["from"],f["to"]
        if f["direction"]=="reverse":src,dst=dst,src
        lines.append(f'{idx+1}. **{_safe(ids[src]["label"])} → {_safe(ids[dst]["label"])}** '
                     f'({f["flow_type"]}; {f["evidence"]}; signal: {_safe(f["signal"] or "unlabeled")}). '
                     f'Model observation: {_safe(f["note"])}. **Needs review.**')
    lines.extend(["","## Unverified / abstained flows",""])
    if not abstained:lines.append("None under model-output rules; physical validation still pending.")
    for idx,reason in abstained:
        f=payload["flows"][idx]
        lines.append(f'- Flow #{idx+1}: {_safe(ids[f["from"]]["label"])} / '
                     f'{_safe(ids[f["to"]]["label"])} — {reason}; needs_review')
    lines.extend(["","## Safety / limits","",
                  "- No source-verified edges, no auto-approval, no LLM coordinates.",
                  "- This report explains model-observed flow proposals; not a proven netlist.",
                  "- Missing blocks or wires cannot be ruled out without independent source review.",
                  "- Human GT accuracy: NOT_EVALUABLE."])
    return "\n".join(lines)+"\n"

def aggregate(payload):
    _,candidates,abstained=classify(payload)
    return {"block_count":len(payload["blocks"]),"flow_count":len(payload["flows"]),
            "flow_candidate_count":len(candidates),"flow_abstained_count":len(abstained),
            "flow_type_counts":dict(sorted(Counter(f["flow_type"] for f in payload["flows"]).items())),
            "abstain_reasons":dict(sorted(Counter(r for _,r in abstained).items())),
            "auto_approval":False,"source_verified":False,"llm_coordinates_used":False,
            "review_state":"needs_review","pass_90":"NOT_EVALUABLE"}

def _loopback(host):
    u=urlsplit(host)
    if u.scheme!="http" or u.hostname not in ("127.0.0.1","localhost","::1") or u.username or u.password or u.path not in ("","/") or u.query or u.fragment:
        raise ValueError("loopback_only")

def infer(image,model,host,seed=42):
    _loopback(host)
    from ollama import Client
    response=Client(host=host).chat(model=model,messages=[{
        "role":"user","content":PROMPT,
        "images":[base64.b64encode(image).decode("ascii")]}],
        options={"temperature":0,"seed":seed},stream=False)
    text=response["message"]["content"] if isinstance(response,dict) else response.message.content
    return validate(json.loads(text))

def main(argv=None):
    p=argparse.ArgumentParser(description="Offline image-to-data-flow analysis")
    p.add_argument("--image",required=True)
    p.add_argument("--model",default="gemma3-27b-local")
    p.add_argument("--host",default="http://127.0.0.1:11434")
    p.add_argument("--figure-id",default="figure")
    p.add_argument("--out-dir",required=True)
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--input-json",help="local prior JSON for deterministic rendering; skips model")
    args=p.parse_args(argv)
    try:
        if args.input_json:
            payload=validate(json.loads(Path(args.input_json).read_text(encoding="utf-8")))
        else:
            payload=infer(Path(args.image).read_bytes(),args.model,args.host,args.seed)
        output=Path(args.out_dir)
        output.mkdir(parents=True,exist_ok=True)
        # Only local report includes private labels; safe aggregate stdout.
        with (output/"flow_analysis.md").open("x",encoding="utf-8") as f:
            f.write(report_markdown(payload,args.figure_id))
        with (output/"flow_summary.json").open("x",encoding="utf-8") as f:
            json.dump(aggregate(payload),f,indent=2)
        print(json.dumps({"status":"candidate_review",**aggregate(payload)}))
    except Exception as exc:
        # No exception messages: they can include private paths, labels or raw replies.
        print(json.dumps({"status":"needs_review","error_type":type(exc).__name__,
                          "auto_approval":False,"pass_90":"NOT_EVALUABLE"}))
        return 1
    return 0
if __name__=="__main__":
    raise SystemExit(main())
