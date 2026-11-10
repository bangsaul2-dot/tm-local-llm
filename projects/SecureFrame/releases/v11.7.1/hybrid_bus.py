"""SecureFrame V11.7.1: deterministic physical-wire / logical-edge fusion.

Synthetic/public-only source. No external requests or customer data.
All outputs are proposals; no approval or source verification.
"""
from __future__ import annotations
from collections import defaultdict
from difflib import SequenceMatcher
import json
import math
import re

DIRECTIONS = {"forward", "reverse", "unknown"}

def _norm(text):
    return re.sub(r"[^a-z0-9]+", "", str(text).casefold())

def _similarity(a, b):
    a, b = _norm(a), _norm(b)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0

def _valid_box(box):
    return (isinstance(box, (list, tuple)) and len(box) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in box)
            and box[2] > box[0] and box[3] > box[1])

def _center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

def _contains(box, point):
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]

def _token_lines(tokens):
    """Merge OCR tokens by line; deterministic reading order."""
    ordered = sorted(tokens, key=lambda t: (_center(t["bbox"])[1], t["bbox"][0], t["text"]))
    lines = []
    for token in ordered:
        y = _center(token["bbox"])[1]
        h = token["bbox"][3] - token["bbox"][1]
        candidates = [(abs(y - line["y"]), i) for i, line in enumerate(lines)
                      if abs(y - line["y"]) <= 0.45 * max(h, line["height"])]
        if candidates:
            index = min(candidates)[1]
            lines[index]["tokens"].append(token)
        else:
            lines.append({"y": y, "height": h, "tokens": [token]})
    return [" ".join(t["text"] for t in sorted(line["tokens"],
            key=lambda t: (t["bbox"][0], t["bbox"][1])))
            for line in sorted(lines, key=lambda line: line["y"])]

def validate_semantic(data):
    if not isinstance(data, dict) or set(data) != {"nodes", "edges"}:
        raise ValueError("semantic schema must contain only nodes and edges")
    if not isinstance(data["nodes"], list) or not isinstance(data["edges"], list):
        raise ValueError("nodes and edges must be arrays")
    names = {}
    for node in data["nodes"]:
        if not isinstance(node, dict) or set(node) != {"name", "kind", "parent"}:
            raise ValueError("node schema invalid; LLM coordinates prohibited")
        name = node["name"]
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError("node name missing or duplicated")
        if node["kind"] not in ("container", "leaf"):
            raise ValueError("invalid node kind")
        names[name] = node
    for name, node in names.items():
        parent = node["parent"]
        if parent is not None and (parent not in names or names[parent]["kind"] != "container"):
            raise ValueError("parent must be a known container")
        visited = set()
        cursor = name
        while cursor is not None:
            if cursor in visited:
                raise ValueError("container cycle")
            visited.add(cursor)
            cursor = names[cursor]["parent"]
    for edge in data["edges"]:
        if not isinstance(edge, dict) or set(edge) != {"from", "to", "direction"}:
            raise ValueError("edge schema invalid; LLM coordinates prohibited")
        if edge["from"] not in names or edge["to"] not in names:
            raise ValueError("unknown endpoint")
        if edge["direction"] not in DIRECTIONS:
            raise ValueError("invalid semantic direction")
    return data

def parse_semantic(text):
    """Strict JSON parsing; local caller may retry; no fabricated repairs."""
    return validate_semantic(json.loads(text))

def ground_nodes(semantic, geometry, min_score=0.84, margin=0.08):
    boxes, tokens = geometry.get("boxes", []), geometry.get("ocr", [])
    if not all(isinstance(b, dict) and _valid_box(b.get("bbox")) for b in boxes):
        raise ValueError("invalid OpenCV boxes")
    if not all(isinstance(t, dict) and _valid_box(t.get("bbox"))
               and isinstance(t.get("text"), str) for t in tokens):
        raise ValueError("invalid OCR tokens")
    grounded = []
    for node in semantic["nodes"]:
        ranked = []
        for index, box in enumerate(boxes):
            inside = [t for t in tokens if _contains(box["bbox"], _center(t["bbox"]))]
            if not inside:
                continue
            lines = _token_lines(inside)
            candidates = lines + [" ".join(lines)]
            score = max(_similarity(node["name"], text) for text in candidates)
            ranked.append((score, index))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        top = ranked[0] if ranked else None
        runner_up = ranked[1] if len(ranked) > 1 else None
        accepted = bool(top and top[0] >= min_score and
                        (runner_up is None or top[0] - runner_up[0] >= margin))
        grounded.append({**node, "bbox": boxes[top[1]]["bbox"] if accepted else None,
                         "box_index": top[1] if accepted else None,
                         "grounding": "grounded" if accepted else "needs_review"})
    by_box = defaultdict(list)
    for node in grounded:
        if node["box_index"] is not None:
            by_box[node["box_index"]].append(node)
    for duplicates in by_box.values():
        if len(duplicates) > 1:
            for node in duplicates:
                node.update(bbox=None, box_index=None, grounding="ambiguous")
    return grounded

def _distance_to_boundary(point, box):
    x, y = point
    if _contains(box, point):
        return min(x - box[0], box[2] - x, y - box[1], box[3] - y)
    return math.hypot(max(box[0] - x, 0, x - box[2]),
                      max(box[1] - y, 0, y - box[3]))

def snap_endpoint(point, nodes, tolerance=8.0, gap=2.0):
    """Abstain on close competitors; never snap to containers."""
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError("invalid point")
    candidates = sorted((_distance_to_boundary(point, n["bbox"]), n["name"])
                        for n in nodes if n["kind"] == "leaf" and n["bbox"] is not None)
    if not candidates or candidates[0][0] > tolerance:
        return {"name": None, "status": "unmatched"}
    if len(candidates) > 1 and candidates[1][0] - candidates[0][0] < gap:
        return {"name": None, "status": "ambiguous_endpoint"}
    return {"name": candidates[0][1], "status": "matched"}

def _physical_direction(wire, src, dst):
    """Arrow direction is relative to ordered wire points, not semantic edge order."""
    if wire["a"] == src and wire["b"] == dst:
        return wire["arrow"]
    if wire["a"] == dst and wire["b"] == src:
        return {"forward": "reverse", "reverse": "forward", "unknown": "unknown"}[wire["arrow"]]
    return "unknown"

def fuse(semantic, geometry, tolerance=8.0):
    validate_semantic(semantic)
    nodes = ground_nodes(semantic, geometry)
    names = {node["name"]: node for node in nodes}
    wires = []
    wire_ids = set()
    for wire in geometry.get("wires", []):
        if not isinstance(wire, dict) or not isinstance(wire.get("id"), str) or wire["id"] in wire_ids:
            raise ValueError("wire ID missing or duplicated")
        wire_ids.add(wire["id"])
        points = wire.get("points")
        if (not isinstance(points, list) or len(points) < 2
            or any(not isinstance(p, (list, tuple)) or len(p) != 2 or
                   any(type(v) not in (int, float) or not math.isfinite(v) for v in p)
                   for p in points)):
            raise ValueError("wire points invalid")
        arrow = wire.get("arrow_direction", "unknown")
        if arrow not in DIRECTIONS:
            raise ValueError("invalid arrow direction")
        a = snap_endpoint(points[0], nodes, tolerance)
        b = snap_endpoint(points[-1], nodes, tolerance)
        wires.append({"id": wire["id"], "bus_group_id": wire.get("bus_group_id"),
                      "a": a["name"], "b": b["name"], "a_status": a["status"],
                      "b_status": b["status"], "arrow": arrow,
                      "trace_verified": wire.get("trace_verified") is True})
    proposals = []
    for index, edge in enumerate(semantic["edges"]):
        src, dst = edge["from"], edge["to"]
        reasons = []
        if src == dst:
            reasons.append("self_loop")
        if names[src]["kind"] != "leaf" or names[dst]["kind"] != "leaf":
            reasons.append("container_endpoint")
        if names[src]["bbox"] is None or names[dst]["bbox"] is None:
            reasons.append("ungrounded_endpoint")
        matches = sorted((w for w in wires if w["trace_verified"]
                          and {w["a"], w["b"]} == {src, dst}
                          and w["a"] is not None and w["b"] is not None),
                         key=lambda w: w["id"])
        # Physical wire multiplicity is not itself a reason to reject a logical edge.
        # All matched wires are retained individually, without falsely merging buses.
        if not matches:
            reasons.append("wire_missing")
        physical = {_physical_direction(w, src, dst) for w in matches}
        known = physical - {"unknown"}
        if len(known) > 1:
            reasons.append("direction_conflict_between_wires")
        if "unknown" in physical:
            reasons.append("direction_partially_unverified")
        if edge["direction"] == "unknown":
            reasons.append("semantic_direction_unknown")
        if known and edge["direction"] != "unknown" and known != {edge["direction"]}:
            reasons.append("semantic_geometry_direction_conflict")
        # Grouping metadata is informative only; missing IDs do not cause auto-bus inference.
        bus_ids = sorted({str(w["bus_group_id"]) for w in matches if w["bus_group_id"] is not None})
        if len(bus_ids) > 1:
            reasons.append("multiple_bus_groups_require_review")
        direction = (edge["direction"] if not reasons else "unknown")
        proposals.append({"id": "proposal_%04d" % index, "from": src, "to": dst,
                          "wire_ids": [w["id"] for w in matches], "bus_group_ids": bus_ids,
                          "direction": direction, "status": "candidate" if not reasons else "ambiguous",
                          "review_state": "needs_review", "evidence_status": "candidate",
                          "source_verified": False, "reasons": sorted(set(reasons))})
    return {"schema_version": "v11.7.1", "nodes": nodes, "wires": wires,
            "edges": proposals, "auto_approval": False, "llm_coordinates_used": False}

def evaluate(result, gt):
    """Set-based metrics against independently human-authored GT."""
    if not isinstance(gt, dict) or not isinstance(gt.get("edges"), list) or not gt["edges"]:
        return {"status": "NOT_EVALUABLE", "pass_90": False}
    confirmed = [e for e in result["edges"] if e["status"] == "candidate"]
    def metric(predicted, truth):
        tp = len(predicted & truth)
        fp = len(predicted - truth)
        fn = len(truth - predicted)
        return {"tp": tp, "fp": fp, "fn": fn,
                "precision": tp / (tp + fp) if tp + fp else 0.0,
                "recall": tp / (tp + fn) if tp + fn else 0.0}
    truth_exist = {(e["from"], e["to"]) for e in gt["edges"]}
    truth_dir = {(e["from"], e["to"], e["direction"]) for e in gt["edges"]
                 if e.get("direction") in ("forward", "reverse")}
    if not truth_dir:
        return {"status": "NOT_EVALUABLE", "pass_90": False}
    exist = metric({(e["from"], e["to"]) for e in confirmed}, truth_exist)
    direct = metric({(e["from"], e["to"], e["direction"]) for e in confirmed
                     if e["direction"] != "unknown"}, truth_dir)
    return {"status": "EVALUATED", "existence": exist, "direction": direct,
            "direction_coverage": len([e for e in confirmed if e["direction"] != "unknown"])
                                  / len(confirmed) if confirmed else 0.0,
            "pass_90": all(m[k] >= 0.90 for m in (exist, direct)
                           for k in ("precision", "recall"))}
