# P1 OCR text combination — experimental, opt-in

The module `ocr_text_combine.combine_ocr_tokens(geometry)` is a **pure in-memory preprocessor** for the existing `hybrid_bus.ground_nodes`. No approved module is changed. No automatic correction, semantic-driven merge, output of coordinates or automatic approval.

## Internal-only A/B experiment

After the existing P1/P2 pipeline has produced in-memory `semantic`, `geometry` and `grounded_nodes` (do not serialize these objects):

```python
from ocr_text_combine import combine_ocr_tokens
from hybrid_bus import ground_nodes
from p1_grounding_diagnostics import diagnose_grounding

before = diagnose_grounding(semantic, geometry, grounded_nodes)
combined_geometry = combine_ocr_tokens(geometry)
after_nodes = ground_nodes(semantic, combined_geometry, min_score=0.84, margin=0.08)
after = diagnose_grounding(semantic, combined_geometry, after_nodes)
# Only emit aggregated count dictionaries; do not print raw inputs.
print({"before": before["unmatched_reason_counts"],
       "after": after["unmatched_reason_counts"],
       "grounded_before": before["grounded_count"],
       "grounded_after": after["grounded_count"]})
```

**Important:** `diagnose_grounding` is heuristic. It approximates token matching differently from `ground_nodes` (line grouping); the before/after counts are diagnostic, not GT precision or recall. Do not interpret a decrease in `low_text_similarity` as proof of improved correctness. Also compare grounded, ambiguous and edge candidate counts. The production pipeline remains unchanged until A/B validation passes.

Conservative rules: only combine adjacent alphanumeric-containing OCR fragments assigned unambiguously to the **same** geometry box; same text line and bounded horizontal gap; maximum four fragments by default. NFKC normalization only, no fuzzy label injection, no dictionary substitutions, no cross-box joins. Some diagrams may worsen; keep opt-in.

Run: `python3 -m unittest discover -p 'test_*.py' -v`. Expected total: prior 39 + new 11 = 50, subject to Ubuntu validation.

Safety: no external network, source mutation, DB/Graph writes, auto approval, coordinate printing or private data in repository. `pass_90=NOT_EVALUABLE`.
