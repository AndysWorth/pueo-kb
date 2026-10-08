#!/usr/bin/env python3
"""PR validation rules for pueo-kb contributions.

Checks:
1. At most one evidence/*.json file is modified per PR.
2. Any evidence file added or modified has a valid schema.
3. Any new runbook added to runbooks/ has valid frontmatter.

MANIFEST.json must NOT be hand-edited — build-manifest.yml handles it automatically.
PRs that touch MANIFEST.json are rejected unless scripts/build_manifest.py is also
being introduced (bootstrap case).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

# Add scripts/ to path so we can import schemas
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import yaml
    from schemas import EvidenceFile, RunbookFrontmatter
except ImportError as exc:
    print(f"ERROR: required dependency missing: {exc}", file=sys.stderr)
    print("Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def get_changed_files(base_ref: str) -> list[str]:
    """Return list of files changed between base_ref and HEAD."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        print(
            f"WARN: could not determine changed files: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return []
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def validate_evidence_schema(path: Path) -> list[str]:
    """Return a list of schema errors for an evidence file."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]
    ev = EvidenceFile.from_dict(raw)
    return ev.validate()


def validate_runbook_frontmatter(path: Path) -> list[str]:
    """Return a list of validation errors for a runbook's frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return ["missing YAML frontmatter block"]
    try:
        end = text.index("---\n", 4)
    except ValueError:
        return ["frontmatter block is not closed with '---'"]
    fm_raw = yaml.safe_load(text[4:end]) or {}
    if not isinstance(fm_raw, dict):
        return ["frontmatter must be a YAML mapping"]
    missing = {"id", "type", "state"} - set(fm_raw.keys())
    if missing:
        return [f"missing required frontmatter fields: {sorted(missing)}"]
    fm = RunbookFrontmatter(
        id=fm_raw["id"],
        type=fm_raw["type"],
        state=fm_raw["state"],
        signature=fm_raw.get("signature"),
        tags=fm_raw.get("tags") or [],
        integrations=fm_raw.get("integrations") or ["all"],
    )
    return fm.validate()


def is_bootstrap_pr(changed: list[str]) -> bool:
    """True if this is the initial scaffold PR that introduces build_manifest.py."""
    return "scripts/build_manifest.py" in changed


def main() -> int:
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    changed = get_changed_files(base_ref)

    errors = []
    warnings = []

    # --- MANIFEST.json hand-edit check ---
    if "MANIFEST.json" in changed and not is_bootstrap_pr(changed):
        errors.append(
            "MANIFEST.json must not be hand-edited. "
            "It is rebuilt automatically by build-manifest.yml on every push to main."
        )

    # --- Evidence file checks ---
    evidence_files = [f for f in changed if re.match(r"evidence/[^/]+\.json$", f)]

    if len(evidence_files) > 1:
        errors.append(
            f"A PR may modify at most one evidence/*.json file, "
            f"but this PR modifies {len(evidence_files)}: {evidence_files}"
        )

    for ev_rel in evidence_files:
        ev_path = ROOT / ev_rel
        if not ev_path.exists():
            continue  # deleted; no validation needed
        schema_errs = validate_evidence_schema(ev_path)
        if schema_errs:
            for err in schema_errs:
                errors.append(f"{ev_rel}: {err}")

    # --- New runbook frontmatter checks ---
    new_runbooks = [
        f for f in changed
        if re.match(r"runbooks/[^/]+\.md$", f)
        and not f.startswith("runbooks/seed_")  # seeds are managed by maintainers
    ]
    for rb_rel in new_runbooks:
        rb_path = ROOT / rb_rel
        if not rb_path.exists():
            continue  # deleted; no validation needed
        fm_errs = validate_runbook_frontmatter(rb_path)
        if fm_errs:
            for err in fm_errs:
                errors.append(f"{rb_rel}: {err}")

    for w in warnings:
        print(f"WARN: {w}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    files_checked = len(evidence_files) + len(new_runbooks)
    print(f"OK: PR checks passed ({files_checked} files validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
