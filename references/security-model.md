# Security Model

Mine is designed so that private keys never leave the local wallet. All platform interactions use time-limited session tokens for signing.

## Key Principles

1. **Private keys stay in awp-wallet.** Mine never reads, stores, or transmits seed phrases or private keys. All signing happens through the `awp-wallet` CLI subprocess.

2. **Session tokens are time-limited.** The default session duration is 3600 seconds (1 hour). Tokens are auto-renewed before expiry during long-running mining sessions.

3. **EIP-712 typed data signing.** Every platform API request is signed using the EIP-712 standard with domain `Platform Service` version `1`. The signed message includes method, host, path, query hash, headers hash, body hash, nonce, and timestamps.

4. **No secrets in config files.** `mine.json`, environment variables, and runtime config should never contain raw private keys or seed phrases. Only session tokens (which expire) and public wallet addresses are stored.

5. **No secrets in output.** Runtime logs, status summaries, and error messages must not leak private keys, session tokens, or wallet mnemonics. Token values are referenced by name, not printed in full.

## Wallet Interaction

Mine interacts with `awp-wallet` through subprocess calls:

| Command | Purpose |
|---|---|
| `awp-wallet receive` | Get the wallet address |
| `awp-wallet unlock --duration 3600` | Create a time-limited session token |
| `awp-wallet sign-typed-data --token <token> --data <json>` | Sign an EIP-712 typed data message |

The session token is passed via `--token` flag, not stored in files. Mine sets `AWP_WALLET_TOKEN` in the process environment for convenience but this is per-process and not written to disk.

## Token Lifecycle

1. **Initial unlock**: the user runs `awp-wallet unlock --duration 3600` before starting mining, or Mine prompts for it during dependency check.
2. **Proactive renewal**: during `run-worker`, the runtime checks `token_expires_at` and calls `renew_session()` when expiry is within 5 minutes.
3. **Reactive renewal**: if a `401` with `TOKEN_EXPIRED` or `SESSION_EXPIRED` is received, the runtime attempts one auto-renewal before surfacing the error.
4. **User recovery**: if auto-renewal fails, the user is instructed to run `awp-wallet unlock --duration 3600` manually.

## What NOT to Do

- Never store `AWP_WALLET_TOKEN` in `.env` files that might be committed.
- Never print the full session token in user-facing output.
- Never pass private keys as command arguments or environment variables.
- Never log the `X-Signature` header value in user-facing summaries.
- Never commit `session.json` or `mine.json` to version control if they contain tokens.

## Wallet Address and Miner ID

- **Wallet address**: derived from `awp-wallet receive`. This is the public Ethereum address used for signing.
- **Miner ID**: set via the `MINER_ID` environment variable. This is the platform-assigned identifier for the mining account.
- **Relationship**: a Miner ID is associated with a wallet address on the platform side. The wallet address proves ownership through EIP-712 signatures. One wallet can be associated with one Miner ID.
