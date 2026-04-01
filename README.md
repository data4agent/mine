# Mine

OpenClaw-first plugin/skill project for autonomous data-mining workflows backed by `social-data-crawler`.

## What this project is

`mine` is the OpenClaw-facing product layer. It provides:

- a native OpenClaw plugin manifest
- tool registration for worker-style mining operations
- a Python bridge that reuses the proven `social-data-crawler` runtime
- build/install scripts for packaging `dist/openclaw-plugin`
- a root skill contract for OpenClaw workspace usage

The crawler engine remains in `D:\kaifa\clawtroop\social-data-crawler`. `mine` orchestrates it.

## Registered OpenClaw tools

- `mine_worker`
- `mine_heartbeat`
- `mine_run_once`
- `mine_run_loop`
- `mine_process_task_file`
- `mine_export_core_submissions`

## Required plugin config

- `crawlerRoot`
- `platformBaseUrl`
- `minerId`

Important optional config:

- `pythonBin`
- `platformToken`
- `outputRoot`
- `awpWalletBin`
- `awpWalletToken`
- `awpWalletTokenRef`
- `workerStateRoot`
- `workerMaxParallel`

## Build

```bash
python scripts/build_openclaw_plugin.py
```

Outputs:

- `dist/openclaw-plugin`
- `dist/mine-openclaw-plugin.zip`
- `dist/mine-openclaw-plugin.tar.gz`

## Install into OpenClaw

### Windows

```powershell
./scripts/install_openclaw_integration.ps1 --platform-base-url http://101.47.73.95 --miner-id miner-001
```

### Unix-like

```bash
./scripts/install_openclaw_integration.sh --platform-base-url http://101.47.73.95 --miner-id miner-001
```

The installer:

- builds `dist/openclaw-plugin`
- optionally builds the archive bundle
- updates `~/.openclaw/openclaw.json` or `OPENCLAW_CONFIG_PATH`
- installs a workspace skill wrapper under `~/.openclaw/workspace/skills/mine`
- uses `awpWalletTokenRef` when no direct token is available

Archive installs are guarded: if `plugin-source=archive` is selected but `dist/mine-openclaw-plugin.tar.gz` does not exist, the installer fails before writing config.

## Config example

See [`openclaw.config.example.jsonc`](./openclaw.config.example.jsonc).

This project uses the current OpenClaw `plugins.installs` schema, not the legacy `plugins.entries` format.

## Local verification

```bash
python scripts/build_openclaw_plugin.py --no-archive
python -m pytest tests/test_openclaw_plugin_contract.py -q
python scripts/run_tool.py --help
```
