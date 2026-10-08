#!/usr/bin/env python3
"""Scan runbooks/*.md and evidence/*.json -> write MANIFEST.json.

Run:
    python3 scripts/build_manifest.py [--root <repo-root>]

In CI (build-manifest.yml) this runs on every push to main and commits the result.
The output replaces MANIFEST.json wholesale — PRs must NOT hand-edit it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml is required. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from schemas import (
    CommunityStats,
    EvidenceFile,
    ManifestEntry,
    RunbookFrontmatter,
    VALID_STATES,
)

# Promotion thresholds
MIN_SUCCESSES = 3
MIN_INSTANCES = 2


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frontmatter(path: Path) -> Optional[dict]:
    """Return YAML frontmatter dict or None if no frontmatter block."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    try:
        end = text.index("---\n", 4)
    except ValueError:
        return None
    fm_text = text[4:end]
    parsed = yaml.safe_load(fm_text)
    return parsed if isinstance(parsed, dict) else None


def load_evidence(evidence_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Aggregate evidence across all instance files.

    Returns {kb_id: {"successes": int, "failures": int, "instances": set}}.
    """
    stats: Dict[str, Any] = defaultdict(
        lambda: {"successes": 0, "failures": 0, "instances": set()}
    )
    if not evidence_dir.exists():
        return {}
    for f in sorted(evidence_dir.glob("*.json")):
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
            ev = EvidenceFile.from_dict(raw)
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"WARN: skipping malformed evidence file {f.name}: {exc}", file=sys.stderr)
            continue
        for kb_id, rb in ev.runbooks.items():
            s = stats[kb_id]
            s["successes"] += rb.successes
            s["failures"] += rb.failures
            if rb.successes > 0:
                s["instances"].add(ev.instance_id)
    return {
        k: {
            "successes": v["successes"],
            "failures": v["failures"],
            "instances": len(v["instances"]),
        }
        for k, v in stats.items()
    }


def compute_state(fm_state: str, cs: Dict[str, int]) -> str:
    """Derive manifest state from frontmatter state and community evidence.

    Seeds are immutable. Candidates can be promoted to validated or flagged.
    """
    if fm_state == "seed":
        return "seed"
    if cs["failures"] > 0:
        return "flagged"
    if cs["successes"] >= MIN_SUCCESSES and cs["instances"] >= MIN_INSTANCES:
        return "validated"
    return fm_state


def build_manifest(root: Path) -> Tuple[List[dict], List[str]]:
    """Scan runbooks/ and evidence/ under root and return (entries, warnings)."""
    runbooks_dir = root / "runbooks"
    evidence_dir = root / "evidence"

    if not runbooks_dir.exists():
        raise FileNotFoundError(f"runbooks/ not found under {root}")

    evidence = load_evidence(evidence_dir)
    entries = []
    warnings = []

    for path in sorted(runbooks_dir.glob("*.md")):
        fm_raw = load_frontmatter(path)
        if fm_raw is None:
            warnings.append(f"WARN: {path.name} has no frontmatter — skipping")
            continue

        # Validate required fields
        missing = {"id", "type", "state"} - set(fm_raw.keys())
        if missing:
            warnings.append(
                f"WARN: {path.name} frontmatter missing {missing} — skipping"
            )
            continue

        fm = RunbookFrontmatter(
            id=fm_raw["id"],
            type=fm_raw["type"],
            state=fm_raw["state"],
            signature=fm_raw.get("signature"),
            tags=fm_raw.get("tags") or [],
            integrations=fm_raw.get("integrations") or ["all"],
            ha_version_min=fm_raw.get("ha_version_min"),
            ha_version_max=fm_raw.get("ha_version_max"),
            contributed_at=fm_raw.get("contributed_at"),
        )
        errs = fm.validate()
        if errs:
            warnings.append(
                f"WARN: {path.name} frontmatter invalid ({'; '.join(errs)}) — skipping"
            )
            continue

        # Look up community stats by id (seeds use their id; contributed use kb_id)
        kb_id = fm_raw.get("kb_id") or fm.id
        raw_cs = evidence.get(kb_id, {"successes": 0, "failures": 0, "instances": 0})
        cs = CommunityStats(**raw_cs)

        derived_state = compute_state(fm.state, raw_cs)

        entry = ManifestEntry(
            id=fm.id,
            type=fm.type,
            path=f"runbooks/{path.name}",
            sha256=compute_sha256(path),
            state=derived_state,
            signature=fm.signature,
            tags=fm.tags,
            integrations=fm.integrations,
            ha_version_min=fm.ha_version_min,
            ha_version_max=fm.ha_version_max,
            contributed_at=fm.contributed_at,
            community_stats=cs,
        )
        entries.append(entry.to_dict())

    return entries, warnings


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Repo root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the manifest without writing MANIFEST.json",
    )
    args = parser.parse_args(argv)

    try:
        entries, warnings = build_manifest(args.root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for w in warnings:
        print(w, file=sys.stderr)

    manifest_json = json.dumps(entries, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(manifest_json)
        return 0

    manifest_path = args.root / "MANIFEST.json"
    manifest_path.write_text(manifest_json + "\n", encoding="utf-8")
    print(f"OK: wrote {len(entries)} entries to {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
