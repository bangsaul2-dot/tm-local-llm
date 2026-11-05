"""Public-only diagram benchmark utilities. No customer data or network access."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def box_iou(a, b) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0

def score_boxes(predicted, truth, iou_threshold=0.5):
    """One-to-one GT matching, without counting a GT box twice."""
    pairs = sorted(
        ((box_iou(p, g), i, j) for i, p in enumerate(predicted)
         for j, g in enumerate(truth)),
        reverse=True,
    )
    used_p, used_g = set(), set()
    for overlap, i, j in pairs:
        if overlap < iou_threshold:
            break
        if i not in used_p and j not in used_g:
            used_p.add(i)
            used_g.add(j)
    tp = len(used_p)
    fp, fn = len(predicted) - tp, len(truth) - tp
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
    }

def evaluate_manifest(manifest_path, output_path):
    """Evaluate only entries with independent, explicitly supplied public GT."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    results = []
    for item in manifest:
        if item.get("classification") != "public" or not item.get("license_reviewed"):
            raise ValueError("Only license-reviewed public examples are permitted")
        if "ground_truth_boxes" not in item:
            results.append({"id": item["id"], "status": "NOT_MEASURED"})
            continue
        metric = score_boxes(item.get("predicted_boxes", []), item["ground_truth_boxes"])
        results.append({"id": item["id"], "status": "NODE_ONLY_GT_EVALUATED", **metric})
    report = {"results": results, "full_graph_accuracy": None, "winner": None}
    Path(output_path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
