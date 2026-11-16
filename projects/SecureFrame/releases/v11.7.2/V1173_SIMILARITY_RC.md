# SecureFrame V11.7.3 similarity — release candidate, NOT production release

Base: P1/P2 integration + P1 diagnostics + opt-in OCR join (join stays disabled).
New: `candidate_similarity.py` and `test_candidate_similarity.py` (22 synthetic cases).

## Objective

OCR text vs Qwen semantic labels can differ despite OCR tokens existing in every box. Compare normalized labels, token fragments, bounded contiguous token windows, and protected numeric identifiers. Produce *review-only candidate rankings*, not accepted grounding. Existing `hybrid_bus.ground_nodes`, `qwen_contract`, `adapter_contract`, `hybrid_fusion` remain unchanged.

## Safety

- No changes to original geometry, semantic, OCR, DB, Graph or approval state.
- Numeric sequences must match exactly, in order (including leading zeroes).
- Only NFKC, case folding and alphanumeric comparison. No O/0, I/1 or other speculative substitutions.
- Ambiguous top boxes and duplicate node-to-box claims abstain.
- Substrings shorter than five characters do not get boosted.
- No coordinate output, OCR label, source image, file path or Qwen raw response in `aggregate()`.
- `rank_candidates()` is PRIVATE IN-MEMORY ONLY; contains private names and box indices and MUST NOT be logged, printed or serialized.
- `auto_approval=False`, `source_verified=False`, `review_state=needs_review`, `pass_90=NOT_EVALUABLE`.

## Synthetic checks

```bash
cd projects/SecureFrame/releases/v11.7.2
python3 -m unittest discover -p 'test_*.py' -v
```

Expected test count if prior Ubuntu suite has 50: **72** (50+22). This is a target, not a claimed test result.

## Internal A/B only (figure_000 and several other figures)

Keep one fixed `semantic` response (seed=42) and one fixed `geometry`.
Use `rank_candidates(semantic,geometry)` and `aggregate(proposals)`.
Only print aggregate metrics; never print the private `proposals` list.
Compare against baseline grounded=13/32, edge_candidates=0, low_text_similarity=18.
New candidate counts are NOT grounded counts and must not be substituted for them.
Do not route candidates to `fuse_grounded` or approval pipeline before independent local evaluation and review.

## Release gate

1. All prior 50 tests + 22 new synthetic tests PASS.
2. No byte changes to four approved modules.
3. Local synthetic ground-truth test sets cover positive AND negative matches; false-positive acceptance remains zero for protected digit mismatches.
4. Internal A/B on figure_000 and additional figures shows non-regressive candidate ranking with no privacy leak.
5. Promote only after documented evidence. Human GT required for a real-world accuracy percentage, not for development testing.

If any gate fails, keep as RC and report exact counts only.
