"""SecureFrame V11.7.2 offline, synthetic-only adapter contract."""
from __future__ import annotations
import math

VALID_DIR = {"forward", "reverse", "unknown"}

def _point(p):
    return isinstance(p, (tuple, list)) and len(p) == 2 and all(type(x) in (int, float) and math.isfinite(x) for x in p)

def _bbox(b):
    return isinstance(b, (tuple, list)) and len(b) == 4 and _point(b[:2]) and _point(b[2:]) and b[0] < b[2] and b[1] < b[3]

def arrow_from_tip_base(points, tip, base, *, min_projection=0.15):
    """Return direction relative to ordered wire points; abstain if weak."""
    if not _point(tip) or not _point(base) or len(points) < 2 or not all(_point(p) for p in points):
        return "unknown"
    vx, vy = points[-1][0] - points[0][0], points[-1][1] - points[0][1]
    ax, ay = tip[0] - base[0], tip[1] - base[1]
    nv, na = math.hypot(vx, vy), math.hypot(ax, ay)
    if not nv or not na:
        return "unknown"
    cosine = (vx * ax + vy * ay) / (nv * na)
    return "forward" if cosine >= min_projection else "reverse" if cosine <= -min_projection else "unknown"

def normalize_wire(wire):
    if not isinstance(wire, dict):
        raise ValueError("wire must be a dict")
    result = dict(wire)
    if not isinstance(result.get("id"), str) or not result["id"].strip():
        raise ValueError("wire id required")
    points = result.get("points")
    if not isinstance(points, list) or len(points) < 2 or not all(_point(p) for p in points):
        raise ValueError("end-to-end points required")
    old, new = result.pop("bus_id", None), result.get("bus_group_id")
    if old is not None and new is not None and old != new:
        raise ValueError("conflicting bus identifiers")
    result["bus_group_id"] = new if new is not None else old
    if result["bus_group_id"] is not None and not isinstance(result["bus_group_id"], str):
        raise ValueError("bus group id must be a string")
    declared = result.get("arrow_direction", "unknown")
    if declared not in VALID_DIR:
        raise ValueError("invalid arrow direction")
    tip, base = result.get("arrowhead_tip"), result.get("arrowhead_base")
    measured = arrow_from_tip_base(points, tip, base) if tip is not None or base is not None else "unknown"
    if measured != "unknown" and declared != "unknown" and measured != declared:
        result["arrow_direction"] = "unknown"
        result["direction_conflict"] = True
    else:
        result["arrow_direction"] = measured if measured != "unknown" else declared
        result["direction_conflict"] = False
    result["arrow_geometry_verified"] = measured != "unknown" and not result["direction_conflict"]
    result["trace_verified"] = result.get("trace_verified") is True
    return result

def adaptive_snap(point, nodes, *, scale=1.0, base_tolerance=8.0,
                  max_tolerance=16.0, min_gap=2.0, incoming_vector=None):
    """Snap to nearest leaf boundary; abstain on competing leaf or tangent."""
    if not _point(point) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("invalid point or scale")
    tolerance = min(max_tolerance, max(base_tolerance, 12.0 * scale))
    candidates = []
    for node in nodes:
        b = node.get("bbox")
        if node.get("kind") != "leaf" or not _bbox(b):
            continue
        x, y = point
        dx = max(b[0] - x, 0, x - b[2])
        dy = max(b[1] - y, 0, y - b[3])
        distance = math.hypot(dx, dy) if dx or dy else min(x-b[0], b[2]-x, y-b[1], b[3]-y)
        if distance <= tolerance:
            candidates.append((distance, str(node["name"]), b))
    candidates.sort(key=lambda t: (t[0], t[1]))
    if not candidates:
        return {"name": None, "status": "unmatched", "tolerance": tolerance}
    if len(candidates) > 1 and candidates[1][0] - candidates[0][0] < min_gap * scale:
        return {"name": None, "status": "ambiguous_endpoint", "tolerance": tolerance}
    distance, name, b = candidates[0]
    if incoming_vector is not None:
        if not _point(incoming_vector):
            raise ValueError("invalid incoming vector")
        vx, vy = incoming_vector
        norm = math.hypot(vx, vy)
        if norm < 1e-9:
            return {"name": None, "status": "ambiguous_angle", "tolerance": tolerance}
        x, y = point
        side = min(((abs(x-b[0]), "vertical"), (abs(x-b[2]), "vertical"),
                    (abs(y-b[1]), "horizontal"), (abs(y-b[3]), "horizontal")))[1]
        normal_component = abs(vx)/norm if side == "vertical" else abs(vy)/norm
        if normal_component < 0.5:
            return {"name": None, "status": "ambiguous_angle", "tolerance": tolerance}
    return {"name": name, "status": "matched", "tolerance": tolerance, "distance": distance}

def normalize_geometry(geometry):
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be dict")
    wires = [normalize_wire(w) for w in geometry.get("wires", [])]
    if len({w["id"] for w in wires}) != len(wires):
        raise ValueError("duplicate wire id")
    for box in geometry.get("boxes", []):
        if not _bbox(box.get("bbox")):
            raise ValueError("invalid box")
    for token in geometry.get("ocr", []):
        if not _bbox(token.get("bbox")) or not isinstance(token.get("text"), str):
            raise ValueError("invalid OCR token")
    return {"boxes": list(geometry.get("boxes", [])),
            "ocr": list(geometry.get("ocr", [])), "wires": wires}
