---
name: mine
description: Autonomous mining skill for signed platform work, crawler execution, and submission export through awp-wallet.
bootstrap: ./scripts/bootstrap.sh
windows_bootstrap: ./scripts/bootstrap.ps1
smoke_test: ./scripts/smoke_test.py
requires:
  skills:
    - auto-browser
  bins:
    - npm
    - git
  anyBins:
    - python
    - python3
    - py
---

# Mine

Mine is the agent-facing entrypoint for the local mining runtime in this repository.

## Canonical host command surface

OpenClaw and other host agents should prefer these commands:

```bash
python scripts/run_tool.py agent-status
python scripts/run_tool.py agent-start
python scripts/run_tool.py agent-control status
python scripts/run_tool.py agent-control pause
python scripts/run_tool.py agent-control resume
python scripts/run_tool.py agent-control stop
```

Advanced local/runtime commands still exist, but they are not the recommended host integration path.

## Setup

Bootstrap first.

Unix-like:

```bash
./scripts/bootstrap.sh
```

Windows:

```powershell
./scripts/bootstrap.ps1
```

Bootstrap installs Python dependencies, verifies the host, installs `awp-wallet` from GitHub if it is missing, and refreshes the public signature config cache when the platform is reachable.
On supported hosts, bootstrap also prepares or restores the local wallet session so `agent-start` can run without manual token export.
Bootstrap / post-install checks now also report whether the active signature config came from `platform` or `fallback`.

Windows note:

- LinkedIn `--auto-login` uses a local visible Chrome/Edge window
- `python auto-browser/scripts/vrd.py check` verifies the native Windows browser path
- if LinkedIn blocks login with CAPTCHA or browser risk checks, the crawler should now return an `AUTH_*` diagnostic instead of a Python runtime exception

## Wallet flow

The normal path is now auto-managed:

- bootstrap verifies `awp-wallet`
- Mine restores the last valid local wallet session from worker state when available
- if no session exists yet, Mine attempts `awp-wallet init` and `awp-wallet unlock --duration 3600` automatically

Manual wallet commands are now fallback/recovery tools, not the primary host path.

Mine uses `awp-wallet` for all request signing. Never store seed phrases or private keys in repo files.

## Environment

Mine now has safe built-in defaults and does not require a `.env` file. If you do set environment variables, they override the defaults.

Common overrides:

```bash
PLATFORM_BASE_URL=http://101.47.73.95
MINER_ID=mine-agent
AWP_WALLET_BIN=awp-wallet
```

Important nuance:

- `PLATFORM_BASE_URL` now defaults to testnet
- `MINER_ID` now defaults to `mine-agent` for helper-layer compatibility
- EIP-712 参数会在运行时优先尝试从平台公开接口 `GET /api/public/v1/signature-config` 拉取
- 拉取成功后会覆盖本地默认值，并写入本地 worker state 缓存
- 平台暂时不可达时，才回退到内置 fallback 默认值
- `EIP712_DOMAIN_NAME` / `EIP712_CHAIN_ID` / `EIP712_VERIFYING_CONTRACT` 现在只应作为手动覆盖手段
- 若钱包尚未在 AWP 注册，启动链路会自动尝试 gasless 自注册，等价于 `setRecipient(self)`
- `doctor` 会显示签名配置来源和注册状态，方便宿主判断当前是否已 ready
- lower-level platform identity is still derived from the wallet signer address

For full details, see [`docs/ENVIRONMENT.md`](./docs/ENVIRONMENT.md).

## Recommended OpenClaw workflow

1. Run bootstrap.
2. Run `python scripts/run_tool.py agent-status`.
3. Run `python scripts/run_tool.py agent-start`.
4. Use `python scripts/run_tool.py agent-control status` to inspect progress without blocking chat.

## Troubleshooting

Use:

```bash
python scripts/run_tool.py doctor
python scripts/run_tool.py diagnose
python scripts/run_tool.py agent-status
awp-wallet unlock --duration 3600
```

Windows LinkedIn preflight:

```powershell
python auto-browser/scripts/vrd.py check
python auto-browser/scripts/vrd.py start
python auto-browser/scripts/vrd.py status
```

If `awp-wallet` is missing and bootstrap did not install it, install it from GitHub:

```bash
git clone https://github.com/awp-core/awp-wallet.git
cd awp-wallet
npm install
npm install -g .
```

Do not rely on `npm install -g @aspect/awp-wallet`.

## Alias mapping

If OpenClaw exposes slash aliases, they should map to the canonical commands instead of becoming the source of truth:

```text
/mine-start  -> python scripts/run_tool.py agent-start
/mine-status -> python scripts/run_tool.py agent-control status
/mine-pause  -> python scripts/run_tool.py agent-control pause
/mine-resume -> python scripts/run_tool.py agent-control resume
/mine-stop   -> python scripts/run_tool.py agent-control stop
```

## Reference docs

- [`docs/AGENT_GUIDE.md`](./docs/AGENT_GUIDE.md)
- [`docs/ENVIRONMENT.md`](./docs/ENVIRONMENT.md)
- [`references/commands-mining.md`](./references/commands-mining.md)
- [`references/api-platform.md`](./references/api-platform.md)
- [`references/protocol-miner.md`](./references/protocol-miner.md)
- [`references/security-model.md`](./references/security-model.md)
- [`references/error-recovery.md`](./references/error-recovery.md)
