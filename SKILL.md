---
name: mine
description: >
  Autonomous data mining and validation on the ocDATA / aMine platform. Use this
  skill whenever the user mentions: mining, miner, validator, validating, aMine,
  ocDATA, data mining rewards, crawling for rewards, earning tokens by crawling,
  mining status, mining start/stop/pause/resume, dataset selection, repeat crawl,
  evaluation tasks, mining diagnostics, doctor, mining errors, 401/auth errors
  related to mining, submission scores, epoch rewards, credit tier, or anything
  about running autonomous data collection workers. Also trigger when the user
  asks to "go online", "start earning", "check my submissions", or troubleshoot
  platform connectivity issues. ALL platform interaction goes through
  `python scripts/run_tool.py` — never make direct HTTP calls (they require
  EIP-712 signatures and will always fail). Not for AWP wallet transfers,
  RootNet staking, smart contract deployment, or general server monitoring.
version: 0.9.2
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
  emoji: "⛏️"
  homepage: https://github.com/data4agent/mine
---

# Mine

Autonomous data mining & validation on AWP. Agents earn $aMine rewards by
crawling public data and validating others' submissions.

## Agent-First Design

This skill is designed for **agent execution** — all commands must be run by you
(the agent) in the terminal. **Never show command text to the user.** Instead,
execute commands yourself and present the results as natural-language summaries.

Every command outputs JSON with:

- `user_message` — show this to the user (natural language)
- `user_actions` — action options to present (natural language labels)
- `_internal` — for your eyes only, contains `action_map` mapping labels to commands

**Workflow**: Run command → parse JSON → show `user_message` to user → if user
picks an action from `user_actions`, look up the command in `_internal.action_map`
and execute it.

## Rules

1. **Execute commands yourself.** Never display `python scripts/run_tool.py ...` to
   the user. Run the command, read the JSON output, and speak to the user in natural
   language based on `user_message`.

2. **Only use `run_tool.py` commands.** Never make HTTP requests (curl, fetch, httpx,
   requests, WebFetch) to the platform. Never construct JSON-RPC payloads. The platform
   requires cryptographic signatures — raw HTTP calls always fail with 401.

3. **Never expose secrets.** Do not print `AWP_WALLET_TOKEN`, `VALIDATOR_PRIVATE_KEY`,
   private keys, mnemonics, or `.env` contents. To check if set: `[ -n "$VAR" ] && echo "set"`.

4. **Use `_internal` for next steps.** When the JSON output contains `_internal.action_map`,
   use it to determine which command to run next. Never show `_internal` content to the user.

## LLM Enrich With OpenClaw

When the user asks you to run or debug **LLM enrich**, **OpenClaw enrich**, or
why enrichment is not producing fields, you must execute the enrich flow
yourself and verify the result from logs and cache artifacts instead of just
describing the command.

- Prefer the crawler path that already wires OpenClaw in:
  `python3 -m crawler run ... --use-openclaw`
- Treat OpenClaw as the first-choice enrich backend when available.
- Confirm actual OpenClaw execution from logs, not assumptions. The important
  markers are:
  - `[enrich] openclaw start ...`
  - `[enrich] openclaw end ...`
  - `[AGENT] CLI start ...`
  - `[AGENT] CLI end ...`
- Successful generative groups write normal cache files under
  `.cache/enrich/`.
- Failed, skipped, partial, or pending groups write debug artifacts under
  `.cache/enrich/_debug/`. Check this directory whenever the user says enrich
  "didn't run", "only base fields appeared", or "no task available".
- If you diagnose OpenClaw problems, report whether the failure is:
  - task sourcing / no executable work
  - field-group source data missing
  - OpenClaw agent creation / routing
  - model response / JSON parse failure

## Fast Path

When the user wants practical mining progress instead of code analysis, use
this order:

1. Check readiness with `agent-status`
2. Check whether a worker is already active with `agent-control status`
3. If idle, start mining
4. Judge progress from real artifacts, not only from high-level status text
5. If a task looks stalled, inspect the task output directory before changing code

For arXiv, the most useful files are:

- `artifacts/<paper_id>/fetch.json`
- `artifacts/<paper_id>/structured.json`
- `.cache/enrich/*.json`
- `.cache/enrich/_debug/*.json`
- `records.jsonl`
- `summary.json`
- `core-submissions.json`
- `core-submissions-response.json`

If `records.jsonl` and `summary.json` exist, the crawler run itself has already
completed. If `core-submissions-response.json` also exists, submission export
was reached.

## Known Pitfalls

- `no task available` does not mean a ban. It usually means backend claim,
  dataset discovery, and resume queue all returned no executable work.
- For arXiv, a task can look "stuck" even after fetch/extract succeeded. Check
  the task directory first. If `artifacts/` and `.cache/enrich/` are present,
  the run is usually waiting on late-stage LLM enrich rather than page fetch.
- Do not assume OpenClaw is unused just because final fields are sparse.
  Skipped/failed/pending groups are written to `.cache/enrich/_debug/`.
- In this repo, heavy arXiv generative groups are the dominant runtime cost.
  A single field group can take 15s to 25s.
- The stable default is: crawl serial, LLM enrich conservative. Increasing task
  concurrency before verifying OpenClaw behavior usually causes worker-level
  timeouts.
- A task may produce fetch artifacts and many enrich cache files but still fail
  the outer worker if `crawler run` does not finish before the worker timeout.
- arXiv uses API fetch, but the runtime may still start Playwright internals.
  This is noisy and can mislead diagnosis; it is not always the root cause.
- Old `crawler run` processes can linger after experiments and steal CPU or
  OpenClaw capacity. Check and clean them before judging worker health.

## Recommended Runtime

For stable mining defaults:

- `WORKER_MAX_PARALLEL=1`
- `CRAWL_TIMEOUT_SECONDS=900`

For "collection serial, enrich concurrent" experiments:

- `WORKER_MAX_PARALLEL=1`
- `MINE_ENRICH_CONCURRENCY=2`
- `MINE_ENRICH_AGENT_POOL_SIZE=2`

This keeps task collection serial while allowing a small fixed pool of
concurrent OpenClaw enrich calls.

## Welcome Screen

On first launch (no worker running), or whenever the user says `start` without
specifying a mode, **ask the user to choose a working mode first**:

```text
mine - autonomous data mining

crawl data. earn rewards. fully autonomous.

-- choose your mode ----------------
1. Repeat Tasks      - claim platform repeat/refresh tasks
2. Validator         - validate submissions, earn $aMine
3. Active Discovery  - proactively crawl and submit data
------------------------------------

which mode? (1, 2, or 3)
```

**Do NOT skip this step.** The user must choose before any worker starts.

- "repeat", "repeat tasks", "claim tasks", "1" → **Repeat Task Mode**
- "validator", "validate", "start validating", "2" → **Validator Mode**
- "active", "discovery", "self crawl", "mine", "start mining", "3" → **Active Discovery Mode**
- If unclear, ask again

## Mining Architecture

### Task Sources

Each worker iteration collects tasks from three independent sources:

| Source            | Class                    | Where tasks come from                       | Dataset-filtered |
| ----------------- | ------------------------ | ------------------------------------------- | ---------------- |
| Backend Claim     | `BackendClaimSource`     | Platform claim API (repeat-crawl / refresh) | No               |
| Dataset Discovery | `DatasetDiscoverySource` | Seed URLs from dataset `source_domains`     | Yes              |
| Resume            | `ResumeQueueSource`      | Backlog / auth_pending from prior failures  | No               |

All three are collected in parallel, merged, and deduplicated. Up to
`max_parallel` items enter the current iteration.

> "no task available" means none of the three sources produced an executable
> task — most commonly because Backend Claim returned nothing and Discovery is
> in cooldown. This does **not** mean your miner is banned.

### Discovery Behavior

Dataset Discovery is platform-specific:

1. **API-direct discovery** — some platforms fetch content URLs from an upstream
   API and go straight to the `run` phase.
2. **discover-crawl + run** — other platforms start from seed pages, extract
   follow-up links, and execute them with `run`.

Current special cases:

- **arXiv** — uses the arXiv API to fetch recent `/abs/...` paper URLs directly.
  Listing pages are **never** sent into the submission pipeline.
- **Wikipedia** — uses the MediaWiki Random API, skipping `discover-crawl`.
- **Amazon** — may still use seed-page discovery followed by `discover-crawl`.

### API Call Chain

```text
Discovery path:
  GET  /api/core/v1/datasets                          <- dataset list
  GET  /api/core/v1/url/check                         <- dedup check
  (local crawler fetches content URL)
  POST /api/core/v1/submissions                       <- submit data
  POST /api/mining/v1/pow-challenges/{id}/answer      <- PoW (probabilistic)

Backend Claim path:
  POST /api/mining/v1/repeat-crawl-tasks/claim        <- claim task
  (local crawler fetches target site)
  POST /api/mining/v1/repeat-crawl-tasks/{id}/report  <- report result
  POST /api/core/v1/submissions                       <- submit data
```

Both paths ultimately submit via `POST /api/core/v1/submissions`.

### Dataset Selection

- Platform returns only 1 dataset — auto-selected.
- Multiple datasets, none selected — enters `selection_required`; user must choose.
- `selected_dataset_ids` only filters Discovery / followup tasks; Backend Claim
  tasks are not affected.

### Credit Tier & Limits

| Tier   | `credit_score` | Backend Claim           | Discovery Submissions                     |
| ------ | -------------- | ----------------------- | ----------------------------------------- |
| novice | 0              | Platform may not assign | Normal, but epoch settlement gate applies |
| higher | > 0            | Normal assignment       | Normal                                    |

Epoch settlement gate: `task_count >= 80` and `avg_score >= 60` (protocol v2.0).
A novice miner's primary path is **Active Discovery** to accumulate submissions.

## Miner Workflow

Repeat Task Mode and Active Discovery Mode both launch the same miner worker.
The difference is the **user's intent**:

- **Repeat Task Mode** — emphasize platform-claimed repeat/refresh tasks.
- **Active Discovery Mode** — emphasize proactive dataset crawling and submission.

The miner implementation collects Backend Claim, Dataset Discovery, and Resume
sources in every iteration regardless of mode.

### Start Miner Worker

Step 1 — Check readiness:

```bash
cd {baseDir} && python scripts/run_tool.py agent-status
```

If `ready` is false, execute the fix command from `_internal.action_map`.

Step 2 — Start worker:

```bash
cd {baseDir} && python scripts/run_tool.py agent-start
```

If `selection_required`, present dataset names and re-run with the chosen ID:

```bash
cd {baseDir} && python scripts/run_tool.py agent-start <datasetId>
```

Step 3 — Confirm to the user. Example:

```text
[1/3] wallet       0x1234...5678  ok
[2/3] platform     connected      ok
[3/3] worker       started (session: abc12)  ok

mining. say "mine status" to check progress.
```

Adapt the confirmation message to the chosen mode:

- **Repeat Task Mode** — "claiming repeat/refresh tasks when available."
- **Active Discovery Mode** — "proactively crawling datasets and submitting."

### Check Status

```bash
cd {baseDir} && python scripts/run_tool.py agent-control status
```

### Stop / Pause / Resume

```bash
cd {baseDir} && python scripts/run_tool.py agent-control stop
cd {baseDir} && python scripts/run_tool.py agent-control pause
cd {baseDir} && python scripts/run_tool.py agent-control resume
```

### List Datasets

```bash
cd {baseDir} && python scripts/run_tool.py list-datasets
```

### Diagnose

```bash
cd {baseDir} && python scripts/run_tool.py doctor
```

## Validator Workflow

### Start Validating

```bash
cd {baseDir} && python scripts/run_tool.py validator-start
```

Auto-installs dependencies, submits validator application, and connects via
WebSocket. If the application status is `pending_review`, re-run after approval.

### Check Status / Stop

```bash
cd {baseDir} && python scripts/run_tool.py validator-control status
cd {baseDir} && python scripts/run_tool.py validator-control stop
```

### Diagnose Validator

```bash
cd {baseDir} && python scripts/run_tool.py validator-doctor
```

## Debugging Background Workers

Background workers write output to log files. `agent-control status` surfaces
recent errors automatically. For more detail, read the log at
`_internal.log_path`:

```bash
cd {baseDir} && tail -50 output/agent-runs/<session_id>.log
```

## Error Recovery

If any command returns `401` or an authentication error:

1. Run `python scripts/run_tool.py doctor` to diagnose.
2. Follow the fix instructions in the output.
3. Common causes: expired wallet session, missing AWP registration.

If the error is `address_not_registered` or `registration_required`:

1. The wallet must be registered on-chain first.
2. Tell the user to **install and use the AWP Skill** for registration.
3. After registration, retry `agent-start`.

**Do NOT** tell users to register on a website or call registration APIs manually.

If you see `signer_mismatch`, it usually means EIP-712 signature parameters
are wrong. The `doctor` command handles diagnostics. Never attempt to fix auth
by making HTTP calls, adding headers, or reading signing code.

## Intent Routing

| User says | Action |
| --- | --- |
| "start" / "go online" | Ask which mode: Repeat Tasks / Validator / Active Discovery |
| "repeat" / "claim tasks" | Run miner workflow via `agent-start` |
| "active" / "discovery" / "self crawl" | Run miner workflow via `agent-start` |
| "validator" / "start validating" | Run `validator-start` |
| "status" / "how am I doing" | `agent-control status` or `validator-control status` |
| "stop" | `agent-control stop` or `validator-control stop` |
| "pause" | `agent-control pause` (miner only) |
| "resume" | `agent-control resume` (miner only) |
| "datasets" / "what can I mine" | `list-datasets` |
| "diagnose" / "doctor" / "fix" | `doctor` or `validator-doctor` |
| "help" | List available actions in natural language |
| "switch mode" / "switch role" | Re-show Welcome Screen |
| "401 error" / "auth error" | Run `doctor` (see Error Recovery) |

## Sub-Agent Guidelines

- **One mining worker per session** — do not spawn multiple concurrent miners.
- Use `agent-control status` to poll progress.
- Use `agent-control stop` to terminate.
- All platform interaction goes through `run_tool.py` — sub-agents included.

## Configuration

No environment variables needed by default. Everything is auto-detected.

EIP-712 signature parameters are fetched from the platform automatically.
Do **not** override them in `.env` unless you know the exact values — a wrong
`EIP712_VERIFYING_CONTRACT` causes `signer_mismatch` 401 errors.

Runtime overrides (optional, via `.env` or shell):

| Variable              | Default                    | Description              |
| --------------------- | -------------------------- | ------------------------ |
| `PLATFORM_BASE_URL`   | `https://api.minework.net` | Platform API endpoint    |
| `MINER_ID`            | `mine-agent`               | Miner identifier         |
| `WORKER_MAX_PARALLEL` | `1`                        | Concurrent crawl workers |
| `CRAWL_TIMEOUT_SECONDS` | `900`                    | Per-item crawler timeout |
| `MINE_ENRICH_CONCURRENCY` | unset                  | LLM enrich field-group concurrency override |
| `MINE_ENRICH_AGENT_POOL_SIZE` | unset              | Fixed OpenClaw agent pool size for concurrent LLM enrich |

For validator settings, see `docs/ENVIRONMENT.md`.

For stable mining, keep crawl collection serial. If you need faster LLM enrich,
prefer enabling a small fixed agent pool instead of task-level crawl parallelism:

- `WORKER_MAX_PARALLEL=1`
- `MINE_ENRICH_CONCURRENCY=2`
- `MINE_ENRICH_AGENT_POOL_SIZE=2`

This keeps dataset collection serial while allowing at most two concurrent
OpenClaw enrich calls through stable fixed agent IDs.

## Advanced

Read these docs only when needed:

- [Browser session & login](./docs/BROWSER_SESSION.md)
- [Internal commands & rules](./docs/INTERNAL_COMMANDS.md)
- [Agent guide](./docs/AGENT_GUIDE.md)
- [Environment](./docs/ENVIRONMENT.md)
- [Validator Protocol](./references/protocol-validator.md)
