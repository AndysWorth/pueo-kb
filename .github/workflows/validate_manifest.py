#!/usr/bin/env python3
"""Validate that MANIFEST.json is consistent with the repository contents."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

VALID_STATES = {"seed", "candidate", "validated", "flagged"}
REQUIRED_FIELDS = {"id", "type", "path", "sha256", "state", "community_stats"}


def validate_community_stats(entry: dict, errors: list) -> None:
    cs = entry.get("community_stats")
    if not isinstance(cs, dict):
        errors.append(f"{entry.get('id')}: community_stats must be an object")
        return
    for field in ("successes", "failures", "instances"):
        val = cs.get(field)
        if not isinstance(val, int) or val < 0:
            errors.append(
                f"{entry.get('id')}: community_stats.{field} must be a non-negative int"
            )


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
        entry_id = entry.get("id", "<unknown>")

        # Required field presence
        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            errors.append(f"{entry_id}: missing required fields: {sorted(missing)}")

        # File existence and SHA-256
        path = ROOT / entry.get("path", "")
        if not path.exists():
            errors.append(f"{entry_id}: missing file: {entry.get('path')}")
            continue
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != entry.get("sha256", ""):
            errors.append(
                f"{entry_id}: SHA-256 mismatch for {entry.get('path')}: "
                f"manifest={entry.get('sha256')} actual={actual_sha}"
            )

        # State enum
        state = entry.get("state")
        if state not in VALID_STATES:
            errors.append(f"{entry_id}: state must be one of {sorted(VALID_STATES)}, got {state!r}")

        # Signature: string or null
        sig = entry.get("signature", "<absent>")
        if sig != "<absent>" and sig is not None and not isinstance(sig, str):
            errors.append(f"{entry_id}: signature must be a string or null")

        # Community stats
        validate_community_stats(entry, errors)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(entries)} manifest entries validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
