# Miner Session Protocol

Mine keeps a persisted worker session with:

- mining state
- selected datasets
- epoch progress
- settlement snapshot
- queue counters
- last control action
- wallet token expiry hints

Session state is updated around:

1. start-working
2. heartbeat refresh
3. per-iteration summaries
4. pause/resume/stop control changes
