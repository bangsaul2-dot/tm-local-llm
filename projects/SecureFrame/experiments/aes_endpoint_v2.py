"""AES reconstruction V2: review-only endpoint adjudication.

Preserves Qwen output verbatim in memory. Never converts annotation/container
to leaf or invents ports. Invalid edges are abstained, not silently deleted.
This is an isolated experiment, not approved SecureFrame grounding.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from aes_qwen_reconstruct import validate, svg

def adjudicate(raw):
    if not isinstance(raw,dict) or set(raw)!={"blocks","connections"}:
        raise ValueError("invalid document")
    blocks=raw["blocks"]; edges=raw["connections"]
    if not isinstance(blocks,list) or not isinstance(edges,list):
        raise ValueError("invalid arrays")
    # Use existing strict validator for geometry, ID uniqueness, parents, text.
    # Port is a valid *explicitly predicted* endpoint in this experiment.
    for b in blocks:
        if not isinstance(b,dict) or b.get("kind") not in ("leaf","container","annotation","port"):
            raise ValueError("invalid block kind")
    schema_blocks=[{**b,"kind":"leaf" if b["kind"]=="port" else b["kind"]} for b in blocks]
    validate({"blocks":schema_blocks,"connections":[]})
    ids={b["id"]:b for b in blocks}
    accepted=[]; rejected=[]; counts=Counter()
    for index,e in enumerate(edges):
        if not isinstance(e,dict) or set(e)!={"from","to","direction","label"}:
            reason="edge_schema"
        elif not isinstance(e["label"],str) or len(e["label"])>200 or e["direction"] not in ("forward","reverse","unknown"):
            reason="edge_schema"
        elif e["from"] not in ids or e["to"] not in ids or e["from"]==e["to"]:
            reason="invalid_reference"
        elif ids[e["from"]]["kind"] not in ("leaf","port") or ids[e["to"]]["kind"] not in ("leaf","port"):
            reason="non_endpoint_kind"
        else:
            reason=None
        if reason:
            rejected.append({"edge_index":index,"reason":reason})
            counts[reason]+=1
        else:
            accepted.append(e)
    # SVG renderer accepts leaf-only. Create ephemeral copies of explicit ports
    # for rendering; original kinds and raw inputs remain unchanged.
    render_blocks=[{**b,"kind":"leaf" if b["kind"]=="port" else b["kind"]} for b in blocks]
    render_data=validate({"blocks":render_blocks,"connections":accepted})
    return render_data,rejected,{
        "status":"needs_review" if rejected else "candidate_review",
        "block_count":len(blocks),"edge_count":len(edges),
        "rendered_edge_count":len(accepted),"abstained_edge_count":len(rejected),
        "abstain_reason_counts":dict(sorted(counts.items())),
        "auto_approval":False,"source_verified":False,
        "llm_coordinates_used":True,"review_state":"needs_review",
        "pass_90":"NOT_EVALUABLE"}

def render_local(raw,output_dir):
    """Writes local experimental SVG only, with no overwrite."""
    render_data,rejected,summary=adjudicate(raw)
    target=Path(output_dir)
    target.mkdir(parents=True,exist_ok=True)
    with (target/"reconstruction_v2.svg").open("x",encoding="utf-8") as f:
        f.write(svg(render_data))
    with (target/"reconstruction_v2_summary.json").open("x",encoding="utf-8") as f:
        json.dump(summary,f,ensure_ascii=False,indent=2)
    # Rejected edge indices/reasons are in memory only; summary is sanitized.
    return summary

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--input-json",required=True)
    p.add_argument("--out-dir",required=True)
    a=p.parse_args()
    raw=json.loads(Path(a.input_json).read_text(encoding="utf-8"))
    print(json.dumps(render_local(raw,a.out_dir),ensure_ascii=False))
if __name__=="__main__":
    main()
