"""Conservative OCR token combination for deterministic grounding.

No LLM names are used to select merges. Inputs remain unchanged.
Output is IN-MEMORY ONLY and contains coordinates; never serialize it.
"""
from __future__ import annotations
from copy import deepcopy
import math
import unicodedata

def _valid_bbox(b):
    return (isinstance(b,(list,tuple)) and len(b)==4 and
            all(type(v) in (int,float) and math.isfinite(v) for v in b)
            and b[2]>b[0] and b[3]>b[1])

def _center(t):
    b=t["bbox"]
    return ((b[0]+b[2])/2,(b[1]+b[3])/2)

def _owner(token,boxes):
    x,y=_center(token)
    owners=[i for i,b in enumerate(boxes)
            if b["bbox"][0]<=x<=b["bbox"][2] and b["bbox"][1]<=y<=b["bbox"][3]]
    # No cross-box merges or ambiguous overlapping box assignments.
    return owners[0] if len(owners)==1 else None

def _normal(text):
    return unicodedata.normalize("NFKC",text).strip()

def _can_join(left,right,*,gap_ratio=0.65,line_tolerance=0.45):
    a,b=left["bbox"],right["bbox"]
    ah,bh=a[3]-a[1],b[3]-b[1]
    if abs((a[1]+a[3])/2-(b[1]+b[3])/2)>line_tolerance*max(ah,bh):
        return False
    gap=b[0]-a[2]
    if gap<0 or gap>gap_ratio*max(ah,bh):
        return False
    # Don't merge punctuation-only fragments, which may be wire/arrow artifacts.
    if not any(c.isalnum() for c in left["text"]) or not any(c.isalnum() for c in right["text"]):
        return False
    return True

def combine_ocr_tokens(geometry,*,max_group=4,gap_ratio=0.65,line_tolerance=0.45):
    """Return new geometry with safe within-box OCR clusters combined.

    Original node/box/wire counts unchanged. Coordinates retained only
    in memory. A merge may improve or worsen similarity; validate locally.
    """
    if not isinstance(geometry,dict):
        raise TypeError("geometry must be a dict")
    if not isinstance(max_group,int) or not 2<=max_group<=8:
        raise ValueError("max_group must be 2..8")
    if not 0<=gap_ratio<=2 or not 0<=line_tolerance<=1:
        raise ValueError("invalid merge tolerance")
    boxes=geometry.get("boxes",[])
    tokens=geometry.get("ocr",[])
    if not isinstance(boxes,list) or not isinstance(tokens,list):
        raise ValueError("boxes and ocr must be lists")
    for box in boxes:
        if not isinstance(box,dict) or not _valid_bbox(box.get("bbox")):
            raise ValueError("invalid box")
    for token in tokens:
        if (not isinstance(token,dict) or not _valid_bbox(token.get("bbox"))
                or not isinstance(token.get("text"),str)):
            raise ValueError("invalid OCR token")
    out=deepcopy(geometry)
    by_owner={}
    unowned=[]
    for token in out["ocr"]:
        token["text"]=_normal(token["text"])
        owner=_owner(token,boxes)
        if owner is None:
            unowned.append(token)
        else:
            by_owner.setdefault(owner,[]).append(token)
    merged=list(unowned)
    for owner in sorted(by_owner):
        ts=sorted(by_owner[owner],key=lambda t:(_center(t)[1],t["bbox"][0]))
        # Build deterministic line clusters; never bridge distant tokens.
        groups=[]
        for t in ts:
            if groups and len(groups[-1])<max_group and _can_join(groups[-1][-1],t,
                gap_ratio=gap_ratio,line_tolerance=line_tolerance):
                groups[-1].append(t)
            else:
                groups.append([t])
        for group in groups:
            if len(group)==1:
                merged.append(group[0])
                continue
            # Concatenation preserves identifier characters; no hallucinated
            # substitutions or dictionary-based corrections.
            bbox=[min(t["bbox"][0] for t in group),
                  min(t["bbox"][1] for t in group),
                  max(t["bbox"][2] for t in group),
                  max(t["bbox"][3] for t in group)]
            merged.append({"text":"".join(t["text"] for t in group),
                           "bbox":bbox})
    out["ocr"]=merged
    return out
