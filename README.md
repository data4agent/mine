# Mine

Agent-first skill project for autonomous data-mining workflows powered by the built-in `mine` runtime.

## What this project is

`mine` is the primary **skill + Python runtime** project. It provides:

- an internal Python crawler/enrichment runtime under `crawler/`
- a first-load / dataset-listing / status-summary runtime for guided Mine UX
- a single CLI entrypoint via `scripts/run_tool.py`
- bootstrap and verification scripts for one-repo setup
- references, runtime helpers, and schema support files
- a root skill contract that can be reused across agent hosts

The crawler engine now lives inside this repository. `mine` owns the runtime, schemas, references, and skill workflow.

## Primary entrypoint

Use `scripts/run_tool.py` as the only public command surface:

```bash
python scripts/run_tool.py first-load
python scripts/run_tool.py start-working
python scripts/run_tool.py check-status
python scripts/run_tool.py list-datasets
python scripts/run_tool.py run-worker
python scripts/run_tool.py run-once
python scripts/run_tool.py process-task-file <taskType> <taskJsonPath>
python scripts/run_tool.py export-core-submissions <inputPath> <outputPath> <datasetId>
```

## Bootstrap and verification

### Unix-like

```bash
./scripts/bootstrap.sh
python scripts/verify_env.py --profile minimal --json
python scripts/host_diagnostics.py --json
python scripts/smoke_test.py --json
```

### Windows

```powershell
./scripts/bootstrap.ps1
./scripts/bootstrap.cmd
python scripts/verify_env.py --profile minimal --json
python scripts/host_diagnostics.py --json
python scripts/smoke_test.py --json
```

The bootstrap flow creates or reuses a virtualenv, installs layered requirements, runs host diagnostics, verifies the environment, and finishes with a smoke test.

## Runtime environment

Required:

- `PLATFORM_BASE_URL`
- `MINER_ID`

Important optional variables:

- `SOCIAL_CRAWLER_ROOT`
- `PYTHON_BIN`
- `PLATFORM_TOKEN`
- `CRAWLER_OUTPUT_ROOT`
- `MINE_CONFIG_PATH`
- `MINE_GATEWAY_TOKEN`
- `MINE_GATEWAY_BASE_URL`
- `MINE_ENRICH_MODEL`
- `MINE_UPSTREAM_MODEL`
- `AWP_WALLET_BIN`
- `AWP_WALLET_TOKEN`
- `AWP_WALLET_TOKEN_SECRET_REF`
- `WORKER_STATE_ROOT`
- `WORKER_MAX_PARALLEL`

`SOCIAL_CRAWLER_ROOT` defaults to the current `mine` project root, so most agents can run without extra path configuration. `MINE_CONFIG_PATH` defaults to `~/.mine/mine.json`.

## Generic payload compatibility

Mine can process compatibility inputs like `generic/page` and `generic` task payloads when a local task file or platform item uses a generic web extraction flow.

## Why skill-only

- one runtime entrypoint for all agents
- no host-specific install wrapper layer
- easier portability across Cursor, Codex, Claude, OpenAI-style agents, and plain shell execution
- clearer separation: `SKILL.md` explains behavior, `scripts/run_tool.py` executes it

## awp-wallet

Mine uses `awp-wallet` for time-limited signing sessions. A typical recovery command is:

```bash
awp-wallet unlock --duration 3600
```

Do not store seed phrases or private keys in repository files, config dumps, or logs.

## Local verification

```bash
python -m pytest tests -q
python -m pytest crawler/tests/test_bootstrap_assets.py -q
python scripts/run_tool.py --help
```
