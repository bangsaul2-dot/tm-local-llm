# SecureFrame V11.7.2 — Adaptive Fusion (Development Release)

**Scope:** security-sanitized, offline-only generic source; **not** a production replacement or proof of SFT pass_90. Based on the V11.7.1 development branch. Original operational SQLite, approved graph, SFT image, OCR outputs, GT and customer-derived JSON are excluded.

## Changes
- Normalize V11.6 `bus_id` to canonical `bus_group_id`; reject conflicting aliases.
- Preserve independently traced physical `wire_id` values within a candidate logical edge.
- Use an adaptive endpoint tolerance (default 12 px at scale 1, capped at 16 px), with competing-leaf ambiguity protection.
- Optionally reject tangential endpoint approaches when an independently measured incoming vector is provided.
- Cross-check existing `arrowhead_tip`/`arrowhead_base` against ordered wire `points`; conflicting evidence becomes unknown/ambiguous.
- Reject duplicate wire IDs, invalid geometry and container endpoints.
- Never auto-approve: `status=candidate|ambiguous`, `review_state=needs_review`, `source_verified=false`.

## Contract
```json
{
  "boxes": [{"bbox": [0, 0, 30, 40]}],
  "ocr": [{"text": "Example", "bbox": [1, 1, 20, 10]}],
  "wires": [{
    "id": "w0",
    "points": [[42, 20], [88, 20]],
    "bus_id": "bus_0",
    "arrow_direction": "forward",
    "arrowhead_tip": [80, 20],
    "arrowhead_base": [75, 20],
    "trace_verified": true
  }]
}
```
`bus_group_id` may replace `bus_id`. If both are present, they must agree. `trace_verified=true` must be independently established by the upstream local segment tracer. Arrow direction is relative to point order; geometric arrow evidence is optional but disagreement forces ambiguity. The sample is synthetic.

`fuse_grounded(semantic, geometry, grounded_nodes, scale=1.0)` expects independently pixel-grounded nodes. **Do not pass model-generated bounding boxes.** Semantic nodes and hierarchy must be validated upstream (V11.7.1 `validate_semantic`); this module does not perform Qwen/Ollama calls or OCR extraction.

## Offline tests
```bash
cd projects/SecureFrame/releases/v11.7.2
python3 -m unittest discover -p 'test_*.py' -v
```
The standalone synthetic suite has 16 tests. It was executed before publication in the development workspace (16/16). Run again on Ubuntu; actual SFT validation and human GT scoring remain pending.

## Remaining gates
1. Integrate with existing V11.6 adapter; validate 12 physical wire records and bus_0..2 locally.
2. Confirm that 4 parallel wires remain associated with one candidate without incorrect leaf snapping.
3. Connect server-local OCR/Tesseract; measure grounded vs ungrounded leaf counts.
4. Connect server-local Ollama/Qwen through the strict V11.7.1 JSON contract; no remote inference.
5. Use independent human GT to evaluate existence and direction precision/recall; absent GT = NOT_EVALUABLE.
6. Verify existing operating DB, graph approvals and input image hashes unchanged.
7. No source_verified promotion without human approval.

**Known limitation:** tolerance uses an image scale parameter, not fully inferred port geometry. Segment tracing and OCR/Ollama transport are not included. A matched logical edge remains an unapproved proposal, not a verified engineering connection.
