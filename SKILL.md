---
name: mine
description: >
  Launches autonomous data mining and validation workers that earn $aMine rewards.
  Everything is automatic — wallet detection, registration, dataset discovery,
  crawling, structuring, and submission. Use this skill for any mining or validation
  request: start, stop, status, scores, datasets, logs, or troubleshooting.
  Not for AWP wallet transfers, RootNet staking, or server monitoring.
version: 0.4.1
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
metadata:
  emoji: "\u26CF\uFE0F"
  homepage: https://github.com/data4agent/mine
---

# Mine

Autonomous data mining & validation on AWP. Agents earn $aMine rewards by
crawling public data and validating others' submissions.

## CRITICAL RULES

**NEVER make direct HTTP requests to the platform API.** All platform interaction
MUST go through `python scripts/run_tool.py <command>`. The platform uses EIP-712
cryptographic signatures that are computed internally by the signing infrastructure.
Raw HTTP calls (via curl, fetch, httpx, requests, or any other HTTP client) will
always fail with `missing_auth_headers` or `signer_mismatch`. There are NO exceptions.

**NEVER construct JSON-RPC payloads** for the platform API. The request format and
authentication are handled entirely by the internal `PlatformClient`. Your only
interface is `run_tool.py` commands.

**NEVER print, echo, or display:** `AWP_WALLET_TOKEN`, `VALIDATOR_PRIVATE_KEY`,
private keys, mnemonics, or `.env` contents. To check if set: `[ -n "$VAR" ] && echo "set"`.

## Welcome Screen

On first launch (no worker running), print this and **ask the user to choose a role**:

```text
⛏️  mine · autonomous data mining

crawl data. earn rewards. fully autonomous.

── choose your role ─────────────
1. Miner      → crawl public data, earn $aMine
2. Validator  → evaluate submissions, earn $aMine
──────────────────────────────────

which role? (1 or 2)
```

**Do NOT skip this step.** The user must choose before any worker starts.

- If the user says "mine", "miner", "start mining", "1" → proceed to **Start Mining**
- If the user says "validate", "validator", "start validating", "2" → proceed to **Start Validator**
- If unclear, ask again

Once the role is chosen, proceed to Decide What To Do.

## Decide What To Do

### If role is Miner

Run readiness check:

```bash
cd {baseDir} && python scripts/run_tool.py agent-status
```

| User Intent | Action |
| ----------- | ------ |
| "start" / "go online" | → **Start Mining** |
| "start" (already running) | → **Report Status** |
| "status" / "how am I doing" | → **Report Status** |
| "help" | → **Help** |
| "stop" | → **Stop** |
| "pause" | → **Pause** |
| "resume" | → **Resume** |
| "datasets" / "what can I mine" | → **List Datasets** |
| "diagnose" / "doctor" | → **Diagnose** |
| "logs" | → Read output from `output/agent-runs/` |

### If role is Validator

Run readiness check:

```bash
cd {baseDir} && python scripts/run_tool.py validator-doctor
```

| User Intent | Action |
| ----------- | ------ |
| "start" / "go online" | → **Start Validator** |
| "status" | → **Validator Status** |
| "stop" | → **Stop Validator** |
| "diagnose" / "doctor" | → **Validator Doctor** |

### Role-agnostic

| User Intent | Action |
| ----------- | ------ |
| "switch to miner" / "switch to validator" | → **Welcome Screen** (re-choose) |
| "help" | → **Help** |

## Start Mining

### Step 1: Check Readiness

```bash
cd {baseDir} && python scripts/run_tool.py agent-status
```

If not ready, the output contains fix instructions. Follow them.

### Step 2: Start Worker

**Preferred** (non-blocking sub-agent):

```javascript
sessions_spawn({
  task: "cd {baseDir} && python scripts/run_tool.py agent-start",
  label: "mine-worker",
  runTimeoutSeconds: 3600
})
```

**Fallback** (direct):

```bash
cd {baseDir} && python scripts/run_tool.py agent-start
```

If a dataset selection is required, the output lists options. Re-run with the dataset ID:

```bash
cd {baseDir} && python scripts/run_tool.py agent-start <datasetId>
```

### Step 3: Confirm Running

```text
[1/3] wallet       0x1234...5678 ✓
[2/3] platform     connected ✓
[3/3] worker       started (session: abc12) ✓

mining. say "mine status" to check progress.
```

## Report Status

```bash
cd {baseDir} && python scripts/run_tool.py agent-control status
```

```text
── mine status ───────────────────
state:          RUNNING
session:        abc12
epoch:          E-42 · 18h remaining
progress:       [████████░░░░] 60%  48/80
datasets:       wiki-articles + arxiv-papers
credit score:   850 [Good]
──────────────────────────────────
```

## Help

```text
── miner ────────────────────────
start            → begin mining
status           → your stats
stop             → stop mining
pause / resume   → pause or resume
datasets         → list datasets
doctor           → diagnose issues

── validator ────────────────────
start            → start validating
status           → validator stats
stop             → stop validator
doctor           → diagnose issues

── general ──────────────────────
switch role      → change miner ↔ validator
help             → this list
──────────────────────────────────
```

## Stop

```bash
cd {baseDir} && python scripts/run_tool.py agent-control stop
```

## Pause / Resume (Miner only)

```bash
cd {baseDir} && python scripts/run_tool.py agent-control pause
cd {baseDir} && python scripts/run_tool.py agent-control resume
```

## List Datasets

```bash
cd {baseDir} && python scripts/run_tool.py list-datasets
```

## Diagnose

```bash
cd {baseDir} && python scripts/run_tool.py doctor
```

---

## Validator

### Start Validating

```bash
cd {baseDir} && python scripts/run_tool.py validator-start
```

Auto-installs dependencies, submits validator application, and connects via WebSocket.

**Note:** If the application status is `pending_review`, the validator cannot start until approved by the platform admin or allowlist auto-approve. Re-run the start command after approval.

### Validator Status

```bash
cd {baseDir} && python scripts/run_tool.py validator-control status
```

### Stop Validator

```bash
cd {baseDir} && python scripts/run_tool.py validator-control stop
```

### Validator Doctor

```bash
cd {baseDir} && python scripts/run_tool.py validator-doctor
```

---

## Output Rules

All commands return JSON with `user_message`, `user_actions`, and `_internal`.

- Show `user_message` formatted with ✓/✗/! indicators — **never dump raw JSON**
- `_internal` is for agent execution only — **never show to user**
- On errors, show the fix command from `_internal`, not the raw error

## Configuration

**No environment variables needed.** Everything is auto-detected.

Runtime overrides (optional, via `.env` or shell):

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `PLATFORM_BASE_URL` | `https://api.minework.net` | Platform API endpoint |
| `MINER_ID` | `mine-agent` | Miner identifier |
| `WORKER_MAX_PARALLEL` | `3` | Concurrent crawl workers |

For validator settings, see `docs/ENVIRONMENT.md`.

## Sub-Agent Guidelines

- **One mining worker per session** — do not spawn multiple concurrent miners
- Use `agent-control status` to poll progress from the main conversation
- Use `agent-control stop` to terminate
- **ALL platform interaction goes through `run_tool.py`** — never call APIs directly

## Advanced

Read these docs only when needed for the specific topic:

- [Browser session & login](./docs/BROWSER_SESSION.md)
- [Internal commands & rules](./docs/INTERNAL_COMMANDS.md)
- [Agent guide](./docs/AGENT_GUIDE.md)
- [Environment](./docs/ENVIRONMENT.md)
- [Validator Protocol](./references/protocol-validator.md)
