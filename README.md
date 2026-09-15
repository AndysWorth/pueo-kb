# pueo-kb

[![Validate](https://github.com/AndysWorth/pueo-kb/actions/workflows/validate.yml/badge.svg)](https://github.com/AndysWorth/pueo-kb/actions/workflows/validate.yml)
[![License: LGPL-3.0](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](LICENSE)

Federated runbook library for [Pueo](https://github.com/AndysWorth/pueo), a local
privacy-first agent that monitors and self-heals Home Assistant instances.

## What's in this repo

| Path | Contents |
|---|---|
| `runbooks/` | Investigation runbooks — YAML-fronted `.md` files describing how to diagnose and fix recurring HA failure modes |
| `gaps/` | Gap reports — `.yaml` files recording failure cases where no runbook existed |
| `MANIFEST.json` | Index of all runbooks and gaps with slugs, titles, and checksums |

## How Pueo uses it

At every RAG refresh (`--mode rag-refresh`), Pueo pulls the latest runbooks from this
repo via `utils/knowledge/kb_ingester.py`, embeds them into its local ChromaDB knowledge
store, and makes them available to every agent session via the `query_knowledge` tool.

When an agent completes a successful repair using a novel approach, the user can review
it in the dashboard (Runbook Review tab) and contribute it back here via
`utils/knowledge/kb_contributor.py`, which opens a pull request automatically.

The repo ships with 10 seed runbooks covering common HA failure modes:
config errors, disk space, integration errors, log analysis, Lovelace config,
notification analysis, Pueo log patterns, repair issues, security notifications,
and update analysis.

## How to contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for the runbook format, frontmatter schema,
and submission process.

## License

GNU Lesser General Public License v3.0 — see [LICENSE](LICENSE).
