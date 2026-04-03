---
name: mine
description: Agent-first mining skill for signed platform work, data crawling, structured extraction, LLM enrichment, schema(1) field alignment, and submission export through awp-wallet.
bootstrap: ./scripts/bootstrap.sh
windows_bootstrap: ./scripts/bootstrap.cmd
smoke_test: ./scripts/smoke_test.py
requires:
  bins:
    - npm
    - git
  anyBins:
    - python
    - python3
    - py
---

# Mine

## Quick Start

1. **Install** — run the bootstrap script in the `mine/` directory:
   - Windows: `.\scripts\bootstrap.cmd`
   - Unix: `./scripts/bootstrap.sh`
2. **Check readiness**: `python scripts/run_tool.py agent-status`
3. **Start mining**: `python scripts/run_tool.py agent-start`

That is the entire setup. Do NOT read source code or clone external repos.

## Actions

| Action | Command |
| ------ | ------- |
| Initialize | `python scripts/run_tool.py init` |
| Check readiness | `python scripts/run_tool.py agent-status` |
| Start mining | `python scripts/run_tool.py agent-start` |
| Check status | `python scripts/run_tool.py agent-control status` |
| Pause | `python scripts/run_tool.py agent-control pause` |
| Resume | `python scripts/run_tool.py agent-control resume` |
| Stop | `python scripts/run_tool.py agent-control stop` |
| Diagnose | `python scripts/run_tool.py doctor` |
| List datasets | `python scripts/run_tool.py list-datasets` |
| Crawl URL | `python -m crawler run --input <input.jsonl> --output <output_dir>` |
| Enrich records | `python -m crawler enrich --input <records.jsonl> --output <output_dir>` |
| Validate schema | `python scripts/schema_tools.py validate` |
| Export submissions | `python scripts/run_tool.py export-core-submissions <input> <output> <datasetId>` |

## Flow

1. Run **Check readiness** first
2. If not initialized → run **Initialize** → then check again
3. When ready → **Start mining**
4. Control with **Check status** / **Pause** / **Resume** / **Stop**

## Reference

Read these docs only when needed for the specific topic:

- [Browser session & login](./docs/BROWSER_SESSION.md) — cookie import, auto-login, PrepareBrowserSession
- [Internal commands & rules](./docs/INTERNAL_COMMANDS.md) — full command mapping, readiness states, behavior rules
- [Agent guide](./docs/AGENT_GUIDE.md) — detailed operational guide
- [Environment](./docs/ENVIRONMENT.md) — environment variables and config
- [OpenClaw integration](./docs/OPENCLAW_HOST_INTEGRATION.md) — host contract for OpenClaw
