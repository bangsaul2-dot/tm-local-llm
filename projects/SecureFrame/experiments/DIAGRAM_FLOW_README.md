# SecureFrame diagram flow analyzer — DEVELOPMENT / NOT VERIFIED

**Goal:** Explain what a source diagram actually shows, not redraw its boxes.
Input: original AES crop or internal SFT figure image. Output: local
`flow_analysis.md` (block inventory, proposed data/control/key/authentication
flows, unverified links) and sanitized `flow_summary.json`.

The tool is experimental and does **not** claim that model-observed arrows
are physically verified. It never sets source_verified true, and never
generates coordinates or writes an approval graph/DB. The raw labels are
included only in the local Markdown report; do NOT commit or upload it.

## Quick test — AES first

```bash
cd projects/SecureFrame/experiments
python3 -m unittest test_diagram_flow_analyzer.py -v
ollama list
python3 diagram_flow_analyzer.py \
 --image /approved/local/aes_diagram_crop.png \
 --model gemma3-27b-local \
 --figure-id aes_diagram_crop \
 --out-dir "$HOME/secureframe-flow/aes-001"
```

The model name must match `ollama list`. Use the same AES image previously
used for the local reconstruction experiment. If no local image exists, stop;
do not substitute a hand-authored graph. The Ollama Python client is required
and uses `content` as a string and `images` as a separate base64 list.

Inspect `flow_analysis.md` locally against the original image. Every arrow
is a **proposal**, even if marked `visible_arrow` by the model. Do not
count it as true without human/physical corroboration.

## Repeat on SFT

```bash
python3 diagram_flow_analyzer.py \
 --image /private/local/sft_figure_001.png \
 --model gemma3-27b-local \
 --figure-id sft_figure_001 \
 --out-dir "$HOME/secureframe-flow/sft-001"
```

Use one local figure image per run. Choose a new output directory per
experiment. The script refuses overwriting output files. Input files are
read-only. Run SFT only after AES baseline inspection and security checks.

## What to verify

- Block inventory completeness: especially Video Expand, Hash, AES GMAC,
  Sign Line Gen in relevant SFT figures
- Directional data/control/key/authentication flows, source and target
- Missing and hallucinated edges, arrowheads and signal names
- Container vs leaf/port endpoints (container/annotation prohibited)
- Count of observed-arrow candidates and abstentions
- Compare Gemma and Qwen with **same input and prompt** when useful
- No false `source_verified` or auto-approval
- Baseline vs manually reviewed output; report time spent reviewing

**Important limitations:** current model-only image interpretation does not
trace pixels with OpenCV or validate each arrow against a source crop. It is
an initial flow-description experiment, not a certified SFT analysis system.
A flow candidate is *not* a physically grounded connection. No automatic
promotion without reviewed AES and SFT outcomes. No actual performance
results are claimed in this repository.
