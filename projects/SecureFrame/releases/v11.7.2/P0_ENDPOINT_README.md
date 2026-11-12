# P0 V11.6 Endpoint Geometry Proposal — NOT RELEASED

This isolated module proposes corrections only when the outward ray from an existing, independently traced wire endpoint intersects an actual leaf rectangle face within `max_extension` (default 12 px). It preserves `_source_points`, outputs `proposed_points` separately and records intersection evidence. No original wire or DB is modified. All outputs remain `needs_review`, `source_verified=false`, `auto_approval=false`.

**Important diagnostic limitation:** an endpoint 12 px above the target rectangle and 18 px from its x-facing side is **not** correctable by this module unless the measured segment direction intersects a rectangle face within the allowed extension. This implementation intentionally abstains instead of forcing physical 4/4. In particular, a horizontal segment 12 px above a rectangle cannot be moved vertically without independent source evidence.

## Run locally

```bash
cd projects/SecureFrame/releases/v11.7.2
python3 -m unittest discover -p 'test_*.py' -v
```

Existing 27 tests plus new synthetic tests must all pass. Actual private 4-wire 4/4 remains a **separate blocked gate** until independently measured, source-grounded geometry supports the fourth connection. A failure to recover it is not permission to widen tolerance, silently alter original coordinates, or use bus IDs / LLM coordinates as geometric evidence.

The caller should produce a private `refined_geometry_proposal.json` by applying **only reviewed** proposals to a copy of the upstream geometry; do not overwrite original `refined_geometry.json` or operating SQLite. This module intentionally does not write files or access network services.

This branch is a development candidate, not a promoted V11.7.2 release. No actual SFT test or GT score has been performed by ChatGPT. `pass_90=NOT_EVALUABLE` without human GT.
