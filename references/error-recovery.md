# Error Recovery

## Platform

- `401 MISSING_HEADERS`: instruct wallet/session setup
- `401` expired session: renew wallet session and retry
- `404` occupancy: compatibility fallback to empty payload
- `429`: cooldown dataset and continue with other eligible work

## Runtime

- AUTH-required crawler outputs move to auth-pending
- submit failures move to submit-pending
- pause/stop requests preserve current-batch semantics in user messaging
