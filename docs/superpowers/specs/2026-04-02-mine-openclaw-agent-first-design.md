# Mine OpenClaw Agent-First Design

## Summary

This design reshapes the `mine` skill around the primary product goal: a user pastes a GitHub link into OpenClaw, the agent installs Mine with minimal branching, presents a clean first-run experience, and starts mining without blocking the ongoing conversation.

The current codebase already has most of the raw runtime pieces:

- bootstrap scripts
- readiness probes
- welcome and status renderers
- worker lifecycle controls
- an intent router

The product problem is not missing capability. It is that the capability is spread across too many surfaces, mixes shell commands with slash-style commands, and makes background behavior sound more complete than it currently is.

The recommended direction is an OpenClaw agent-first shell around the existing runtime. The shell should expose a very small stable command surface, return compact structured outputs for hosts, and make long-running mining explicitly background-managed rather than just described as background work in human text.

## Product Goals

1. A host agent can install Mine from a GitHub repository with one obvious path and no contradictory dependency instructions.
2. The first message shown in OpenClaw is concise, friendly, and directly actionable.
3. The main mining action runs as background work so the user can keep chatting with the agent.
4. The skill exposes a small set of short, stable agent commands instead of asking agents to assemble long shell commands.
5. OpenClaw-specific slash-style affordances are treated as presentation aliases, not as the only real interface.

## Non-Goals

1. Replacing the crawler runtime.
2. Removing wallet-based signing.
3. Solving platform-side allow-listing or `UNTRUSTED_HOST` policy issues.
4. Building a full OpenClaw plugin protocol in this phase.

## Current Product Review

### High-severity issues

1. Install guidance is inconsistent.
   `bootstrap.sh`, `bootstrap.ps1`, `README.md`, and `docs/AGENT_GUIDE.md` say `awp-wallet` should be installed from the GitHub repository. `run_tool.py doctor` and `post_install_check.py` still suggest `npm install -g @aspect/awp-wallet`. This makes the "copy GitHub link and install" story unreliable because the host can receive different next steps depending on which entrypoint it hits.

2. The public command model is too wide for host agents.
   `run_tool.py` exposes setup commands, guided UX commands, worker commands, low-level task commands, and intent helpers all at the same layer. The host must choose among `setup`, `doctor`, `first-load`, `agent-status`, `start-working`, `run-worker`, and `agent-run` with too little guidance about which are canonical.

3. Background mining is promised more clearly than it is productized.
   `render_start_working_response()` says mining "will run in a background process", but the visible public path still relies on foreground CLI invocations like `run-worker 60 0` or `agent-run`. There is no clearly documented background supervisor command with handle-based status and stop semantics for OpenClaw hosts.

### Medium-severity issues

1. Welcome copy mixes shell reality and OpenClaw presentation.
   `skill_runtime.py` presents `/mine-start`, `/mine-status`, and similar slash commands, while the real public entrypoint is `python scripts/run_tool.py ...`. This is risky in non-slash channels and confusing in any host that cannot transparently map slash aliases.

2. The first-run experience is too verbose for chat-based host UX.
   The welcome surface is informative, but it still reads like terminal help. For OpenClaw, the first message should be a short status card: readiness, blockers, next action, and optional "more info".

3. Required environment data is still too low-level.
   A host agent should not need to explain `MINER_ID`, `EIP712_*`, wallet token sourcing, and platform URL selection all at once unless the quick path fails.

### Low-severity issues

1. Some docs describe the same journey with different command examples.
2. The repo lacks a single product-facing "OpenClaw integration contract" document that defines the supported host interaction model.

## Recommended Product Direction

### Chosen approach

Adopt an `Agent-first shell` on top of the existing runtime.

Keep the crawler and runtime internals largely intact. Reshape the host-facing layer so OpenClaw and similar agents see a small set of canonical commands and structured outputs.

### Canonical host command surface

The host-facing contract should be reduced to these commands:

1. `python scripts/run_tool.py agent-status`
   Fast readiness probe. Always safe. Returns compact JSON with `ready`, `state`, `message`, `next_action`, `next_command`, and optional `details`.

2. `python scripts/run_tool.py agent-start`
   Canonical start entrypoint. Performs setup validation, guided dataset selection if needed, and starts mining through a background execution path.

3. `python scripts/run_tool.py agent-control <status|pause|resume|stop>`
   Single control surface for background sessions.

4. `python scripts/run_tool.py agent-route "<user input>"`
   Optional host helper that maps short natural language requests onto canonical commands.

Low-level commands such as `run-worker`, `run-loop`, `process-task-file`, and `export-core-submissions` remain available for internal and advanced use, but they should no longer be the recommended host path in `SKILL.md` or first-run docs.

## Interaction Design

### GitHub install journey

The target OpenClaw flow is:

1. User pastes the GitHub link.
2. OpenClaw installs the skill and runs bootstrap.
3. The host agent invokes `agent-status`.
4. If not ready, the response contains one exact next command and one concise explanation.
5. Once ready, the host agent invokes `agent-start`.
6. Mining starts in the background and the conversation stays interactive.

The host should never need to choose between multiple competing install or readiness commands during the happy path.

### First-run welcome content

The OpenClaw first-run content should render in three blocks only:

1. `Mine is ready` or `Mine needs one fix`
2. `Next action`
3. `Available actions`

Example tone:

- one sentence of welcome
- one line of readiness
- one next step
- up to three short actions

It should avoid:

- long prerequisite explanations
- simultaneous shell and slash command lists
- raw environment-variable dumps unless the user explicitly asks

### Slash commands and other message channels

Slash-style commands such as `/mine-start` should be treated as host aliases only.

The source of truth must be plain command ids and shell entrypoints:

- `agent-start`
- `agent-control status`
- `agent-control pause`
- `agent-control resume`
- `agent-control stop`

If OpenClaw supports slash aliases, it can map:

- `/mine-start` -> `agent-start`
- `/mine-status` -> `agent-control status`
- `/mine-pause` -> `agent-control pause`
- `/mine-resume` -> `agent-control resume`
- `/mine-stop` -> `agent-control stop`

This keeps the skill portable across other channels where slash commands do not exist.

## Background Execution Design

### Product requirement

Mining must not monopolize the current chat turn or trap the host in a long foreground command.

### Required behavior

`agent-start` should initiate a durable background execution path and return quickly with:

- session id
- selected dataset ids
- current state
- recommended follow-up command

`agent-control status` should query that background session and return a compact summary.

`agent-control pause`, `resume`, and `stop` should operate on the same persisted session model.

### Implementation boundary

The existing persisted worker state in `_worker_state` is a good base. This phase should add a lightweight background runner or supervisor layer rather than reworking the crawler loop itself.

### Host-visible semantics

OpenClaw should be able to say:

- "Mining is running in the background."
- "You can keep chatting while I mine."
- "I can pause, resume, or stop anytime."

Those claims should only be made once the command truly returns control while work continues elsewhere.

## Output Design

### Structured host outputs

Host-oriented commands should default to JSON with stable keys. Human-readable prose renderers should remain available for local operator use.

Required host payload fields:

- `state`
- `message`
- `next_action`
- `next_command`
- `ready`
- `session_id` when applicable
- `actions` when useful

### Human-readable outputs

Human-readable outputs such as `first-load` and `check-status` should be shortened and explicitly framed as user-facing views, not as the host integration contract.

## Error Handling

### Install failures

All install and doctor surfaces must agree on one `awp-wallet` installation source. If GitHub installation is the supported path, every fix command and document must say so.

### Missing config

The host should receive one missing prerequisite at a time, ordered as:

1. runtime not bootstrapped
2. platform URL missing
3. miner id missing
4. wallet session missing
5. platform auth or allow-list issue

### Auth and platform errors

OpenClaw-facing messages should distinguish:

1. local fixable issue
2. wallet session issue
3. platform policy issue

`UNTRUSTED_HOST` and similar allow-list problems should never be described as a local install failure.

## Documentation Changes

The following docs should be updated in implementation:

1. `SKILL.md`
   Make `agent-status` and `agent-start` the canonical path.

2. `README.md`
   Separate "operator CLI" from "host agent integration".

3. `docs/AGENT_GUIDE.md`
   Align install path, readiness checks, and background mining semantics.

4. New host integration note if needed
   Document OpenClaw aliases and the plain command contract.

## Testing Strategy

Implementation should verify:

1. bootstrap and doctor return consistent `awp-wallet` fix guidance
2. `agent-status` returns compact stable JSON across missing-config states
3. first-run welcome output stays concise and OpenClaw-safe
4. background start returns immediately and persists a resumable session handle
5. control commands work against the persisted background session
6. slash alias documentation maps correctly onto canonical commands

## Rollout Plan

Phase 1:

1. unify install guidance
2. reduce `SKILL.md` to canonical agent commands
3. tighten first-run output and agent-status payloads

Phase 2:

1. add real `agent-start` and `agent-control`
2. implement background execution semantics
3. document OpenClaw alias mapping

Phase 3:

1. optionally collapse or de-emphasize old host-facing commands
2. keep advanced runtime commands for local and debugging workflows

## Decision Summary

The product should optimize for OpenClaw agent reliability, not terminal feature breadth. The best next step is to narrow the host-facing surface, unify installation guidance, and make background mining a real capability rather than just a welcome-message promise.
