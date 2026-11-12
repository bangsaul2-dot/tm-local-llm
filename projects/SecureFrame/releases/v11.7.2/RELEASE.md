# SecureFrame V11.7.2 — Axis Snap Logical Bus Grounding Release

**Status: PROMOTED — logical bus grounding gate only.**
**Validated source commit:** `08c416c5f252222ed8d4da20a055038dc830153d`
**Release branch:** `secureframe/v11.7.2-axis-snap-release`
**Validation authority:** OpenCode private/local report; underlying customer data, logs and GT are not published.

## Validated outcomes (reported by OpenCode)

- Synthetic regression: **27/27 PASS**
- Corner, top-edge, true tangent abstention and competing-leaf negative cases: PASS
- Logical bus grounding: **PASS** — 3 geometrically consistent traced wires support one logical candidate, bus group preserved.
- **Physical 4/4: FAIL (3/4)**. One wire is excluded due to upstream V11.6 geometry; **no recovery claimed**.
- Deterministic repeated input: PASS
- No automatic approval, `source_verified=False`, `review_state=needs_review`, no LLM-derived coordinates.
- Operational SQLite, original diagram and approved graph unchanged; no external transfer reported.
- Independent human GT absent: `pass_90=NOT_EVALUABLE`.

## Acceptance scope

The revised gate allows a logical bus candidate grounded by one or more consistent physical traces, provided all excluded traces remain explicitly unverified and the output is never auto-approved. This **does not** substitute for physical wire recall, 4/4 connectivity, or whole-diagram edge existence/direction precision and recall. For this case, 3 wires are grounded and one is excluded.

## Immutable algorithm provenance

This release branch starts from the validated RC source commit. No algorithm or test edits were made as part of promotion. The only added artifact is this release declaration. The earlier RC_GATE.md contains the detailed conditional gate amendment.

## Follow-on work (separate change)

Repair the upstream V11.6 endpoint geometry using independently measured segment-to-face intersection, retaining original and proposed points; require new negative cases before accepting a corrected physical 4/4. Then integrate local OCR/OpenCV grounding and Qwen semantics and evaluate against independently labeled human GT. Do not claim pass_90 until measured.

## Safety

Never publish proprietary original images, operational code, actual traces, private validation report, GT, SQLite or internal logs. All edges remain unapproved candidates; human-only source verification.
