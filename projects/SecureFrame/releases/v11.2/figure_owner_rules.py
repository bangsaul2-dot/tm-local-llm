"""Generic diagram ownership routing. Sanitized reimplementation of a V11.2 concept.

No customer labels, technical formulas, or source documents are embedded.
"""
from __future__ import annotations
import re

def assign_owner(figures, topics, rules):
    """Return proposals for figure-to-topic ownership, without approving them."""
    topic_names = {str(t["name"]) for t in topics}
    result = []
    for figure in figures:
        title = str(figure.get("title", ""))
        matches = []
        for rule in rules:
            owner = str(rule["owner_topic"])
            if owner not in topic_names:
                raise ValueError("Unknown owner topic")
            if re.search(str(rule["pattern"]), title, flags=re.IGNORECASE):
                matches.append(owner)
        result.append({
            "figure_id": figure["id"],
            "candidate_owner": matches[0] if len(set(matches)) == 1 else None,
            "status": "needs_review",
            "conflict": len(set(matches)) > 1,
        })
    return result
