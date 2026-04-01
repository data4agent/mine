# Mining Commands Reference

All runtime commands go through `scripts/run_tool.py`. This is the only public CLI surface.

## Primary Commands

### `first-load`

```bash
python scripts/run_tool.py first-load
```

Renders the welcome experience: welcome message, dependency check results, and quick-start actions. Also used on first skill load by any agent.

### `check-again`

```bash
python scripts/run_tool.py check-again
```

Alias for `first-load`. Re-runs the dependency check after the user has fixed something.

### `start-working`

```bash
python scripts/run_tool.py start-working [dataset_id1,dataset_id2,...]
```

Begins autonomous mining. Optionally accepts a comma-separated list of dataset IDs to constrain work. Without arguments, uses all eligible datasets. On first run, the agent should confirm the dataset selection with the user.

### `check-status`

```bash
python scripts/run_tool.py check-status
```

Renders a human-readable status summary: mining state, credit score/tier, epoch progress, active datasets, and recent activity.

### `status-json`

```bash
python scripts/run_tool.py status-json
```

Returns structured JSON status for programmatic consumption.

### `list-datasets`

```bash
python scripts/run_tool.py list-datasets
```

Lists active datasets with their IDs, names, and current epoch metadata.

### `run-worker`

```bash
python scripts/run_tool.py run-worker
```

Starts the full autonomous worker loop. This is the primary long-running mining command. Handles heartbeat, batch work, epoch monitoring, and stop conditions internally.

### `run-once`

```bash
python scripts/run_tool.py run-once
```

Single-pass execution. Runs one batch of work and exits. Useful for debugging or validating a single cycle.

### `run-loop`

```bash
python scripts/run_tool.py run-loop
```

Repeated loop execution. Use only when explicitly requested.

### `heartbeat`

```bash
python scripts/run_tool.py heartbeat
```

Sends a single heartbeat to the platform and reports the result. Useful for verifying connectivity and registration state.

## Control Commands

### `pause`

```bash
python scripts/run_tool.py pause
```

Signals the runtime to pause after the current batch completes. Sets `mining_state = paused`. Does not interrupt in-progress work.

### `resume`

```bash
python scripts/run_tool.py resume
```

Resumes a paused session. Sets `mining_state = running` and continues from the next batch.

### `stop`

```bash
python scripts/run_tool.py stop
```

Signals the runtime to stop after the current batch completes. The agent should confirm this action with the user before executing. On stop, a final session summary is printed.

## Payload Commands

### `process-task-file`

```bash
python scripts/run_tool.py process-task-file <taskType> <taskJsonPath>
```

Processes a local task JSON file. Useful for offline execution or when a task payload is already available outside the normal claim flow. `taskType` is one of `repeat-crawl` or `refresh`.

### `export-core-submissions`

```bash
python scripts/run_tool.py export-core-submissions <inputPath> <outputPath> <datasetId>
```

Converts crawler output records into platform-ready submission payloads. Reads from `inputPath` (typically `records.jsonl`), writes to `outputPath`, tagged with `datasetId`.

## Verification Commands

These are not part of `run_tool.py` but are used for environment validation:

```bash
python scripts/verify_env.py --profile minimal --json
python scripts/host_diagnostics.py --json
python scripts/smoke_test.py --json
```

## Command Priority

When the user's intent is ambiguous, prefer commands in this order:

1. `run-worker` — primary autonomous worker
2. `run-once` — debug or single-pass
3. `process-task-file` — local payload available
4. `heartbeat` — connectivity check only
5. `run-loop` — only when explicitly requested
6. `export-core-submissions` — conversion/export only
