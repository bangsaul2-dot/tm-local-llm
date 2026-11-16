"""Read-only, privacy-preserving P1 grounding diagnostics.

Accepts existing in-memory semantic, geometry and grounded nodes.
Never serializes labels, coordinates, image bytes, paths or source data.
No automatic acceptance/approval and no mutation of input objects.
"""
from __future__ import annotations
from collections import Counter
from difflib import SequenceMatcher
import re

def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).casefold())

def _similarity(a,b):
    a,b=_norm(a),_norm(b)
    return SequenceMatcher(None,a,b).ratio() if a and b else 0.0

def _inside(bbox, token):
    x=(token["bbox"][0]+token["bbox"][2])/2
    y=(token["bbox"][1]+token["bbox"][3])/2
    return bbox[0]<=x<=bbox[2] and bbox[1]<=y<=bbox[3]

def diagnose_grounding(semantic, geometry, grounded_nodes, *, min_score=0.84, margin=0.08):
    """Aggregate explanatory *heuristics*, not GT accuracy or corrective matching.

    Counts for mutually exclusive unmatched causes use conservative precedence:
    no OCR > weak OCR similarity > competing boxes > other.
    """
    if not isinstance(semantic,dict) or not isinstance(geometry,dict) or not isinstance(grounded_nodes,list):
        raise TypeError("invalid diagnostic inputs")
    boxes=geometry.get("boxes",[])
    tokens=geometry.get("ocr",[])
    if len(grounded_nodes)!=len(semantic.get("nodes",[])):
        raise ValueError("grounded node count mismatch")
    reasons=Counter()
    kinds=Counter()
    endpoint_counts=Counter()
    names={n["name"]:n for n in semantic["nodes"]}
    for edge in semantic["edges"]:
        for endpoint in ("from","to"):
            n=names.get(edge[endpoint])
            if n and n["kind"]=="container":
                endpoint_counts["container_endpoint"]+=1
    for node,grounded in zip(semantic["nodes"],grounded_nodes):
        kinds[node["kind"]]+=1
        if grounded["grounding"]=="grounded":
            reasons["grounded"]+=1
            continue
        if grounded["grounding"]=="ambiguous":
            reasons["duplicate_box"]+=1
            continue
        scores=[]
        for box in boxes:
            inside=[t["text"] for t in tokens if _inside(box["bbox"],t)]
            if inside:
                scores.append(max(_similarity(node["name"],word) for word in inside+[ " ".join(inside)]))
        scores.sort(reverse=True)
        if not scores:
            reasons["no_ocr_in_boxes"]+=1
        elif scores[0]<min_score:
            reasons["low_text_similarity"]+=1
        elif len(scores)>1 and scores[0]-scores[1]<margin:
            reasons["competing_boxes"]+=1
        else:
            reasons["other_unmatched"]+=1
    return {
        "schema_version":"p1-diagnostics-dev",
        "node_count":len(grounded_nodes),
        "grounded_count":reasons["grounded"],
        "unmatched_count":len(grounded_nodes)-reasons["grounded"],
        "unmatched_reason_counts":{key:reasons[key] for key in
            ("no_ocr_in_boxes","low_text_similarity","competing_boxes",
             "duplicate_box","other_unmatched")},
        "node_kind_counts":{"leaf":kinds["leaf"],"container":kinds["container"]},
        "container_endpoint_occurrences":endpoint_counts["container_endpoint"],
        "diagnostic_only":True,
        "auto_approval":False,"source_verified":False,
        "llm_coordinates_used":False,"review_state":"needs_review",
        "pass_90":"NOT_EVALUABLE",
    }
