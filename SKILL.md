---
name: mine
description: OpenClaw-first autonomous mining skill for Data Mining WorkNet. Delegates crawling and extraction to social-data-crawler, signs Platform Service requests through awp-wallet, and exposes a guided mining workflow with clear status updates, recovery hints, and OpenClaw tool priorities.
metadata:
  openclaw:
    install:
      script_windows: ./scripts/install_openclaw_integration.ps1
      script_unix: ./scripts/install_openclaw_integration.sh
---

# Mine

Use this skill when the goal is to operate the OpenClaw-facing mining workflow end to end:

- start autonomous mining work
- check mining status, epoch progress, or reward state
- process task payload files
- export or submit Core payloads
- install, package, or verify the Mine OpenClaw plugin

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

**Security:** your private keys never leave awp-wallet.
Mine only uses time-limited session tokens for signing.
No seed phrase or private key should be stored in config, environment text output, or sent to the platform.

---

## Dependency check

Always present dependency results in a concrete, actionable way.
Do not say only “missing dependency” or “please install”.

### Dependencies to verify

1. **AWP Wallet**
   - installed
   - reachable on PATH or explicit config path
   - unlocked or ready to unlock

2. **social-data-crawler**
   - repository present
   - Python runtime available
   - environment bootstrapped enough to run crawler commands

3. **Platform Service base URL**
   - use plugin config `platformBaseUrl` when set
   - if the user is on the test setup, it is acceptable to explain the testnet default

### Good dependency-check success tone

- `AWP Wallet — installed, unlocked`
- `social-data-crawler — installed (Python 3.11+ ready)`
- `Platform Service base URL — configured`
- `All dependencies ready.`

### Good dependency-check failure tone

When a dependency is missing, give the user the exact next steps.

For example:

- `AWP Wallet — missing`
  - suggest install path or binary setup
- `social-data-crawler — not installed`
  - tell the user to clone the repo and bootstrap it
- Python too old
  - explicitly say Mine needs Python 3.11+
- platform base URL missing
  - explain whether Mine will use the current testnet default or needs explicit config

Always include a recovery close like:

> Run these commands, then say `check again` and I’ll re-verify.

### Required concrete guidance phrases

The skill should be able to guide with language like:

- `AWP Wallet`
- `social-data-crawler`
- `Platform Service base URL`
- `check again`

If wallet renewal is needed, it is valid to instruct:

```bash
awp-wallet unlock --duration 3600
```

---

## Runtime model

`mine` is the OpenClaw product layer.

- OpenClaw plugin root: this repository
- crawler runtime root: `D:\kaifa\clawtroop\social-data-crawler` by default
- request signing: `awp-wallet`
- platform connectivity: plugin config `platformBaseUrl`

Mine should feel like a guided product, not a loose collection of tools.

---

## OpenClaw tool priority

When choosing tools, prefer this order:

1. **`mine_worker`** — recommended default
   - primary autonomous worker
   - best choice for normal mining work

2. **`mine_run_once`**
   - debug or single-pass execution
   - good when validating one cycle

3. **`mine_process_task_file`**
   - use when a local payload JSON is already available
   - useful for offline or claim-bypassed execution

4. **`mine_heartbeat`**
   - use when only heartbeat verification is needed

5. **`mine_run_loop`**
   - use when the caller explicitly wants repeated loop execution

6. **`mine_export_core_submissions`**
   - use for conversion/export workflows only

Do not make the user infer this order.
If the user is vague, prefer `mine_worker`.

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

If signing requests fail because the wallet session is stale or expired:

- explain that the session token likely expired
- suggest or run:

```bash
awp-wallet unlock --duration 3600
```

Do not describe this as just “retry signing”.

### 429 rate limiting

If the platform returns `429`:

- say that rate limiting happened
- cool down the affected dataset
- continue with other eligible work if available
- surface the retry window if known

### AUTH_REQUIRED

If crawler output indicates `AUTH_REQUIRED`:

- explicitly say login or browser confirmation is needed
- move the item into pending/retry state
- tell the user what needs to be completed before retry

### Occupancy / dedup fallback

If the occupancy check endpoint is unavailable:

- do not crash the session
- treat it as a compatibility fallback when safe
- keep the user informed only if it becomes operationally important

---

## Status and settlement language

`check status` should aim to surface:

- miner health
- epoch id
- submitted count
- target count
- credit score / tier
- pending auth work
- pending submit work
- reward or settlement state if available

At epoch end, the preferred settlement UX includes:

- confirmed count
- rejected count
- reward amount
- credit-score movement

---

## Installation and packaging

Preferred install entrypoints:

- Windows: `./scripts/install_openclaw_integration.ps1`
- Unix-like: `./scripts/install_openclaw_integration.sh`

Preferred packaging entrypoint:

```bash
python scripts/build_openclaw_plugin.py
```

If the user is installing the plugin, guide them toward the installer rather than asking them to wire config by hand unless they explicitly want manual setup.
