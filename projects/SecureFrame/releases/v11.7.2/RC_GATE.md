# SecureFrame V11.7.2 Axis Snap — BLOCKED RELEASE CANDIDATE

**Do not merge or deploy until local regression gate passes.**

## Origin of block

Previous angle-contract patch: 5/21 failures and 1/4 real parallel wires matched (reported by internal validator). The baseline remains the prior V11.7.2 adaptive-fusion branch.

## Candidate changes

- `adaptive_snap` now chooses a contact face from the observed wire axis:
  - horizontal: left/right x-facing boundary; check x-face distance and vertical offset
  - vertical: top/bottom y-facing boundary; check y-face distance and horizontal offset
- Do not choose face by nearest Euclidean corner or lexicographic orientation string.
- Retain competitor ambiguity, container exclusion, tolerance 12 at scale 1, no automatic approval.
- New synthetic tests for corner-horizontal, top-offset-horizontal, true tangent, competition, 4-wire group and 11/12/13 px boundary.
- A horizontal line passing within 12 px of the top edge may be accepted **only if** its endpoint is also within tolerance of the vertical face and no competing leaf wins. This is a provisional corridor rule, not proof of a physical connection.
- No arbitrary endpoint coordinate rewriting and no bus-based bypass of geometric checks.

## Mandatory local gate

1. Run **all** existing and new synthetic tests; 0 failures required.
2. Run the private real 4-wire case; require 4/4 wire IDs retained, correct bus group, one candidate logical edge, no false matches.
3. Run true tangent and competing-leaf negative cases; no false candidate.
4. Verify direction disagreement, unknown arrow and missing trace never auto-promote.
5. Reconfirm source_verified=false, needs_review, no LLM coordinates, unchanged DB/approved graph/image hash and no outbound transfer.
6. Without independent human GT, report pass_90 as NOT_EVALUABLE.

**This GitHub branch is a proposed fix, NOT a successful release.** Internal SFT results and code are not requested or uploaded.
