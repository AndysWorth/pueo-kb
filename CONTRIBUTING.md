# Contributing to pueo-kb

This repository is the federated knowledge base for [Pueo](https://github.com/AndysWorth/pueo),
a local Home Assistant self-healing agent.

## What belongs here

- **Runbooks** — investigation approaches for recurring HA failure modes (YAML-fronmattered `.md` files)
- **Evidence files** — per-instance usage statistics that feed automated validation (`evidence/<instance_id>.json`)
- **Gap reports** — documented failure cases where no runbook existed (`.yaml` files in `gaps/`)

## How runbook contributions work

Pueo submits runbooks automatically from the dashboard (Runbook Review tab → Contribute).
This opens a pull request with:
1. A runbook file `runbooks/<kb_id>.md` with the YAML frontmatter shown below.
2. An evidence file `evidence/<instance_id>.json` with this instance's usage statistics.

**MANIFEST.json is never hand-edited.** The `build-manifest.yml` CI workflow rebuilds it
automatically on every push to `main`. Your PR must not include MANIFEST.json changes.

## Runbook frontmatter format

Every runbook must have a YAML frontmatter block:

```yaml
---
id: rb_abc123def456        # "rb_" + sha256(signature)[:12]; seeds use a descriptive slug
type: runbook
state: candidate           # seed | candidate | validated | flagged
signature: "error text that identifies this failure class"   # null for seeds
tags: [integration, config]
integrations: [zha, mqtt]  # or ["all"]
ha_version_min: "2024.1"   # optional
contributed_at: "2026-10-08"
---
```

## Evidence file format

Each Pueo instance contributes a single `evidence/<instance_id>.json` per PR.

```json
{
  "instance_id": "<UUID>",
  "pueo_version": "1.2.3",
  "updated_at": "2026-10-08T12:00:00Z",
  "runbooks": {
    "rb_abc123def456": {
      "sha256": "<sha256 of the runbook file>",
      "signature": "error text that identifies this failure class",
      "successes": 3,
      "failures": 0,
      "episodes": ["ep_id_1", "ep_id_2", "ep_id_3"]
    }
  }
}
```

**Rules:**
- A PR may modify at most **one** `evidence/<instance_id>.json` file.
- The evidence file must pass the schema validation in `validate_pr.yml`.

## Promotion thresholds (encoded in `scripts/build_manifest.py`)

| Condition | Result |
|-----------|--------|
| `state = seed` | Always stays `seed` — seeds are never demoted |
| `failures > 0` | → `flagged` (maintainer review required) |
| `successes ≥ 3` AND `distinct instances with a success ≥ 2` AND `failures = 0` | → `validated` |
| Otherwise | Stays `candidate` |

Flagged runbooks are excluded from Pueo's knowledge retrieval until a maintainer reviews them.

## File layout

```
pueo-kb/
├── MANIFEST.json           # auto-generated — do not hand-edit
├── runbooks/               # investigation runbooks (.md with YAML frontmatter)
│   ├── seed_*.md           # curated seeds shipped with Pueo
│   └── rb_*.md             # community contributions
├── evidence/               # per-instance usage statistics (.json)
├── gaps/                   # gap reports (.yaml) — failure cases without a fix
└── scripts/
│   ├── build_manifest.py   # rebuilds MANIFEST.json from runbooks + evidence
│   ├── schemas.py          # dataclasses for manifest entries and evidence files
│   ├── test_build_manifest.py  # pytest tests
│   └── requirements.txt
└── .github/workflows/
    ├── validate.yml        # CI: checks MANIFEST.json on push/PR
    ├── validate_manifest.py
    ├── validate_pr.yml     # CI: PR rules (evidence count, frontmatter, no MANIFEST edits)
    ├── validate_pr.py
    └── build-manifest.yml  # CI: rebuilds MANIFEST.json on push to main
```

## Running the tests locally

```bash
pip install -r scripts/requirements.txt
pytest scripts/test_build_manifest.py -v
```

To rebuild MANIFEST.json manually (e.g. to preview changes):

```bash
python3 scripts/build_manifest.py
```
