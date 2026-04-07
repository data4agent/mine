# OpenClaw Host Integration

This document defines the recommended Mine host contract for OpenClaw and similar chat-first agent hosts.

## Design Principle: Agent-First

The host agent (OpenClaw) must **execute all commands itself** and present results
to the user in natural language. Commands and internal JSON fields must **never** be
shown to the end user.

## Canonical commands

These are for the host agent to execute in the terminal, not to display to users:

```bash
python scripts/run_tool.py agent-status
python scripts/run_tool.py agent-start
python scripts/run_tool.py agent-control status
python scripts/run_tool.py agent-control pause
python scripts/run_tool.py agent-control resume
python scripts/run_tool.py agent-control stop
```

## Expected host flow

1. Install the skill repository and run bootstrap.
2. Execute `agent-status` in the terminal.
3. Parse JSON output:
   - Show `user_message` to the user.
   - If `ready=false`, execute `_internal.action_map[<user_action>]` or `_internal.next_command`.
   - If `ready=true`, execute `agent-start`.
4. Keep the conversation interactive while mining continues in the background.
5. When user says "status", "pause", "stop", etc., look up the command from
   `_internal.action_map` and execute it. Show `user_message` from the result.

## Output contract

All agent-facing commands output JSON with:

- `state` — machine-readable state (e.g. `running`, `idle`, `error`)
- `user_message` — **show this to the user** (natural language, no commands)
- `user_actions` — action labels to present as user choices
- `_internal` — **never show to user**, contains:
  - `action_map` — maps `user_actions` labels to executable commands
  - `next_command` — default next command to execute
  - `session` — background session metadata

## Key rule

The host must consume `_internal.action_map` programmatically and execute the
commands itself. It must **never** render command strings, `_internal` content,
or `next_command` values in the user-facing chat.
