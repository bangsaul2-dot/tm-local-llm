"""Generic graph proposal safety validation.

This is a sanitized standalone reimplementation, not a historical source snapshot.
No automatic evidence approval is performed.
"""
from __future__ import annotations
import re

VALID_OUTPUT = {"out", "inout"}
VALID_INPUT = {"in", "inout"}
PDF_REF = re.compile(r"(?i)\.pdf\s+(?:p\.|page\s+)\d+(?:\b|$)")

def validate_edge(edge, nodes):
    """Return deterministic rejection reasons for a proposed directed edge."""
    reasons = []
    source, target = edge.get("from"), edge.get("to")
    if source not in nodes or target not in nodes:
        reasons.append("missing_node")
        return reasons
    if source == target:
        reasons.append("self_loop_requires_manual_review")
    if edge.get("from_port_direction") not in VALID_OUTPUT:
        reasons.append("invalid_source_port_direction")
    if edge.get("to_port_direction") not in VALID_INPUT:
        reasons.append("invalid_target_port_direction")
    if edge.get("evidence_status") == "source_verified":
        if not PDF_REF.search(str(edge.get("source_ref", ""))):
            reasons.append("invalid_source_reference")
        if edge.get("reviewer_approved") is not True:
            reasons.append("missing_human_approval")
    return reasons

def check_graph(graph):
    """Inspect without mutating the input or approving candidates."""
    nodes = {node["id"] for node in graph.get("nodes", [])}
    results = []
    for index, edge in enumerate(graph.get("edges", [])):
        reasons = validate_edge(edge, nodes)
        approved = (not reasons and edge.get("evidence_status") == "source_verified"
                    and edge.get("reviewer_approved") is True)
        results.append({"index": index, "id": edge.get("id"),
                        "eligible_for_reviewed_render": approved,
                        "reasons": reasons})
    return {"edge_count": len(results),
            "approved_edge_count": sum(r["eligible_for_reviewed_render"] for r in results),
            "results": results}
