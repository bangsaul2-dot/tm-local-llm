# AES local vision-model benchmark (experimental)

This is an **offline comparison harness**, not an accuracy-certified release.
It uses the same prompt and AES image for each model, validates through the
existing experimental endpoint-v2 adjudicator, and writes only aggregate CSV.
The existing SecureFrame approved modules, DB and Graph are untouched.

## Environment (Ubuntu RTX 5090 32GB)

- Ollama already running on 127.0.0.1:11434
- Python 3 + locally installed `ollama` Python package
- Existing Qwen model `qwen3vl-30b-local`
- Additional models are **optional**. Verify image input and Ollama support
  *before* installing: `ollama list` and `ollama show <model>`.
- Gemma 3 27B (e.g. Ollama tag `gemma3:27b`) is a candidate; ensure memory
  availability and quantization. InternVL3-14B may require a supported
  compatible model build/runtime, and must not be assumed to be available
  under a specific Ollama tag. Do not `ollama pull` in restricted networks
  without an approved internal source.
- Run one model at a time; this script runs sequentially, but Ollama may keep
  prior models loaded. Use `ollama stop <model>` between models if VRAM
  pressure occurs. Avoid simultaneous Docling GPU jobs.

## Quick start

```bash
cd projects/SecureFrame/experiments
python3 -m unittest test_aes_qwen_reconstruct.py test_aes_endpoint_v2.py test_aes_vlm_benchmark.py -v
ollama list
python3 aes_vlm_benchmark.py \
 --image /approved/local/aes_diagram_crop.png \
 --models qwen3vl-30b-local gemma3:27b \
 --report "$HOME/aes-vlm-benchmark-001.csv"
```

Only list models already installed and verified to accept images. If InternVL3
is not available in a compatible Ollama format, benchmark it separately using
its supported local runtime and adapt the transport, rather than claiming
the Ollama comparison succeeded.

## Interpretation

Columns: model, status, blocks, containers, annotations, ports, edges,
rendered, abstained, non_endpoint, invalid_reference, latency_sec,
tokens_per_sec, image_sha256_prefix, error_type.

- `schema_pass` means syntactically and structurally processed, **not** correct.
- `rendered` means endpoints are allowed by the experimental schema,
  **not** physically verified.
- `abstained` counts unsafe endpoints.
- The model prompt is shared across all models. It uses the V1 schema
  (leaf/container/annotation), so explicit port prediction is not yet tested.
- The renderer still draws straight center-to-center lines. The benchmark
  cannot establish physical-wire fidelity or direction accuracy without
  an independent ground truth.
- Compare against a local manually reviewed AES reference before ranking
  actual block/edge precision or recall.
- For reproducibility, record exact model digests (`ollama list`), inference
  runtime, quantization and input hash locally. Seed=42 and temperature=0
  do not guarantee bitwise repeatability.

## Safety

Only HTTP loopback Ollama. No image or labels sent to GitHub, stdout or CSV.
No auto approval. Existing four approval modules are unchanged.
No report overwrite. Local internal model and data access remain restricted.
