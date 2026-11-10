# SecureFrame V11.7.1 — Hybrid Multiwire Candidate Release

**Status: Development / local validation required.** This is a sanitized generic implementation. It is not the original private local commit, and it has not been tested against the actual SFT image or human GT.

## R1: Physical wires vs logical edges

A logical edge can be supported by multiple independently traced physical wires. The output retains each `wire_id` and any explicit `bus_group_id`. Wire multiplicity alone no longer triggers ambiguous. The implementation does not infer a bus ID from a shared leaf pair.

A logical edge remains **candidate / needs_review / source_verified=false** if all matched, trace-verified wires are consistently oriented and agree with the semantic proposal. Unknown, conflicting, missing or multiple bus-group evidence is conservatively marked ambiguous. Even a candidate is **never automatically approved**.

**Critical precondition:** The upstream V11.6 adapter must provide independently traced, end-to-end `points`, correct arrow direction relative to point order, `trace_verified`, and optional bus-group ID. This release does **not** establish that those values are correct.

## R2/R3

OCR tokens are grouped into reading-order lines within OpenCV boxes. Names are matched to those lines or their concatenation. Ambiguous or duplicate box assignment abstains. Endpoint snapping uses boundary distance and competitor gap; no container endpoints. A future integration must calibrate tolerance by image scale and port/line geometry; the present defaults are provisional.

## R4/R5

`qwen_contract.py` provides a strict no-coordinate prompt, local inference callback contract and bounded schema retries. It does not implement Ollama transport or any network call. The fusion compares Qwen direction against arrow direction relative to wire point order and abstains on unknown/conflict.

## R6 GT

`evaluate(result, gt)` measures edge existence and directed edge precision/recall. Empty or directionless GT is NOT_EVALUABLE. GT must be independently annotated by a human and kept only on the Ubuntu machine. No actual SFT accuracy is claimed.

## R7/R8 validation

From the repository root:

```bash
git fetch origin
git switch --track origin/secureframe/v11.7.1-hybrid-bus-fix
cd projects/SecureFrame/releases/v11.7.1
python3 -m unittest discover -p 'test_*.py' -v
```

If already checked out, use `git switch secureframe/v11.7.1-hybrid-bus-fix`.

Before any real-data run: confirm local-only Ollama binding, blocked outbound access, local input paths, V11.6 adapter contract, OCR availability, independent human GT, immutable source hash, and DB read-only policy. Do not commit original images, OCR text, GT, SQLite or generated JSON.

## Required follow-up

1. Run regression tests on Ubuntu and report actual results.
2. Audit the local four-file adapter commit and compare the real wire mapping.
3. Verify whether the nine shared-leaf wires are truly the same logical bus; do not infer solely from endpoints.
4. Add independent segment tracing and arrowhead detector (not implemented here).
5. Calibrate OCR and snap thresholds against annotated public and private-local examples.
6. Integrate existing GT tooling without changing its original files.
7. Run human-GT existence and direction precision/recall; `pass_90` is not yet demonstrated.

**Security:** This branch contains generic source and synthetic tests only. No original private diagram, local operational DB, customer-specific names, source-derived formulas or real annotation JSON.
