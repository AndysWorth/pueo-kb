#!/usr/bin/env python3
"""Validate that MANIFEST.json is consistent with the repository contents."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def main() -> int:
    manifest_path = ROOT / "MANIFEST.json"
    if not manifest_path.exists():
        print("ERROR: MANIFEST.json not found", file=sys.stderr)
        return 1

    try:
        entries = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: MANIFEST.json is not valid JSON: {e}", file=sys.stderr)
        return 1

    if not isinstance(entries, list):
        print("ERROR: MANIFEST.json must be a JSON array", file=sys.stderr)
        return 1

    errors = []
    for entry in entries:
        path = ROOT / entry.get("path", "")
        if not path.exists():
            errors.append(f"Missing file: {entry.get('path')}")
            continue
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != entry.get("sha256", ""):
            errors.append(
                f"SHA-256 mismatch for {entry.get('path')}: "
                f"manifest={entry.get('sha256')} actual={actual_sha}"
            )

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(entries)} manifest entries validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
