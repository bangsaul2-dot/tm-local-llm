"""Offline, deterministic, proposal-only semantic/geometry fusion.
No network calls, image assets, original documents, or operational records.
"""
import json
import math
import re
from difflib import SequenceMatcher

def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).casefold())

def _score(a, b):
    a, b = _norm(a), _norm(b)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0

def _box(b):
    return (isinstance(b, list) and len(b) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in b)
            and b[2] > b[0] and b[3] > b[1])

def _inside(b, p):
    return b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]

def validate_semantic(obj):
    if not isinstance(obj, dict) or set(obj) != {"nodes", "edges"}:
        raise ValueError("semantic requires exactly nodes and edges")
    if not isinstance(obj["nodes"], list) or not isinstance(obj["edges"], list):
        raise ValueError("nodes and edges must be arrays")
    nodes, names = [], set()
    for n in obj["nodes"]:
        if not isinstance(n, dict) or set(n) != {"name", "kind", "parent"}:
            raise ValueError("invalid semantic node schema; coordinates forbidden")
        name = n["name"]
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError("invalid or duplicate name")
        if n["kind"] not in ("leaf", "container"):
            raise ValueError("invalid node kind")
        names.add(name)
        nodes.append(dict(n))
    by_name = {n["name"]: n for n in nodes}
    for n in nodes:
        p = n["parent"]
        if p is not None and (p not in by_name or by_name[p]["kind"] != "container"):
            raise ValueError("parent must refer to container")
        seen, cur = set(), n["name"]
        while cur is not None:
            if cur in seen:
                raise ValueError("parent cycle")
            seen.add(cur)
            cur = by_name[cur]["parent"]
    for e in obj["edges"]:
        if not isinstance(e, dict) or set(e) != {"from", "to", "direction"}:
            raise ValueError("invalid semantic edge schema; coordinates forbidden")
        if e["from"] not in names or e["to"] not in names:
            raise ValueError("unknown endpoint")
        if e["direction"] not in ("forward", "reverse", "unknown"):
            raise ValueError("invalid direction")
    return obj

def parse_semantic(text):
    """Strict JSON; invalid responses must be retried by local caller."""
    return validate_semantic(json.loads(text))

def ground_nodes(semantic, geometry, threshold=.84, margin=.08):
    boxes = geometry.get("boxes", [])
    ocr = geometry.get("ocr", [])
    if not all(isinstance(b, dict) and _box(b.get("bbox")) for b in boxes):
        raise ValueError("invalid geometry boxes")
    if not all(isinstance(o, dict) and _box(o.get("bbox"))
               and isinstance(o.get("text"), str) for o in ocr):
        raise ValueError("invalid OCR")
    result = []
    for n in semantic["nodes"]:
        ranked = []
        for i, box in enumerate(boxes):
            texts = [o["text"] for o in ocr if _inside(box["bbox"],
                [(o["bbox"][0]+o["bbox"][2])/2, (o["bbox"][1]+o["bbox"][3])/2])]
            if texts:
                score = max(_score(n["name"], t) for t in texts)
                area = (box["bbox"][2]-box["bbox"][0])*(box["bbox"][3]-box["bbox"][1])
                ranked.append((score, -area if n["kind"] == "container" else area, i))
        ranked.sort(key=lambda x: (-x[0], x[1], x[2]))
        best = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None
        # Do not invent coordinates or force a choice between ambiguous boxes.
        if best and best[0] >= threshold and (not second or best[0]-second[0] >= margin):
            idx = best[2]
            result.append({**n, "bbox": boxes[idx]["bbox"], "box_index": idx, "grounding": "grounded"})
        else:
            result.append({**n, "bbox": None, "box_index": None,
                           "grounding": "ambiguous" if best and best[0] >= threshold else "ungrounded"})
    occupancy = {}
    for i, n in enumerate(result):
        if n["box_index"] is not None:
            occupancy.setdefault(n["box_index"], []).append(i)
    for ids in occupancy.values():
        if len(ids) > 1:
            for i in ids:
                result[i].update(bbox=None, box_index=None, grounding="ambiguous")
    return result

def _distance(p, b):
    x, y = p
    if _inside(b, p):
        return min(x-b[0], b[2]-x, y-b[1], b[3]-y)
    return math.hypot(max(b[0]-x, 0, x-b[2]), max(b[1]-y, 0, y-b[3]))

def _endpoints(point, nodes, tolerance):
    return sorted(n["name"] for n in nodes if n["kind"] == "leaf"
                  and n["bbox"] is not None and _distance(point, n["bbox"]) <= tolerance)

def fuse(semantic, geometry, tolerance=8):
    semantic = validate_semantic(semantic)
    nodes = ground_nodes(semantic, geometry)
    wires, ids = [], set()
    for w in geometry.get("wires", []):
        if not isinstance(w, dict) or not isinstance(w.get("id"), str) or w["id"] in ids:
            raise ValueError("invalid or duplicate wire ID")
        ids.add(w["id"])
        points = w.get("points")
        if not isinstance(points, list) or len(points) < 2 or not all(
            isinstance(p, list) and len(p) == 2
            and all(type(v) in (int,float) and math.isfinite(v) for v in p)
            for p in points):
            raise ValueError("invalid wire geometry")
        if w.get("arrow_direction", "unknown") not in ("forward", "reverse", "unknown"):
            raise ValueError("invalid arrow direction")
        wires.append({"id": w["id"], "bus_id": w.get("bus_id"),
                      "a": _endpoints(points[0], nodes, tolerance),
                      "b": _endpoints(points[-1], nodes, tolerance),
                      "arrow": w.get("arrow_direction", "unknown"),
                      "trace_verified": w.get("trace_verified") is True})
    by_name = {n["name"]: n for n in nodes}
    edges = []
    for i, e in enumerate(semantic["edges"]):
        src, dst = e["from"], e["to"]
        reasons = []
        if src == dst: reasons.append("self_loop")
        if by_name[src]["kind"] != "leaf" or by_name[dst]["kind"] != "leaf":
            reasons.append("container_endpoint")
        if by_name[src]["bbox"] is None or by_name[dst]["bbox"] is None:
            reasons.append("ungrounded_endpoint")
        matches = [w for w in wires if w["trace_verified"] and
                   ((src in w["a"] and dst in w["b"]) or
                    (src in w["b"] and dst in w["a"]))]
        direction, wire_id = "unknown", None
        if len(matches) != 1:
            reasons.append("wire_missing_or_ambiguous")
        else:
            w = matches[0]
            wire_id = w["id"]
            # Ordered wire orientation is never used as arrow evidence.
            forward = src in w["a"] and dst in w["b"]
            backward = src in w["b"] and dst in w["a"]
            if forward == backward:
                reasons.append("endpoint_orientation_ambiguous")
            elif w["arrow"] == "unknown" or e["direction"] == "unknown":
                reasons.append("direction_unverified")
            else:
                physical = w["arrow"] if forward else (
                    "reverse" if w["arrow"] == "forward" else "forward")
                if physical != e["direction"]:
                    reasons.append("direction_conflict")
                else:
                    direction = physical
        status = "candidate" if not reasons else "ambiguous"
        edges.append({"id": "proposal_%04d" % i, "from": src, "to": dst,
                      "wire_id": wire_id, "direction": direction,
                      "status": status, "review_state": "needs_review",
                      "evidence_status": "candidate", "source_verified": False,
                      "reasons": reasons})
    return {"schema_version": "v11.7", "nodes": nodes, "wires": wires,
            "edges": edges, "policy": {"auto_approval": False,
                                      "llm_coordinates_used": False,
                                      "external_network": False}}

def evaluate(pred, gt):
    """GT edges are human-authored. Unresolved predictions are not positives."""
    eligible = [e for e in pred["edges"] if e["status"] == "candidate" and not e["reasons"]]
    def score(p, g):
        tp = len(p & g)
        fp = len(p - g)
        fn = len(g - p)
        return {"tp": tp, "fp": fp, "fn": fn,
                "precision": tp/(tp+fp) if tp+fp else 0.0,
                "recall": tp/(tp+fn) if tp+fn else 0.0}
    existence = score({(e["from"],e["to"]) for e in eligible},
                      {(e["from"],e["to"]) for e in gt["edges"]})
    direction = score({(e["from"],e["to"],e["direction"]) for e in eligible if e["direction"] != "unknown"},
                      {(e["from"],e["to"],e["direction"]) for e in gt["edges"] if e.get("direction") in ("forward","reverse")})
    return {"existence": existence, "direction": direction,
            "pass_90": all(x["precision"] >= .9 and x["recall"] >= .9 for x in (existence, direction))}
