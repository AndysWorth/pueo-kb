# pueo-kb

[![Validate](https://github.com/AndysWorth/pueo-kb/actions/workflows/validate.yml/badge.svg)](https://github.com/AndysWorth/pueo-kb/actions/workflows/validate.yml)
[![Build manifest](https://github.com/AndysWorth/pueo-kb/actions/workflows/build-manifest.yml/badge.svg)](https://github.com/AndysWorth/pueo-kb/actions/workflows/build-manifest.yml)
[![License: LGPL-3.0](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](LICENSE)

Federated runbook library for [Pueo](https://github.com/AndysWorth/pueo), a local
privacy-first agent that monitors and self-heals Home Assistant instances.

## What's in this repo

| Path | Contents |
|---|---|
| `runbooks/` | Investigation runbooks — YAML-fronted `.md` files describing how to diagnose and fix recurring HA failure modes |
| `evidence/` | Per-instance usage statistics (`.json`) — used to promote candidates to validated |
| `gaps/` | Gap reports — `.yaml` files recording failure cases where no runbook existed |
| `MANIFEST.json` | Auto-generated index — do not hand-edit; rebuilt by CI on every push to `main` |
| `scripts/` | `build_manifest.py`, `schemas.py`, and tests |

## Runbook lifecycle

```
seed (curated)
    ↕ never demoted

candidate (community-contributed)
    → validated   ≥ 3 successes AND ≥ 2 distinct instances AND 0 failures
    → flagged     any failure → maintainer review required
```

## How Pueo uses it

At every RAG refresh (`--mode rag-refresh`), Pueo pulls the latest runbooks from this
repo via `utils/knowledge/kb_ingester.py`, embeds them into its local ChromaDB knowledge
store, and makes them available to every agent session via the `query_knowledge` tool.

Authority tiers:
- `seed` / `validated` runbooks → authority 0.70
- `candidate` runbooks → authority 0.45 (labelled `[COMMUNITY CANDIDATE]`)
- `flagged` runbooks → skipped entirely

When an agent completes a successful repair using a novel approach, the user can review
it in the dashboard (Runbook Review tab) and contribute it back here via
`utils/knowledge/kb_contributor.py`, which opens a pull request with the runbook file
and an evidence file automatically.

The repo ships with 10 seed runbooks covering common HA failure modes:
config errors, disk space, integration errors, log analysis, Lovelace config,
notification analysis, Pueo log patterns, repair issues, security notifications,
and update analysis.

## How to contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for the runbook format, frontmatter schema,
evidence file format, and submission process.

## License

GNU Lesser General Public License v3.0 — see [LICENSE](LICENSE).
