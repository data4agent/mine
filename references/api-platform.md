# Platform API Reference

Mine communicates with the AWP Platform Service through signed HTTP requests. All mutable endpoints require EIP-712 signatures via `awp-wallet`.

## Base URL

Set via `PLATFORM_BASE_URL`. The testnet default is `http://101.47.73.95`.

## Authentication

Every request carries these headers when a `WalletSigner` is configured:

| Header | Purpose |
|---|---|
| `X-Signer` | Wallet address |
| `X-Signature` | EIP-712 signature |
| `X-Nonce` | Random 52-bit integer |
| `X-Issued-At` | Unix timestamp (seconds) |
| `X-Expires-At` | `issuedAt + 60` |
| `X-Chain-Id` | Chain ID (default `1`) |
| `X-Signed-Headers` | `content-type,x-request-id` |
| `Authorization` | `Bearer <PLATFORM_TOKEN>` when available |

The signed message type is `APIRequest` with domain `Platform Service` version `1`.

## Endpoints

### Heartbeat

```
POST /api/mining/v1/heartbeat
Body: { "client": "<client_name>", "ip_address": "" }
```

Unified heartbeat. Returns miner registration state, credit score, epoch info.

```
POST /api/mining/v1/miners/heartbeat
Body: { "client": "<client_name>" }
```

Miner-specific heartbeat.

### Datasets

```
GET /api/core/v1/datasets
```

Returns `{ "data": [ ... ] }` or `{ "data": { "items": [ ... ] } }`. Each item has `id`, `name`, `schema`, and epoch metadata.

```
GET /api/core/v1/datasets/{datasetId}
```

Single dataset detail.

### Preflight

```
POST /api/mining/v1/miners/preflight
Body: { "dataset_id": "<id>", "epoch_id": "<id>" }
```

Pre-submission check. Returns a PoW challenge when required.

### PoW Challenge

```
POST /api/mining/v1/pow-challenges/{challengeId}/answer
Body: { "answer": "<answer>" }
```

Submit the PoW answer. Must be solved before submission is accepted.

### Occupancy / Dedup

```
GET /api/core/v1/url-occupancies/check?dataset_id={id}&url={encodedUrl}
```

Returns occupancy state. **404 is treated as compatibility fallback** (URL is assumed unoccupied).

### Submission

```
POST /api/core/v1/submissions
Body: { "dataset_id": "...", "entries": [ ... ] }
```

Submit structured records. Each entry must include `dedup_key`, `canonical_url`, and all required schema fields.

```
GET /api/core/v1/submissions/{submissionId}
```

Fetch a single submission result.

### Task Claims

```
POST /api/mining/v1/repeat-crawl-tasks/claim
POST /api/mining/v1/refresh-tasks/claim
```

Claim a pending task. Returns `null` (via 404) when no tasks are available.

```
POST /api/mining/v1/repeat-crawl-tasks/{taskId}/report
POST /api/mining/v1/refresh-tasks/{taskId}/report
Body: { ... task result payload ... }
```

Report task completion.

### Miner Status

```
GET /api/mining/v1/miners/{minerId}/status
```

Returns credit score, tier, registration state. **404 degrades gracefully** to empty dict.

### Settlement

```
GET /api/mining/v1/miners/{minerId}/settlement
```

Returns settlement state for recent submissions. **404 degrades gracefully**.

### Reward Summary

```
GET /api/mining/v1/miners/{minerId}/reward-summary
```

Returns accumulated reward data. **404 degrades gracefully**.

## Error Handling

| Status | Meaning | Runtime Behavior |
|---|---|---|
| `401` + `MISSING_HEADERS` | Wallet signature not configured | Fatal — surface setup instructions |
| `401` + expired token | Session token expired | Auto-renew via `awp-wallet unlock`, retry |
| `403` | Access denied | Stop affected action, surface message |
| `404` (dataset) | Dataset archived or missing | Skip dataset |
| `404` (occupancy) | Endpoint not implemented | Compatibility fallback, treat as unoccupied |
| `404` (status/settlement/reward) | Endpoint not available | Return empty, degrade gracefully |
| `409` | Duplicate submission | Skip URL silently |
| `429` | Rate limited | Cooldown affected dataset, rotate to next |
| `500+` | Server error | Exponential backoff, retry up to 3 times |
| Timeout | Network issue | Exponential backoff, retry up to 3 times |
