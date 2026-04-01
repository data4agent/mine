# Error Recovery Reference

Mine implements structured error recovery so failures are handled automatically when possible and surfaced clearly when user action is needed.

## Platform API Errors

| Error | Meaning | Auto Recovery | User Message |
|---|---|---|---|
| `401` + `MISSING_HEADERS` | EIP-712 signature not configured | None — fatal | "Platform requires Web3 signatures. Run `awp-wallet unlock --duration 3600` and configure `AWP_WALLET_TOKEN`." |
| `401` + token expired | `awp-wallet` session expired | Auto-renew: call `awp-wallet unlock --duration 3600`, update token, retry | "Session auto-renewed." |
| `401` + signature invalid | Signature mismatch | Re-sign and retry once | Notify only on second failure |
| `403` | No permission | Do not retry | "Your wallet `{addr}` does not have mining permission for this dataset." |
| `404` + dataset | Dataset does not exist or is archived | Do not retry | "Dataset `{id}` not found or archived. Skipped." |
| `404` + url-occupancy | Dedup endpoint not implemented | **Graceful fallback**: treat as "unoccupied" | Silent — log only |
| `404` + status/settlement/reward | Endpoint not available upstream | Return empty data | Degrade gracefully, no error surfaced |
| `409` | Duplicate submission | Skip the URL | Silent — log only |
| `429` | Rate limited | Wait `Retry-After`, cooldown dataset, rotate to next | "Rate limited on `{dataset}`. Waiting `{N}s`, continuing with other datasets." |
| `500+` | Server error | Exponential backoff, retry up to 3 times | After 3 failures: "Platform service error. Pausing 5 minutes before retry." |
| Network timeout | Connection failed | Exponential backoff, retry up to 3 times | After 3 failures: "Network connection failed. Check connectivity." |

## Crawler Errors

| Scenario | `summary.json` Status | Recovery |
|---|---|---|
| All records succeed | `status: success` | Proceed to submission |
| Partial failure | `status: partial_success` | Submit successful records; queue failed ones for next batch retry |
| All records fail | `status: failed` | Log error, skip batch, notify user |
| Subprocess crash | Non-zero exit code | Read `errors.jsonl`, notify user, continue with next batch |
| `AUTH_REQUIRED` | `error_code` field | Pause mining loop. Tell user: "Login needed for `{platform}`. Complete authentication, then say `resume`." |
| `AUTH_EXPIRED` | `error_code` field | Auto-refresh session, retry once |

## PoW Errors

| Scenario | Recovery |
|---|---|
| Answer rejected | Re-request challenge, retry once |
| Challenge timeout | Re-request challenge |
| LLM format error | Re-generate answer, up to 2 retries |
| 3 consecutive PoW failures | Pause and notify: "PoW verification failing repeatedly. Check LLM configuration." |

## Wallet / Session Recovery

When the agent detects that signing requests are failing due to an expired or invalid session:

1. Explain that the session token has expired.
2. Auto-renew if `WalletSigner.renew_session()` is available.
3. If auto-renewal fails, instruct the user:

```bash
awp-wallet unlock --duration 3600
```

4. After renewal, say "check again" or "resume" to continue.

Do not describe this generically as "retry signing". Be specific about what expired and what the user must do.

## Recovery Principles

- **Finish current batch** before any pause/stop takes effect.
- **One dataset failure does not block others.** Cooldown and rotate.
- **Surface actionable messages.** Never say just "error occurred" — explain what failed and what the user should do.
- **Log everything.** Even silent fallbacks should be recorded in the run artifacts.
- **Bounded retries.** Never retry indefinitely. After max retries, pause and notify.
