# SecureFrame V11.7 — Hybrid grounding prototype

This is a sanitized, **partial standalone GitHub implementation**, not a byte-for-byte upload of the offline prototype archive or a complete replacement for V11.6.2.

## Design

Semantic input provides only node names, container hierarchy and proposed directed edges. Geometry input supplies OpenCV boxes, OCR bounding boxes, and independently traced end-to-end wires. LLM coordinates are rejected. Only leaf nodes may be edge endpoints. Wire IDs remain separate, including parallel buses.

All output edges remain candidate / needs_review and source_verified=false. Conflicting or missing arrow evidence is ambiguous. The module performs no network calls.

## Run synthetic tests

```bash
cd projects/SecureFrame/releases/v11.7
python3 -m unittest discover -p 'test_*.py' -v
```

## Missing integration work

This repository subset does not call Ollama, retry malformed model output, extract line segments, trace disconnected wire fragments, detect arrowheads, or perform OCR. Supply independently verified end-to-end wire observations from the offline local pipeline; never fabricate trace_verified=true. No private image, OCR result, database, annotated ground truth, or project-derived JSON has been committed.

Real-image precision and recall are **not measured**. pass_90 is a gate for independently supplied human GT only. Existing runtime/GT adapter compatibility is not yet demonstrated.
