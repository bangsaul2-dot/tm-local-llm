"""Offline V11.6 endpoint correction proposals. Never mutate the source geometry."""
from __future__ import annotations
import copy
import math

def _point(p):
    return isinstance(p,(list,tuple)) and len(p)==2 and all(
        type(v) in (int,float) and math.isfinite(v) for v in p)

def _box(b):
    return isinstance(b,(list,tuple)) and len(b)==4 and all(
        type(v) in (int,float) and math.isfinite(v) for v in b) and b[0]<b[2] and b[1]<b[3]

def _intersection(p, q, bbox, max_extension, *, eps=1e-9):
    """Ray from endpoint p away from adjacent point q; only actual face crossings."""
    dx,dy=p[0]-q[0],p[1]-q[1]
    norm=math.hypot(dx,dy)
    if norm<=eps:
        return []
    ux,uy=dx/norm,dy/norm
    x0,y0,x1,y1=bbox
    hits=[]
    for face,coord,component,other,lo,hi in (
        ("left",x0,ux,uy,y0,y1),("right",x1,ux,uy,y0,y1),
        ("top",y0,uy,ux,x0,x1),("bottom",y1,uy,ux,x0,x1)):
        axis_value=p[0] if face in ("left","right") else p[1]
        if abs(component)<=eps:
            continue
        distance=(coord-axis_value)/component
        if distance < -eps or distance > max_extension+eps:
            continue
        other_value=(p[1] if face in ("left","right") else p[0])+distance*other
        if lo-eps <= other_value <= hi+eps:
            hit=[coord,other_value] if face in ("left","right") else [other_value,coord]
            hits.append({"point":hit,"face":face,"distance":max(0.0,distance)})
    return hits

def propose_endpoint_correction(wire, leaves, *, max_extension=12.0,
                                competitor_gap=2.0, eps=1e-7):
    """Returns candidate or abstention. No changes to input or approval state.

    Extension only, not arbitrary translation. Caller must verify independently
    that the supplied leaf geometry and wire trace are source-grounded.
    """
    if not isinstance(wire,dict) or not isinstance(wire.get("points"),list) or len(wire["points"])<2:
        raise ValueError("invalid wire")
    if not all(_point(p) for p in wire["points"]):
        raise ValueError("invalid wire points")
    if not math.isfinite(max_extension) or max_extension<=0 or not math.isfinite(competitor_gap) or competitor_gap<0:
        raise ValueError("invalid tolerances")
    if not isinstance(leaves,list) or any(not isinstance(n,dict) or not _box(n.get("bbox")) or not isinstance(n.get("name"),str) for n in leaves):
        raise ValueError("invalid leaves")
    output={"wire_id":wire.get("id"),"_source_points":copy.deepcopy(wire["points"]),
            "proposed_points":copy.deepcopy(wire["points"]),
            "status":"needs_review","source_verified":False,"auto_approval":False,
            "corrections":[],"reasons":[]}
    if wire.get("trace_verified") is not True:
        output["reasons"].append("trace_unverified")
        return output
    for endpoint,adjacent in ((0,1),(-1,-2)):
        p,q=wire["points"][endpoint],wire["points"][adjacent]
        hits=[]
        for node in leaves:
            if node.get("kind")!="leaf":
                continue
            for hit in _intersection(p,q,node["bbox"],max_extension):
                hits.append({**hit,"leaf":node["name"]})
        hits.sort(key=lambda h:(h["distance"],h["leaf"],h["face"]))
        if not hits:
            output["reasons"].append("no_face_intersection")
            continue
        if len(hits)>1 and hits[1]["distance"]-hits[0]["distance"]<=competitor_gap+eps:
            output["reasons"].append("ambiguous_face_or_competitor")
            continue
        chosen=hits[0]
        if chosen["distance"]<=eps:
            continue
        output["proposed_points"][endpoint]=chosen["point"]
        output["corrections"].append({"endpoint":"start" if endpoint==0 else "end",
            "leaf":chosen["leaf"],"face":chosen["face"],
            "from":copy.deepcopy(p),"to":chosen["point"],
            "extension_px":chosen["distance"],"evidence":"ray_face_intersection"})
    if not output["corrections"]:
        output["reasons"].append("no_safe_correction")
    output["reasons"]=sorted(set(output["reasons"]))
    return output
