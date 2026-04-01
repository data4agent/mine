# Mine Platform API Notes

Mine talks to the platform through heartbeat, dataset listing, preflight, PoW answer, occupancy, and submission endpoints.

## Core flows

- `POST /api/mining/v1/heartbeat`
- `POST /api/mining/v1/miners/heartbeat`
- `GET /api/core/v1/datasets`
- `POST /api/mining/v1/miners/preflight`
- `POST /api/mining/v1/pow-challenges/{id}/answer`
- `GET /api/core/v1/url-occupancies/check`
- `POST /api/core/v1/submissions`

## Product guidance

- Treat `404` occupancy as a compatibility fallback when safe.
- Cool down datasets on `429`.
- Refresh wallet session tokens before expiry and surface recovery guidance.
