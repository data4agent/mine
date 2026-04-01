---
name: mine
description: OpenClaw-first autonomous mining skill that delegates crawling/extraction to social-data-crawler and exposes worker tools through the mine plugin.
metadata:
  openclaw:
    install:
      script_windows: ./scripts/install_openclaw_integration.ps1
      script_unix: ./scripts/install_openclaw_integration.sh
---

# Mine

Use this skill when the task is to operate the OpenClaw-facing mining workflow:

- run autonomous mining workers
- send mining heartbeats
- process task payload files
- export core submission payloads
- install or package the Mine OpenClaw plugin

## Runtime model

`mine` is the OpenClaw product layer.

- OpenClaw plugin root: this repository
- Crawler runtime: `D:\kaifa\clawtroop\social-data-crawler` by default
- Wallet signing: `awp-wallet`

## Key tools

- `mine_worker` — primary autonomous worker
- `mine_run_once` — one-shot debug/compat execution
- `mine_run_loop` — repeated loop execution
- `mine_heartbeat` — heartbeat only
- `mine_process_task_file` — process one local task payload
- `mine_export_core_submissions` — convert crawler output into core submission JSON

## Installation

Prefer:

- Windows: `./scripts/install_openclaw_integration.ps1`
- Unix-like: `./scripts/install_openclaw_integration.sh`

## Packaging

Build the OpenClaw plugin bundle with:

```bash
python scripts/build_openclaw_plugin.py
```
