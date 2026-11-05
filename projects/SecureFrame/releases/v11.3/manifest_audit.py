"""Generic, offline manifest metadata audit; no embedded customer content."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json

def audit(manifest):
    records = manifest.get("records", [])
    keys = [(r.get("topic"), r.get("source", {}).get("name"),
             r.get("source", {}).get("page")) for r in records]
    counts = Counter(keys)
    return {
        "record_count": len(records),
        "duplicate_source_reference_count": sum(n - 1 for n in counts.values() if n > 1),
        "unverified_records": sum(r.get("review_state") != "source_verified" for r in records),
        "status": "metadata_only_not_source_verified",
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit(json.loads(Path(args.manifest).read_text(encoding="utf-8")))
    target = Path(args.output)
    if target.exists():
        raise SystemExit("Refusing to overwrite existing audit")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
