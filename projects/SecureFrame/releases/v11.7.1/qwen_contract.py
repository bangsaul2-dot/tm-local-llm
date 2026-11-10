"""Offline Qwen response contract; transport injected by local Ubuntu runtime.

No HTTP/network implementation in this module. No customer image data bundled.
"""
import json
from hybrid_bus import parse_semantic

SYSTEM_PROMPT = """Analyze the supplied diagram locally. Return JSON only.
Return exactly two top-level keys: nodes, edges.
Each node must have exactly name (string), kind (leaf|container), parent (name|null).
Each edge must have exactly from, to, direction (forward|reverse|unknown).
Use only visible labels. Do not invent missing blocks or connections.
NEVER return bounding boxes, pixel coordinates, x/y, positions or confidence.
Direction unknown if uncertain. Container nodes must not be edge endpoints.
No markdown, explanations, or extra fields."""

def request_semantic(local_infer, image_reference, max_retries=2):
    """Caller supplies a strictly local inference function; bounded retry only.

    The image_reference is opaque and must never be logged or transmitted here.
    """
    if not callable(local_infer):
        raise TypeError("local_infer must be callable")
    if not isinstance(max_retries, int) or not 0 <= max_retries <= 3:
        raise ValueError("max_retries must be 0..3")
    feedback = ""
    for attempt in range(max_retries + 1):
        response = local_infer(SYSTEM_PROMPT + feedback, image_reference)
        if not isinstance(response, str):
            raise TypeError("inference must return a JSON string")
        try:
            return {"status": "valid", "semantic": parse_semantic(response),
                    "attempts": attempt + 1}
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            feedback = "\nPrevious response was invalid. Return ONLY the exact schema. Error: " + type(exc).__name__
    return {"status": "needs_review", "semantic": None, "attempts": max_retries + 1}
