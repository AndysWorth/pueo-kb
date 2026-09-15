# Contributing to pueo-kb

This repository is the federated knowledge base for [Pueo](https://github.com/AndysWorth/pueo),
a local Home Assistant self-healing agent.

## What belongs here

- **Runbooks** — investigation approaches for recurring HA failure modes (YAML-fronmattered `.md` files)
- **Gap reports** — documented failure cases where no runbook existed (`.yaml` files in `gaps/`)

## Submitting a runbook

Pueo can submit runbooks automatically from the dashboard (Runbook Review tab → Contribute).
This opens a pull request with the runbook file and a `MANIFEST.json` update.

To submit manually:

1. Add your runbook as `runbooks/<slug>.md` with YAML frontmatter:
   ```yaml
   ---
   id: your_slug
   type: runbook
   tags: [integration, config]
   integrations: [zha, mqtt]   # or ["all"]
   ha_version_min: "2024.1"    # optional
   ---
   ```
2. Add an entry to `MANIFEST.json` with the file's SHA-256 and metadata.
3. Open a pull request — the validation workflow checks the manifest is consistent.

## File layout

```
pueo-kb/
├── MANIFEST.json           # index of all runbooks and gaps
├── runbooks/               # investigation runbooks (.md)
│   ├── seed_*.md           # curated seeds shipped with Pueo
│   └── <contributed>.md    # community contributions
├── gaps/                   # gap reports (.yaml) — failure cases without a fix
└── .github/workflows/
    └── validate.yml        # CI: checks MANIFEST.json is consistent
```

## Validation

Every PR runs `validate.yml`, which verifies:
- `MANIFEST.json` is valid JSON and all `path` entries exist in the repo
- SHA-256 checksums in the manifest match the actual file contents
