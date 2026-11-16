"""V11.7.3 experimental OCR-to-semantic candidate ranking, read-only.

No name substitution, no LLM coordinates, no automatic grounding or approval.
Use only on-device; candidate details contain private names and must NOT be logged.
"""
from __future__ import annotations
from collections import defaultdict
from difflib import SequenceMatcher
import math
import re
import unicodedata

def normalize(value):
    if not isinstance(value,str):
        raise TypeError("label must be string")
    return "".join(c.casefold() for c in unicodedata.normalize("NFKC",value)
                   if c.isalnum())

def digit_runs(value):
    return tuple(re.findall(r"[0-9]+",normalize(value)))

def _center(box):
    return ((box[0]+box[2])/2,(box[1]+box[3])/2)

def _valid_bbox(box):
    return isinstance(box,(list,tuple)) and len(box)==4 and all(
        type(x) in (int,float) and math.isfinite(x) for x in box
    ) and box[2]>box[0] and box[3]>box[1]

def _inside(box,point):
    return box[0]<=point[0]<=box[2] and box[1]<=point[1]<=box[3]

def similarity(label, observed):
    """Deterministic score. Digit-run mismatch is a hard reject."""
    a,b=normalize(label),normalize(observed)
    if not a or not b:
        return 0.0,"empty"
    if digit_runs(label)!=digit_runs(observed):
        return 0.0,"numeric_conflict"
    if a==b:
        return 1.0,"exact_normalized"
    ratio=SequenceMatcher(None,a,b).ratio()
    # Substring is a candidate only for meaningful >= 5-char identifiers.
    # Short generic substrings are not reliable grounding evidence.
    if min(len(a),len(b))>=5 and (a in b or b in a):
        return min(0.93,0.83+0.10*min(len(a),len(b))/max(len(a),len(b))),"substring"
    return ratio,"edit_similarity"

def _box_texts(box,tokens):
    """Multiple bounded text views; no OCR edits and no semantic injection."""
    inside=[t for t in tokens if _inside(box,_center(t["bbox"]))]
    inside.sort(key=lambda t:(_center(t["bbox"])[1],t["bbox"][0]))
    views=[t["text"] for t in inside]
    if inside:
        # Conservative alternatives; join for ranking only, not OCR mutation.
        views.append(" ".join(t["text"] for t in inside))
        for i in range(len(inside)):
            for size in (2,3,4):
                chunk=inside[i:i+size]
                if len(chunk)!=size:continue
                ys=[_center(t["bbox"])[1] for t in chunk]
                heights=[t["bbox"][3]-t["bbox"][1] for t in chunk]
                if max(ys)-min(ys)<=0.45*max(heights):
                    views.append("".join(t["text"] for t in chunk))
    return views

def rank_candidates(semantic,geometry,*,min_score=0.84,margin=0.08):
    """Return private in-memory proposals, not approved grounding.

    Requires unambiguous best box and no numeric conflicts. A candidate is
    still needs_review even at score 1.0. Containers are never endpoints.
    """
    if not 0<=min_score<=1 or not 0<=margin<=1:
        raise ValueError("invalid thresholds")
    boxes=geometry.get("boxes",[])
    tokens=geometry.get("ocr",[])
    for b in boxes:
        if not isinstance(b,dict) or not _valid_bbox(b.get("bbox")):
            raise ValueError("invalid box")
    for t in tokens:
        if not isinstance(t,dict) or not isinstance(t.get("text"),str) or not _valid_bbox(t.get("bbox")):
            raise ValueError("invalid token")
    proposals=[]
    for node in semantic["nodes"]:
        scores=[]
        for i,box in enumerate(boxes):
            options=_box_texts(box["bbox"],tokens)
            if not options:continue
            best=max((similarity(node["name"],opt) for opt in options),
                     key=lambda x:x[0])
            scores.append((best[0],i,best[1]))
        scores.sort(key=lambda s:(-s[0],s[1]))
        top=scores[0] if scores else (0.0,None,"no_ocr")
        second=scores[1][0] if len(scores)>1 else 0.0
        eligible=top[1] is not None and top[0]>=min_score and (
            len(scores)==1 or top[0]-second>=margin)
        proposals.append({
            "name":node["name"],"kind":node["kind"],
            "box_index":top[1] if eligible else None,
            "score":top[0],"runner_up_score":second,
            "reason":top[2] if eligible else "abstain",
            "review_state":"needs_review","source_verified":False,
            "auto_approval":False,"llm_coordinates_used":False})
    # If two nodes claim one box, abstain for both.
    claimed=defaultdict(list)
    for i,p in enumerate(proposals):
        if p["box_index"] is not None:
            claimed[p["box_index"]].append(i)
    for indices in claimed.values():
        if len(indices)>1:
            for i in indices:
                proposals[i]["box_index"]=None
                proposals[i]["reason"]="duplicate_box_abstain"
    return proposals

def aggregate(proposals):
    """Only sanitized counts, safe to serialize."""
    reasons=defaultdict(int)
    for p in proposals:
        reasons[p["reason"] if p["box_index"] is not None else "abstain"]+=1
    return {"node_count":len(proposals),
            "candidate_count":sum(p["box_index"] is not None for p in proposals),
            "abstain_count":sum(p["box_index"] is None for p in proposals),
            "reason_counts":dict(sorted(reasons.items())),
            "auto_approval":False,"source_verified":False,
            "review_state":"needs_review","llm_coordinates_used":False,
            "pass_90":"NOT_EVALUABLE"}
