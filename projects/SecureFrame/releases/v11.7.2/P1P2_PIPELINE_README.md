# SecureFrame P1/P2 Local Integration — DEVELOPMENT ONLY

This branch adds a generic, local-only glue layer. The approved V11.7.2 release remains unchanged. The actual V11.6 adapter and customer diagrams are not published.

## Required local dependencies

`python3 -m pip install pytesseract Pillow ollama` (only from an approved **internal** package mirror; no direct public internet). The Tesseract binary must be installed separately on Ubuntu. Existing v11.7.1 `hybrid_bus.py`, `qwen_contract.py` and v11.7.2 `hybrid_fusion.py` are reused.

Add the internal module exposing `adapter_v116.to_geometry(v116, image_path, ...)` to `PYTHONPATH` **locally**. Its return contract is `{"boxes":[{"bbox":[x0,y0,x1,y1]}],"ocr":[...],"wires":[...]}`; the P1 stage replaces OCR with local Tesseract output in original image coordinates. Wire fields: `id, points, trace_verified, bus_group_id, arrow_direction`, optionally `arrowhead_tip/base`.

## Single figure

```bash
python3 pipeline_p1p2.py --v116 /private/local-v116.json \
  --image /private/local-figure.png \
  --model qwen3vl-30b-local --ocr-upscale 1 --ocr-psm 11 \
  --report /private/new-sanitized-report.json
```

Default OCR scale is 1.0 and PSM is unset (Tesseract default); tuning scale/PSM is not guaranteed to improve accuracy. The example PSM 11 is an option, not the default. `--report` refuses to overwrite an existing file. If omitted, sanitized counts print to stdout.

## Multiple figures

Supply a local JSON **array** of objects `{"v116":"/private/a.json","image":"/private/a.png"}`. Then:

```bash
python3 pipeline_p1p2.py --figures /private/figures.json --model qwen3vl-30b-local \
  --report /private/new-multi-report.json
```

The output contains only indexed per-figure counts/status and error **types**. Raw coordinates, OCR tokens, semantic names, image bytes, model responses, private file paths and GT are never written by this module.

## Orchestration

1. Load local figure image and private V11.6 input (read-only).
2. Call local `adapter_v116.to_geometry`.
3. Extract Tesseract OCR tokens in original pixels (optional resize is reversed).
4. Call `request_semantic(local_infer, image, max_retries=2)`. The injected Ollama SDK transport uses `messages=[{"role":"user","content":prompt,"images":[base64_image]}]`. It only permits HTTP loopback.
5. Validate strict coordinate-free semantics; do **not** inject OCR labels into prompts.
6. Ground nodes using V11.7.1 `ground_nodes`.
7. Fuse candidate edges with V11.7.2 `fuse_grounded`; check safety invariants.
8. Emit sanitized status and counts; `pass_90=NOT_EVALUABLE` until human GT.

**Limitations:** no production deployment or real SFT validation claimed. Container endpoints remain non-candidates. The existing V11.7.2 fusion may not attach excluded physical wires to the candidate edge; do not interpret logical bus grounding as physical 4/4. Input file errors are reported only by exception class, not private details. All result edges remain `needs_review` and `source_verified=False`; this pipeline cannot grant approval.

## Synthetic regression

```bash
cd projects/SecureFrame/releases/v11.7.2
python3 -m unittest discover -p 'test_*.py' -v
```

No external network access is needed for the injected tests. Local Ollama and Tesseract are required for the real run.
