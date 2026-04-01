---
name: mine
description: Agent-first autonomous mining skill for Data Mining WorkNet. Uses the built-in Mine runtime for crawling, enrichment, schema handling, and submission signing through awp-wallet, and exposes a guided mining workflow with clear status updates, recovery hints, and portable command entrypoints that work across agents.
bootstrap: ./scripts/bootstrap.sh
windows_bootstrap: ./scripts/bootstrap.ps1
smoke_test: ./scripts/smoke_test.py
requires:
  skills:
    - browse
    - auto-browser
  bins:
    - python3
    - awp-wallet
  anyBins:
    - python
    - py
  env:
    - PLATFORM_BASE_URL
    - MINER_ID
---

# Mine

Use this skill when the goal is to operate the Mine mining workflow end to end:

- start autonomous mining work
- check mining status, epoch progress, or reward state
- process task payload files
- export or submit Core payloads
- bootstrap or verify the local Mine runtime

---

## Quick Setup (Recommended for Agents)

The simplest way to get Mine working is to use the setup wizard. All output is structured JSON for easy parsing.

### One-Shot Setup

```bash
python scripts/run_tool.py setup
```

This single command:
1. Checks Python version (needs 3.11+)
2. Creates virtualenv and installs dependencies
3. Initializes agent identity (automatic)
4. Sets environment variables
5. Returns JSON with status and next command

### Quick Diagnosis

```bash
python scripts/run_tool.py doctor
```

Returns JSON with:
- All checks (python, env_vars, agent identity)
- Exact fix commands to copy-paste
- Next command to run

Example output:
```json
{
  "status": "error",
  "checks": [...],
  "fix_commands": [
    "export PLATFORM_BASE_URL=http://101.47.73.95"
  ],
  "next_command": "export PLATFORM_BASE_URL=http://101.47.73.95"
}
```

### Auto-Fix

```bash
python scripts/run_tool.py setup-fix
```

Attempts to automatically fix common issues (create venv, install deps, set defaults).

---

## Agent Integration (For Weak Models)

If you are an AI agent with limited context or reasoning capability, use this simplified flow:

### Step 1: Check Status (One Command)

```bash
python scripts/run_tool.py agent-status
```

Returns ultra-concise JSON:
```json
{"ready": true, "state": "ready", "message": "Ready to mine", "next_action": "Start mining", "next_command": "python scripts/run_tool.py run-worker 60 1"}
```

Or if not ready:
```json
{"ready": false, "state": "env_missing", "message": "PLATFORM_BASE_URL not set", "next_action": "export PLATFORM_BASE_URL=http://101.47.73.95", "next_command": null}
```

### Step 2: Follow `next_action`

- If `ready` is `false`: execute `next_action` (it's a shell command)
- If `ready` is `true`: execute `next_command` to start mining

### Step 3: Loop

After each action, run `agent-status` again to check the new state.

### Decision Tree for Weak Agents

```
START
  |
  v
agent-status --> ready=true? --> YES --> run next_command --> MINING
                    |
                    NO
                    |
                    v
              Execute next_action
                    |
                    v
              agent-status (loop back)
```

### One-Shot Mining (Simplest)

For the simplest possible integration, use `agent-run` which handles everything:

```bash
python scripts/run_tool.py agent-run 1
```

This single command:
1. Auto-unlocks wallet if needed
2. Sends heartbeat
3. Returns structured JSON with all events

Example success:
```json
{"success": true, "message": "Completed 1 iteration(s)", "events": [...]}
```

Example failure:
```json
{"success": false, "error": "auth_failed", "message": "401 Unauthorized", "events": [...]}
```

### Key Rules for Agents

1. **Always start with `agent-status`** — never guess the state
2. **One action at a time** — don't chain multiple commands
3. **Trust the `next_action`** — it tells you exactly what to do
4. **Re-check after each action** — state may have changed
5. **If stuck after 3 retries** — report the error to the user, don't keep trying

### Minimum Agent Requirements

- Must reliably execute shell commands (no hallucinating results)
- Must parse JSON output correctly
- Must follow sequential instructions

Models below Haiku/GLM-4 level may struggle. See the review document for detailed capability assessment.

---

## Command entrypoint

All runtime actions should go through `scripts/run_tool.py`.

### Setup Commands (JSON output, for agents)

- `python scripts/run_tool.py setup` — Full setup wizard
- `python scripts/run_tool.py setup-status` — Check setup status
- `python scripts/run_tool.py setup-fix` — Auto-fix issues
- `python scripts/run_tool.py doctor` — Quick diagnosis with fix commands

### Main Commands

- `python scripts/run_tool.py first-load`
- `python scripts/run_tool.py start-working`
- `python scripts/run_tool.py check-status`
- `python scripts/run_tool.py list-datasets`
- `python scripts/run_tool.py run-worker`
- `python scripts/run_tool.py run-once`
- `python scripts/run_tool.py heartbeat`
- `python scripts/run_tool.py process-task-file <taskType> <taskJsonPath>`
- `python scripts/run_tool.py export-core-submissions <inputPath> <outputPath> <datasetId>`

This keeps `mine` portable across agents without requiring a plugin host.

---

## First-load experience contract

When this skill loads for the first time, the preferred user experience is:

1. show a short welcome
2. show a security note
3. run a dependency check
4. give 3 clear quick-start actions
5. avoid overwhelming the user with low-level implementation detail

Use this exact interaction style or something better:

### Welcome

**Welcome to Mine** — the data service WorkNet.

Your agent mines the internet for structured data and earns `$aMine`.
Crawl, clean, structure, submit — with the agent handling the workflow for you.

### Quick start

- `start working` — begin autonomous mining
- `check status` — see credit score, epoch status, and reward-related state
- `list datasets` — inspect active datasets before starting

End the first-load message with:

> Or just tell me what you'd like to do.

### Security

**Security:** The agent uses its own wallet for signing requests. Wallet management is automatic — you don't need to configure or unlock anything. All request signing happens locally, and private keys never leave the agent's secure environment.

---

## Dependency check

### Version check

Always surface version readiness as its own explicit check before long-running mining work:

1. `Mine runtime version`
   - current project checkout is the active runtime surface
2. `Python version`
   - Mine needs Python 3.11+
3. `Agent identity`
   - agent wallet is initialized and ready for signing

Good version-check tone:

- `Mine runtime version — project checkout ready`
- `Python version — 3.11+ ready`
- `Agent identity — ready`

Always present dependency results in a concrete, actionable way.
Do not say only “missing dependency” or “please install”.

### Dependencies to verify

1. **Mine runtime**
   - runtime present inside this project
   - Python runtime available (3.11+)
   - environment bootstrapped enough to run Mine crawler commands

2. **Agent identity**
   - agent wallet initialized (automatic, no user action needed)
   - signing ready

3. **Platform Service base URL**
   - use environment variable `PLATFORM_BASE_URL` when set
   - if on testnet, the default URL is acceptable

### Good dependency-check success tone

- `Mine runtime — installed (Python 3.11+ ready)`
- `Agent identity — ready`
- `Platform Service — configured`
- `All dependencies ready.`

### Good dependency-check failure tone

When a dependency is missing, give actionable guidance.

For example:

- `Mine runtime — not ready`
  - tell the user to bootstrap this project runtime
- Python too old
  - explicitly say Mine needs Python 3.11+
- Platform base URL missing
  - explain that Mine needs `PLATFORM_BASE_URL` configured

Always include a recovery close like:

> Run these commands, then say `check again` and I’ll re-verify.

Note: Agent wallet issues are handled automatically. If signing fails, the agent will attempt to recover on its own.

---

## Intent routing

When the user expresses an intent, route to the matching action and command.

| Intent | Action | Command | Confirm? |
| --- | --- | --- | --- |
| Start autonomous mining | **A1** | `python scripts/run_tool.py start-working` | First run: yes |
| Check miner status / credit score | **Q1** | `python scripts/run_tool.py check-status` | No |
| List active datasets | **Q2** | `python scripts/run_tool.py list-datasets` | No |
| Check epoch progress | **Q3** | `python scripts/run_tool.py check-status` | No |
| Check submission history | **Q4** | `python scripts/run_tool.py check-status` | No |
| Check mining log | **Q5** | read `output/agent-runs/` artifacts | No |
| Answer PoW challenge | **M1** | handled within `run-worker` / `run-once` | No |
| Check dedup availability | **M2** | handled within `run-worker` / `run-once` | No |
| Configure mining preferences | **C1** | environment variables or `mine.json` | — |
| Pause / resume mining | **A2** | `python scripts/run_tool.py pause` / `resume` | No |
| Stop mining | **A3** | `python scripts/run_tool.py stop` | Yes |

### Routing rules

- If the user is vague or says "start", route to **A1**.
- If the user asks about status, credit, epoch, or rewards, route to **Q1**/**Q3**.
- If the user says "pause", "stop", or "resume", route to **A2**/**A3** directly.
- **A3** (stop) always requires user confirmation before executing.
- **M1** and **M2** are internal workflow steps, not user-facing commands. They run automatically during **A1**.
- For **C1**, guide the user through environment variables (`MINE_CONFIG_PATH`, stop conditions) rather than exposing raw config files.

---

## Runtime model

`mine` is the primary skill/runtime project.

- crawler runtime root: this repository by default
- request signing: handled by agent wallet (automatic)
- platform connectivity: `PLATFORM_BASE_URL`
- discovery may use `generic` or `generic/page` inputs as compatibility fallbacks when needed

Mine should feel like a guided product, not a loose collection of tools.

---

## Command priority

When choosing runtime commands, prefer this order:

1. `python scripts/run_tool.py run-worker`
   - primary autonomous worker
   - best choice for normal mining work

2. `python scripts/run_tool.py run-once`
   - debug or single-pass execution
   - good when validating one cycle

3. `python scripts/run_tool.py process-task-file`
   - use when a local payload JSON is already available
   - useful for offline or claim-bypassed execution

4. `python scripts/run_tool.py heartbeat`
   - use when only heartbeat verification is needed

5. `python scripts/run_tool.py run-loop`
   - use when repeated loop execution is explicitly requested

6. `python scripts/run_tool.py export-core-submissions`
   - use for conversion/export workflows only

Do not make the user infer this order.
If the user is vague, prefer `python scripts/run_tool.py run-worker`.

---

## Start-working experience

The target UX for `start working` is:

1. confirm heartbeat and registration state
2. show current credit score / tier if available
3. show current epoch and time remaining if available
4. discover active datasets
5. let the user choose datasets on first run if multiple are available
6. confirm the plan before starting the long-running workflow

Good confirmation language:

- `Mining wiki-articles + arxiv-papers.`
- `Target: 80 submissions this epoch.`
- `Say pause or stop anytime.`

---

## Progress feedback contract

Mine should provide visible progress through the full pipeline.
Do not let the user sit through a long black box.

Preferred stage language:

- `finding URLs`
- `dedup check`
- `preflight`
- `PoW`
- `crawling`
- `structuring`
- `submitting`

Batch-level updates are preferred over silence.

At the end of a batch, show a compact status summary:

- records discovered
- records crawled successfully
- records failed
- records structured
- records submitted

If possible, also show epoch progress and basic forecast information.

---

## Control language

Mine should support clear control semantics:

- `pause`
- `resume`
- `stop`

### Pause

Preferred behavior:

- finish the current batch
- save state
- report session progress

### Resume

Preferred behavior:

- restore saved state
- confirm restored epoch progress
- continue from the next batch

### Stop

Preferred behavior:

- finish the current batch
- stop starting new work
- return a session summary

Always explain that the **current batch** is finished before pausing or stopping.

---

## Error recovery guidance

Mine should feel resilient and specific.

### Token/session recovery

If signing requests fail because the agent's session is stale or expired:

- the agent will automatically attempt to renew the session
- if auto-renewal fails, report a brief error and retry
- do not expose wallet commands to the user — signing is the agent's internal concern

### 429 rate limiting

If the platform returns `429`:

- say that rate limiting happened
- cool down the affected dataset
- continue with other eligible work if available
- surface the retry window if known

### AUTH_REQUIRED (Auto-Login Flow)

When crawler returns `AUTH_REQUIRED`, use the simplified auth helper scripts.

All dependencies (Xvfb, x11vnc, websockify, icewm, xdotool, agent-browser, Chrome, cloudflared) are auto-installed on first use.

#### Usage

##### Step 1: Request login

```bash
# Extract domain from failed URL (e.g., "linkedin.com" from "https://www.linkedin.com/...")
PUBLIC_URL=$(bash auto-browser/scripts/auth_helper.sh <platform_domain>)
```

This script:

- Tries to import existing cookies (silent)
- If no cookies: starts VNC stack and opens login page
- Returns the Cloudflare public URL for user access

Output to user (one line only):

```text
Login needed: $PUBLIC_URL
```

##### Step 2: Wait for user to complete login

The user will:

1. Click the PUBLIC_URL link
2. Log in through the browser
3. Click "Done" button in the VNC interface, OR say "done" in chat

##### Step 3: Complete login flow

After user says "done" / "finished" / "completed":

```bash
bash auto-browser/scripts/auth_complete.sh --wait-user
```

This captures cookies and returns control to the crawler.

**Output:** `Logged in. Resuming.`

Then retry the failed URLs.

#### Cleanup

```bash
python3 auto-browser/scripts/vrd.py stop
```

Run this when mining session is complete (not after each login).

#### Rules

- Use helper scripts, not raw commands
- Never ask user to manually export cookies
- Never output cookie values or auth details
- Only output the PUBLIC_URL
- Auto-retry failed URLs after successful login

### Occupancy / dedup fallback

If the occupancy check endpoint is unavailable or returns 404:

- do not crash the session
- treat the URL as available and proceed with crawling (optimistic fallback)
- log the fallback internally but do not alarm the user unless it affects >10% of URLs in a batch
- this is expected behavior during platform upgrades or when the endpoint is not yet deployed

---

## Bootstrap and verification

Preferred local checks:

- `./scripts/bootstrap.sh`
- `./scripts/bootstrap.cmd`
- `python scripts/verify_env.py --profile minimal --json`
- `python scripts/host_diagnostics.py --json`
- `python scripts/smoke_test.py --json`

If the user needs environment setup help, guide them toward bootstrapping the local Python runtime. The agent wallet is initialized automatically during bootstrap.

---

## FAQ

### Gas fees

**Q: Does submitting data require gas fees?**

A: No. Data submissions to the Platform Service are off-chain API calls. You do not need ETH in your wallet to submit crawled data.

**Q: Does claiming $aMine rewards require gas?**

A: Reward claiming may require on-chain transactions depending on the platform's settlement mechanism. Check the platform documentation for current settlement details. During testnet, rewards are tracked off-chain.

**Q: Do I need ETH or any crypto to mine?**

A: No. The mining workflow is entirely off-chain. The agent handles all request signing automatically. Gas is only needed if you later bridge rewards or perform on-chain operations.

### Agent Identity and Miner ID

**Q: What is the relationship between agent identity and Miner ID?**

A: They are separate identifiers:

- **Agent wallet** (`0x...`) — The agent's cryptographic identity for request signing. Managed automatically by the agent.
- **Miner ID** — A human-readable identifier for your mining client (e.g., `my-miner-001`). Used by the platform to track your submissions, credit score, and rewards.

**Q: Can one agent run multiple miners?**

A: Yes. You can run multiple mining clients with different Miner IDs. Each Miner ID maintains its own credit score and submission history.

**Q: Do I need to manage the agent's wallet?**

A: No. The agent's wallet is initialized and managed automatically during bootstrap. You don't need to configure, unlock, or interact with it directly.

### PoW challenges

**Q: What types of PoW challenges are supported?**

A: The current solver supports:

| Type | Description | Implementation |
|------|-------------|----------------|
| `content_understanding` | LLM-answerable questions | Requires Mine Gateway LLM |
| `structured_extraction` | Schema-based extraction | Requires Mine Gateway LLM |
| `math` / `arithmetic` | Basic math expressions | Local evaluation |
| `sha256_nonce` / `hashcash` | Hash prefix mining | Local computation |

**Q: What happens if a challenge type is unsupported?**

A: The item is skipped with status `challenge_received_but_unsolved`. It will not block other work.

**Q: How do LLM-based challenges work?**

A: They route through the Mine Gateway (`OPENCLAW_GATEWAY_BASE_URL`). If the gateway is not configured, LLM challenges will fail. Configure the gateway in your environment or `mine.json` for full PoW support.

**Q: What is the roadmap for PoW?**

A: Current implementation handles the most common challenge types. Additional types may be added as the platform evolves. The solver is designed to be extensible — new challenge handlers can be added to `pow_solver.py`.

### Network selection

**Q: How do I choose between testnet and mainnet?**

A: Set `PLATFORM_BASE_URL` explicitly:

- **Testnet:** `http://101.47.73.95`
- **Mainnet:** TBD (will be announced when available)

The install script no longer defaults to testnet. You must explicitly choose your network.

**Q: What happens if I forget to set the URL?**

A: The worker will fail with a clear error asking you to set `PLATFORM_BASE_URL`. This prevents accidental connections to the wrong network.
