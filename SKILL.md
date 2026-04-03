---
name: mine
description: Agent-first mining skill for signed platform work, crawler execution, and submission export through awp-wallet.
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

Local mining skill entry for agents. OpenClaw and other **plugin hosts** should load this skill from the repository root.

Principles:

- Infer user intent before running internal commands
- Return action semantics to the user; do not dump low-level commands by default
- Treat `scripts/run_tool.py` as the internal control plane, not conversational UX
- Prefer the host-friendly background mining path; do not expose low-level worker commands first

## Agent Actions

Standard actions exposed by this skill:

| Action | When to use | Expected outcome |
| ----- | -------- | -------- |
| `Initialize` | First run, environment not initialized, wallet unavailable | Install deps, prepare wallet, finish setup |
| `CheckReadiness` | User asks whether they can start or what the status is | Return readiness and next action |
| `StartMining` | User wants to start mining | Enter background mining session |
| `CheckStatus` | User asks about progress, current state, or whether it is running | Return session / epoch / action |
| `PauseMining` | User wants to pause | Pause current mining session |
| `ResumeMining` | User wants to resume | Resume a paused session |
| `StopMining` | User wants to stop | End session and keep summary |
| `Diagnose` | User reports errors, 401, cannot start, odd state | Return structured diagnosis and fixes |
| `PrepareBrowserSession` | Crawl tasks need browser work, missing login, need cookies / storage state | Prepare a usable session and write it back |

Prefer these action names or natural language, for example:

- “Initialize mining environment”
- “Check if ready”
- “Start mining”
- “Check status”
- “Pause mining”
- “Resume mining”
- “Stop mining”
- “Diagnose issues”
- “Prepare browser session”

Use internal command mapping only when the user explicitly wants low-level commands or the host must execute the mapping.

## Preferred Flow

Typical conversation flow:

1. Run `CheckReadiness` first
2. If not initialized, run `Initialize`
3. Run `CheckReadiness` again after initialization
4. When ready, run `StartMining`
5. Then control via `CheckStatus` / `PauseMining` / `ResumeMining` / `StopMining`
6. If a platform requires an authenticated browser during crawl, run `PrepareBrowserSession` and retry the task

If the user only asks whether they can mine or wants status, do not start mining—use `CheckReadiness` or `CheckStatus` first.

## Readiness States

`CheckReadiness` and `Diagnose` share the same readiness semantics:

| State | can_diagnose | can_start | can_mine | Meaning |
| ----- | ------------ | --------- | -------- | ------- |
| `ready` | true | true | true | Fully usable |
| `registration_required` | true | true | false | Can start; registration runs on start |
| `auth_required` | true | false | false | Wallet session missing or expired |
| `agent_not_initialized` | false | false | false | awp-wallet or runtime not ready |
| `degraded` | true | true | false | Partially usable |

Common warnings:

- `wallet session expired`
- `wallet session expires in Ns`
- `using fallback signature config`

## Behavior Rules

1. Prefer the background session path; do not call low-level `run-worker` first
2. Prefer returning “current state + next action” instead of a list of commands
3. When runtime returns `selection_required`, interpret it as “user must choose a dataset”; do not invent a choice
4. When runtime returns `auth_required` or `401`, prefer `Diagnose` or `Initialize`
5. `StopMining` has side effects; confirm if the user’s intent is unclear
6. Browser or LinkedIn auto-login applies only in those scenarios—not a global prerequisite for this skill
7. For browser login, cookies, or storage state export, prefer `PrepareBrowserSession`; do not have the agent stitch low-level browser commands manually

## Browser Session Policy

When mining or crawl tasks need browser work, cookies, or storage state, follow this priority:

1. Reuse an existing session file first
2. If a reusable browser session exists locally, export it quietly without interrupting the user
3. If none, launch the browser and open the platform login page
4. After session is ready, export session and retry the original task automatically
5. Only escalate to the user for CAPTCHA, risk controls, SMS verification, or explicit human confirmation

Preferred automation:

- Prefer `auto-browser` session bridging
- `agent-browser` is the driver layer for open/wait/export
- Do not expose `vrd.py` / `agent-browser` command chains to the user
- Treat browser session as one high-level action, not many commands

Automation boundaries:

- The agent should automatically: launch browser, open login, wait for session, export session, import cookies, retry crawl
- The agent should not stop by default only because “a browser is needed” or “cookies are missing”
- The agent should stop for: CAPTCHA, SMS, forced human confirmation, risk pages, or export timeout

Success means a valid session, not merely a loaded page. For LinkedIn, key cookies present is the main success signal.

## Browser Flow Simplification

Do not recommend this multi-step manual path in the skill:

- `vrd.py check`
- `vrd.py start`
- `vrd.py status`
- `agent-browser open ...`
- `vrd.py export-session ...`

Fold those into one action:

- `PrepareBrowserSession(platform)`

The goal is not “open a browser” but “obtain a usable session and continue.” If session can be obtained automatically, do not show intermediate commands.

## Internal Command Mapping

Host/agent internal mapping—not the primary user-facing output:

| Action | Internal command |
| ---- | -------- |
| `Initialize` | `python scripts/run_tool.py init` |
| `CheckReadiness` | `python scripts/run_tool.py agent-status` |
| `StartMining` | `python scripts/run_tool.py agent-start` |
| `CheckStatus` | `python scripts/run_tool.py agent-control status` |
| `PauseMining` | `python scripts/run_tool.py agent-control pause` |
| `ResumeMining` | `python scripts/run_tool.py agent-control resume` |
| `StopMining` | `python scripts/run_tool.py agent-control stop` |
| `Diagnose` | `python scripts/run_tool.py doctor` |
| `PrepareBrowserSession` | Use the runtime auto-browser session export flow; do not require the agent to run `vrd.py` / `agent-browser` manually |

Advanced capabilities still exist but must not override the main contract, for example:

- `process-task-file`
- `export-core-submissions`
- `run-worker`
- `agent-run`
- `first-load`
- `list-datasets`

## Bootstrap

Bootstrap installs dependencies, prepares `awp-wallet`, and establishes a local wallet session.

- Unix: `./scripts/bootstrap.sh`
- Windows: `./scripts/bootstrap.cmd`

If the host supports platform-specific bootstrap, use the `bootstrap` / `windows_bootstrap` fields in frontmatter instead of asking the user to type commands.

## Environment (defaults work)

```bash
PLATFORM_BASE_URL=http://101.47.73.95   # testnet default
MINER_ID=mine-agent                      # default
AWP_WALLET_BIN=awp-wallet               # auto-detected
```

EIP-712 signature config is auto-fetched from platform; falls back to built-in defaults if unreachable.

## Optional Capability

`auto-browser` is for LinkedIn / browser login scenarios that need a visible local browser. It is not a global hard dependency and must not block generic mining init, status checks, or background runs.

If a visible local browser is available, prefer it for login and session export; in remote/VRD scenarios, use the same session export entry points from `auto-browser`. The agent should still see one high-level action: `PrepareBrowserSession`.

## Reference

- [`docs/AGENT_GUIDE.md`](./docs/AGENT_GUIDE.md)
- [`docs/ENVIRONMENT.md`](./docs/ENVIRONMENT.md)
- [`README.md`](./README.md)
