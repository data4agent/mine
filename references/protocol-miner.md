# Miner Session Protocol

Mine maintains a persistent worker session that tracks all mining state across restarts. The session file lives at `{WORKER_STATE_ROOT}/session.json` (default: `output/agent-runs/_worker_state/session.json`).

## Session State Contract

### Persisted Fields

| Field | Type | Description |
|---|---|---|
| `mining_state` | `idle \| running \| paused \| stopped` | Current lifecycle state |
| `miner_registered` | `bool` | Set `true` after first successful heartbeat |
| `wallet_addr` | `string` | Wallet address from `awp-wallet receive` |
| `credit_score` | `number` | Current credit score from platform |
| `credit_tier` | `string` | `beginner \| limited \| normal \| good \| excellent` |
| `active_datasets` | `array` | Active dataset list from platform |
| `selected_dataset_ids` | `array` | User-selected datasets for this session |
| `epoch_id` | `string` | Current epoch identifier (e.g. `2026-04-01`) |
| `epoch_submitted` | `number` | Submissions this epoch (queried from API, not local count) |
| `epoch_target` | `number` | Target submissions this epoch (typically 80+) |
| `last_heartbeat_at` | `timestamp` | Last successful heartbeat time |
| `token_expires_at` | `timestamp` | When the current wallet session token expires |
| `last_wallet_refresh_at` | `timestamp` | Last wallet token renewal |
| `settlement` | `object` | Last settlement snapshot |
| `reward_summary` | `object` | Accumulated reward data |
| `session_totals` | `object` | Aggregate counts for this session |
| `last_summary` | `object` | Most recent batch summary |
| `last_iteration` | `object` | Most recent iteration metadata |
| `last_activity_at` | `timestamp` | Last meaningful runtime activity |
| `last_control_action` | `string` | Last control action (pause/resume/stop) |
| `last_state_change_at` | `timestamp` | When `mining_state` last changed |
| `last_wait_seconds` | `number` | Duration of last cooldown/wait |
| `stop_conditions` | `object` | Active stop condition config |
| `stop_reason` | `string \| null` | Why the session stopped |

### Transient Memory State

Not persisted to disk. Reset on restart.

| Field | Type | Description |
|---|---|---|
| `pow_challenge` | `object` | Current pending PoW challenge |
| `current_batch` | `object` | In-progress batch URLs and progress |

## Persistence Behavior

- **Atomic writes**: session state is written to a `.tmp` file first, then renamed into place. This prevents corruption on crash.
- **Single-instance lock**: a lock file prevents multiple workers from running concurrently. Stale locks are recovered based on timestamp and process liveness.
- **Periodic flush**: long-running sessions flush state periodically (not just on control changes) to minimize data loss on unexpected exit.

## State Update Triggers

| Event | Fields Updated |
|---|---|
| Start working | `mining_state`, `selected_dataset_ids`, lock acquired |
| Heartbeat success | `credit_score`, `credit_tier`, `epoch_id`, `epoch_submitted`, `epoch_target`, `last_heartbeat_at`, `miner_registered` |
| Token renewal | `token_expires_at`, `last_wallet_refresh_at` |
| Batch complete | `last_summary`, `last_iteration`, `session_totals`, `last_activity_at` |
| Epoch update | `epoch_submitted`, `epoch_target` |
| Settlement query | `settlement`, `reward_summary` |
| Pause | `mining_state = paused`, `last_control_action`, `last_state_change_at` |
| Resume | `mining_state = running`, `last_control_action`, `last_state_change_at` |
| Stop | `mining_state = stopped`, `stop_reason`, `last_control_action`, `last_state_change_at`, lock released |

## Stop Conditions

Configurable limits that terminate the session cleanly:

| Condition | Default | Description |
|---|---|---|
| `max_submissions` | `null` (unlimited) | Stop after N submissions |
| `max_errors` | `10` | Pause after N consecutive failures |
| `epoch_target_reached` | `false` | Stop when epoch target is met |
| `max_runtime_minutes` | `null` (unlimited) | Stop after N minutes of runtime |
