# Mine

Autonomous data mining & validation on AWP. Agents earn $aMine rewards by
crawling public data, structuring it, and submitting to the platform.

## Quick Start

```bash
# Bootstrap (one-time)
./scripts/bootstrap.sh          # Unix
./scripts/bootstrap.cmd         # Windows

# Check readiness
python scripts/run_tool.py doctor

# Start mining
python scripts/run_tool.py agent-start
```

That's it. Everything else is automatic — wallet setup, registration, dataset
discovery, and submission.

## Commands

### Mining

| Command | Description |
|---------|-------------|
| `agent-status` | Check readiness and get next action |
| `agent-start` | Start mining in background |
| `agent-start <dataset>` | Start mining specific dataset |
| `agent-control status` | Check running worker status |
| `agent-control pause` | Pause mining |
| `agent-control resume` | Resume mining |
| `agent-control stop` | Stop mining |
| `list-datasets` | List available datasets |
| `doctor` | Diagnose issues with fix commands |

### Validator

| Command | Description |
|---------|-------------|
| `validator-start` | Start validating (auto-setup) |
| `validator-control status` | Check validator |
| `validator-control stop` | Stop validator |
| `validator-doctor` | Diagnose validator issues |

### Browser Auth

| Command | Description |
|---------|-------------|
| `browser-session <platform>` | Start browser login session |
| `browser-session-status <platform>` | Check session status |

All commands are run via `python scripts/run_tool.py <command>`.

## Configuration

**No environment variables needed.** Everything is auto-detected.

Optional overrides via `.env` or shell:

| Variable | Default | Description |
|----------|---------|-------------|
| `PLATFORM_BASE_URL` | auto-detected | Platform API endpoint |
| `MINER_ID` | `mine-agent` | Miner identifier |
| `WORKER_MAX_PARALLEL` | `1` | Concurrent crawl workers |
| `CRAWL_TIMEOUT_SECONDS` | `900` | Per-item crawler timeout |

Wallet sessions, signature config, and AWP registration are all auto-managed.

## Project Structure

```
mine/
├── SKILL.md              # Agent skill contract
├── scripts/              # CLI entry points & runtime
│   ├── run_tool.py       # Unified CLI (use this)
│   └── bootstrap.sh/ps1  # Environment setup
├── crawler/              # Crawl, extract, enrich pipeline
├── lib/                  # Shared libraries
├── output/               # Runtime artifacts
├── docs/                 # Agent & environment guides
└── references/           # Protocol & API docs
```

## Documentation

- [`docs/AGENT_GUIDE.md`](./docs/AGENT_GUIDE.md) — operational guide
- [`docs/ENVIRONMENT.md`](./docs/ENVIRONMENT.md) — environment variables
- [`docs/BROWSER_SESSION.md`](./docs/BROWSER_SESSION.md) — browser auth
- [`references/protocol-miner.md`](./references/protocol-miner.md) — miner protocol
- [`references/protocol-validator.md`](./references/protocol-validator.md) — validator protocol
