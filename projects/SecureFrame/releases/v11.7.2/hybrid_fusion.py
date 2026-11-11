"""V11.7.2 offline multiwire fusion; all results are unapproved proposals."""
from __future__ import annotations
from adapter_contract import normalize_geometry, adaptive_snap

def fuse_grounded(semantic, geometry, grounded_nodes, *, scale=1.0):
    """grounded_nodes must originate from pixel OCR/OpenCV, never LLM coordinates."""
    if not isinstance(semantic, dict) or not isinstance(semantic.get("edges"), list):
        raise ValueError("invalid semantic input")
    if not isinstance(grounded_nodes, list):
        raise ValueError("grounded_nodes must be list")
    nodes = {n["name"]: n for n in grounded_nodes}
    geometry = normalize_geometry(geometry)
    wires = []
    for w in geometry["wires"]:
        # At the first endpoint, the incoming vector points back from the
        # second point toward the first; at the last, it points from the
        # penultimate point toward the last. Neither vector is LLM-derived.
        points = w["points"]
        start_vector = [points[0][0] - points[1][0],
                        points[0][1] - points[1][1]]
        end_vector = [points[-1][0] - points[-2][0],
                      points[-1][1] - points[-2][1]]
        a = adaptive_snap(points[0], grounded_nodes, scale=scale,
                          incoming_vector=start_vector)
        b = adaptive_snap(points[-1], grounded_nodes, scale=scale,
                          incoming_vector=end_vector)
        wires.append({**w, "a": a["name"], "b": b["name"],
                      "a_status": a["status"], "b_status": b["status"]})
    edges = []
    for index, edge in enumerate(semantic["edges"]):
        if set(edge) != {"from", "to", "direction"}:
            raise ValueError("edge schema invalid")
        src, dst = edge["from"], edge["to"]
        if src not in nodes or dst not in nodes:
            raise ValueError("unknown semantic node")
        reasons = []
        if src == dst: reasons.append("self_loop")
        if nodes[src].get("kind") != "leaf" or nodes[dst].get("kind") != "leaf":
            reasons.append("container_endpoint")
        if nodes[src].get("bbox") is None or nodes[dst].get("bbox") is None:
            reasons.append("ungrounded_endpoint")
        matches = sorted((w for w in wires if w["trace_verified"] and
                          w["a"] is not None and w["b"] is not None and
                          {w["a"], w["b"]} == {src, dst}), key=lambda w:w["id"])
        if not matches:
            reasons.append("wire_missing")
            # Angle failures must remain visible, not silently disappear.
            if any(w["a_status"] == "ambiguous_angle" or
                   w["b_status"] == "ambiguous_angle" for w in wires):
                reasons.append("endpoint_angle_unverified")
        bus_ids = sorted({w["bus_group_id"] for w in matches if w["bus_group_id"] is not None})
        if len(bus_ids) > 1: reasons.append("multiple_bus_groups_require_review")
        if any(w["direction_conflict"] for w in matches): reasons.append("arrow_geometry_conflict")
        directions = set()
        for w in matches:
            direction = w["arrow_direction"]
            if w["a"] == dst and w["b"] == src:
                direction = {"forward":"reverse","reverse":"forward","unknown":"unknown"}[direction]
            directions.add(direction)
        if "unknown" in directions: reasons.append("direction_partially_unverified")
        known = directions - {"unknown"}
        if len(known) > 1: reasons.append("direction_conflict_between_wires")
        if edge["direction"] not in ("forward", "reverse"):
            reasons.append("semantic_direction_unknown")
        elif known and known != {edge["direction"]}:
            reasons.append("semantic_geometry_direction_conflict")
        reasons = sorted(set(reasons))
        edges.append({"id":f"proposal_{index:04d}", "from":src, "to":dst,
                      "wire_ids":[w["id"] for w in matches], "bus_group_ids":bus_ids,
                      "direction":edge["direction"] if not reasons else "unknown",
                      "status":"candidate" if not reasons else "ambiguous",
                      "review_state":"needs_review","evidence_status":"candidate",
                      "source_verified":False,"reasons":reasons})
    return {"schema_version":"v11.7.2","nodes":grounded_nodes,"wires":wires,"edges":edges,
            "auto_approval":False,"llm_coordinates_used":False}
