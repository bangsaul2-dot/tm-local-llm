# AES input fixture — local Git commit instructions

The source image is a user-supplied AES diagram, **not synthetic**. Do not replace it with a hand-authored reconstruction. The GitHub connector available to the assistant does not accept a container binary-file reference, so the binary has **not** been committed by this change.

Once the AES PNG is transferred to Ubuntu, add it to the experiment branch using:

```bash
# Run from the repository root, on secureframe/aes-qwen-reconstruction-experiment.
mkdir -p projects/SecureFrame/experiments/fixtures
cp /path/to/aes_diagram_crop.png projects/SecureFrame/experiments/fixtures/aes_diagram_crop.png
sha256sum projects/SecureFrame/experiments/fixtures/aes_diagram_crop.png
# Expected SHA-256 for exact original cropped PNG:
# ed2b6cfae6725388331f7afc16683f99103b7d7facc2e0f505cc4b66c25d3c30
git add projects/SecureFrame/experiments/fixtures/aes_diagram_crop.png
git commit -m "Add user-provided AES image as reconstruction input fixture"
git push origin HEAD:secureframe/aes-qwen-reconstruction-experiment
```

**Before pushing:** check that this image is approved for this repository's visibility and information-security policy. Never push other internal diagrams. The screenshot includes an external technical AES block diagram, but its redistribution rights have not been verified.

After the binary commit exists, run from `projects/SecureFrame/experiments`:

```bash
python3 -m unittest test_aes_qwen_reconstruct.py -v
python3 aes_qwen_reconstruct.py \
 --image fixtures/aes_diagram_crop.png \
 --model qwen3vl-30b-local \
 --host http://127.0.0.1:11434 \
 --temperature 0 --seed 42 \
 --out-dir "$HOME/secureframe-aes-test/output-001"
```

Outputs stay local. The generated SVG is a Qwen-layout approximation, **not** physically grounded SecureFrame output. Review the actual SVG and compare blocks and arrows before promotion. Never claim a release based only on schema/test pass.
