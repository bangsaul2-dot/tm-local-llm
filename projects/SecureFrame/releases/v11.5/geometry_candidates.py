"""Generic bounding-box candidate filtering for public diagrams.

Independent sanitized implementation. Does not infer engineering connections.
"""
from __future__ import annotations

def intersection_over_union(a, b):
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    intersection = max(0, right-left) * max(0, bottom-top)
    area_a = max(0, a[2]-a[0]) * max(0, a[3]-a[1])
    area_b = max(0, b[2]-b[0]) * max(0, b[3]-b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0

def deduplicate_boxes(boxes, threshold=0.85):
    """Deterministic overlap suppression; nested containers are retained."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between zero and one")
    candidates = sorted(
        (tuple(map(float, box)) for box in boxes),
        key=lambda b: (-(b[2]-b[0])*(b[3]-b[1]), b),
    )
    kept = []
    for candidate in candidates:
        if not any(intersection_over_union(candidate, old) >= threshold for old in kept):
            kept.append(candidate)
    return [list(box) for box in kept]

def classify_nested_boxes(boxes):
    """Assign parent indices from strict spatial containment only."""
    parents = []
    for i, inner in enumerate(boxes):
        candidates = []
        for j, outer in enumerate(boxes):
            if i == j:
                continue
            if (outer[0] <= inner[0] and outer[1] <= inner[1]
                    and outer[2] >= inner[2] and outer[3] >= inner[3]
                    and outer != inner):
                area = (outer[2]-outer[0])*(outer[3]-outer[1])
                candidates.append((area, j))
        parents.append(min(candidates)[1] if candidates else None)
    return parents
