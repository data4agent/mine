---
name: mine
description: >
  Launches autonomous data mining and validation workers that earn $aMine rewards.
  ALL platform interaction goes through `python scripts/run_tool.py` commands —
  never make direct HTTP/curl/fetch calls to the API (they require EIP-712 crypto
  signatures and will always fail). Use this skill for any mining or validation
  request: start, stop, status, scores, datasets, logs, or troubleshooting.
  Not for AWP wallet transfers, RootNet staking, or server monitoring.
version: 0.8.1
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

## Welcome Screen

On first launch (no worker running), show this and **ask the user to choose a role**:

```text
mine - autonomous data mining

crawl data. earn rewards. fully autonomous.

-- choose your role ----------------
1. Miner      - crawl public data, earn $aMine
2. Validator  - evaluate submissions, earn $aMine
------------------------------------

which role? (1 or 2)
```

**Do NOT skip this step.** The user must choose before any worker starts.

- "mine", "miner", "start mining", "1" -> **Start Mining**
- "validate", "validator", "start validating", "2" -> **Start Validator**
- If unclear, ask again

## Miner Workflow

### Start Mining

Step 1 — Check readiness (run in terminal, do not show command to user):

```bash
cd {baseDir} && python scripts/run_tool.py agent-status
```

Parse the JSON output. If `ready` is false, execute the command from
`_internal.action_map` to fix the issue. Tell the user what's happening
in plain language.

Step 2 — Start worker (run in terminal):

```bash
cd {baseDir} && python scripts/run_tool.py agent-start
```

If dataset selection is required (state = `selection_required`), present the
dataset names from `user_message` to the user. After they choose, re-run with:

```bash
cd {baseDir} && python scripts/run_tool.py agent-start <datasetId>
```

Step 3 — Confirm to user using `user_message` from the JSON output. Example:

```text
[1/3] wallet       0x1234...5678  ok
[2/3] platform     connected  ok
[3/3] worker       started (session: abc12)  ok

mining. say "mine status" to check progress.
```

### Check Status

Run in terminal and show `user_message` to user:

```bash
cd {baseDir} && python scripts/run_tool.py agent-control status
```

### Stop / Pause / Resume

Run the appropriate command based on user intent:

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

Auto-installs dependencies, submits validator application, and connects via WebSocket.
If the application status is `pending_review`, the validator cannot start until approved.
Re-run the start command after approval.

### Check Status / Stop

```bash
cd {baseDir} && python scripts/run_tool.py validator-control status
cd {baseDir} && python scripts/run_tool.py validator-control stop
```

### Diagnose

```bash
cd {baseDir} && python scripts/run_tool.py validator-doctor
```

## Debugging Background Workers

Background mining/validation workers write all output (including errors) to log files.
The `agent-control status` command automatically surfaces recent errors from the log.
If you need more detail, the log path is in the `_internal.log_path` field of the status response:

```bash
cd {baseDir} && tail -50 output/agent-runs/<session_id>.log
```

Always check `agent-control status` first — it shows recent errors without needing to read the log directly.

## Error Recovery

If any command returns a `401` or authentication error:

1. Run `python scripts/run_tool.py doctor` to diagnose
2. Follow the fix instructions in the output
3. Common causes: expired wallet session, missing AWP registration

If the error is `address_not_registered` or `registration_required`:

1. The wallet needs to be registered on-chain before mining can start
2. Tell the user to **install and use the AWP Skill** to complete registration
3. If the AWP Skill is not installed, guide the user to install it first
4. After registration completes, retry `python scripts/run_tool.py agent-start`

**Do NOT** tell users to register on a website or manually call any registration API.
The AWP Skill handles the entire on-chain registration flow automatically.

If you see `missing_auth_headers` or `signer_mismatch`, it means something
bypassed `run_tool.py`. Stop and use the commands listed above instead.

**Never attempt to fix auth by making HTTP calls, adding headers, or reading
signing code.** The `doctor` command handles all auth diagnostics.

## Intent Routing

| User says | Action to take |
|-----------|---------------|
| "start" / "go online" | Run `agent-start` or `validator-start` (depends on role) |
| "status" / "how am I doing" | Run `agent-control status` or `validator-control status` |
| "stop" | Run `agent-control stop` or `validator-control stop` |
| "pause" | Run `agent-control pause` (miner only) |
| "resume" | Run `agent-control resume` (miner only) |
| "datasets" / "what can I mine" | Run `list-datasets` |
| "diagnose" / "doctor" / "fix" | Run `doctor` or `validator-doctor` |
| "help" | Tell the user what actions are available in natural language |
| "switch role" | Re-show Welcome Screen |
| "check connectivity" / "heartbeat" | Run `doctor` (never direct HTTP) |
| "401 error" / "auth error" | Run `doctor` (see Error Recovery) |

## Sub-Agent Guidelines

- **One mining worker per session** — do not spawn multiple concurrent miners
- Use `agent-control status` to poll progress
- Use `agent-control stop` to terminate
- All platform interaction goes through `run_tool.py` — this applies to sub-agents too

## Configuration

No environment variables needed. Everything is auto-detected.

Runtime overrides (optional, via `.env` or shell):

| Variable | Default | Description |
|----------|---------|-------------|
| `PLATFORM_BASE_URL` | `https://api.minework.net` | Platform API endpoint |
| `MINER_ID` | `mine-agent` | Miner identifier |
| `WORKER_MAX_PARALLEL` | `3` | Concurrent crawl workers |

For validator settings, see `docs/ENVIRONMENT.md`.

## Advanced

Read these docs only when needed for the specific topic:

- [Browser session & login](./docs/BROWSER_SESSION.md)
- [Internal commands & rules](./docs/INTERNAL_COMMANDS.md)
- [Agent guide](./docs/AGENT_GUIDE.md)
- [Environment](./docs/ENVIRONMENT.md)
- [Validator Protocol](./references/protocol-validator.md)
