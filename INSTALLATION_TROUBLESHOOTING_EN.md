# Installation Troubleshooting

## Issue: awp-wallet is not installed after installing the Skill

### Symptoms

After installing the mine skill, you may see:

```
ERROR: awp-wallet not found
```

Or:

```
Agent identity — not available
Fix: Install awp-wallet: npm install -g @aspect/awp-wallet
```

### Causes

Possible reasons:

1. **Node.js is not installed** — awp-wallet requires Node.js 20+
2. **npm permission issues** — global npm installs may fail
3. **Network issues** — npm registry unreachable
4. **Bootstrap was skipped** — install done through another path
5. **PATH issues** — awp-wallet is installed but not on PATH

### Solutions

## Method 1: Automatic fix (recommended)

Run the fix script; it detects and repairs common problems:

```bash
cd mine
python scripts/fix_installation.py
```

Or run the check script directly:

```bash
python scripts/post_install_check.py
```

This will:

- ✓ Check Python, Node.js, npm, and awp-wallet
- ✓ Install missing components automatically
- ✓ Set default environment variables where applicable
- ✓ Verify the installation

Example output:

```
================================================================================
Mine Skill - Post-Install Check
================================================================================

✓ Python version: Python 3.12
✓ Node.js: Node.js v20.10.0
✓ npm: npm 10.2.3
⚠ awp-wallet: awp-wallet not found

================================================================================
Attempting Auto-Fix
================================================================================

→ Installing awp-wallet...
  ✓ awp-wallet installed successfully

================================================================================
✓ All checks passed!
================================================================================
```

## Method 2: Re-run Bootstrap

```bash
# Windows
.\scripts\bootstrap.ps1

# Linux / macOS
bash scripts/bootstrap.sh
```

Bootstrap runs the full installation flow.

## Method 3: Manual installation

### Step 1: Confirm Node.js

```bash
node --version
npm --version
```

If missing, install from https://nodejs.org.

**Recommended:** Node.js 20 LTS or newer.

### Step 2: Install awp-wallet

```bash
npm install -g @aspect/awp-wallet
```

### Step 3: Verify

```bash
awp-wallet --version
```

Expected output:

```
@aspect/awp-wallet/1.x.x
```

### Step 4: Initialize the wallet

```bash
awp-wallet init
```

Follow the prompts to set a password.

### Step 5: Unlock the wallet

```bash
awp-wallet unlock --duration 3600
```

Copy the `sessionToken` from the output.

### Step 6: Set environment variables

```bash
export AWP_WALLET_TOKEN=wlt_xxx  # paste from the previous step
```

## FAQ

### Q1: `npm install` fails with permission error (EACCES)

**Windows:**

```powershell
# Run PowerShell as Administrator
npm install -g @aspect/awp-wallet
```

**Linux / macOS:**

```bash
# Prefer nvm; avoid sudo for global npm installs
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
npm install -g @aspect/awp-wallet
```

### Q2: npm registry timeouts

Use a mirror (e.g. in China):

```bash
npm config set registry https://registry.npmmirror.com
npm install -g @aspect/awp-wallet
```

### Q3: awp-wallet installed but command not found

**Check install location:**

```bash
npm list -g @aspect/awp-wallet
```

**Locate the binary:**

```bash
# Windows
where awp-wallet

# Linux / macOS
which awp-wallet
```

**Set PATH manually:**

Windows:

```powershell
$env:AWP_WALLET_BIN = "C:\Users\<username>\AppData\Roaming\npm\awp-wallet.cmd"
```

Linux / macOS:

```bash
export AWP_WALLET_BIN="$(npm root -g)/../bin/awp-wallet"
```

### Q4: Node.js version too old

```bash
# Check version
node --version  # need >= v20.0.0

# Upgrade Node.js

# Windows: download the latest from https://nodejs.org

# macOS:
brew upgrade node

# Linux (with nvm):
nvm install 20
nvm use 20
nvm alias default 20
```

### Q5: Python virtual environment not created

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
pip install -r requirements-core.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements-core.txt
```

## Diagnostic commands

### Full diagnostics

```bash
python scripts/run_tool.py doctor
```

Returns detailed JSON:

```json
{
  "status": "error",
  "checks": [
    {"name": "python", "ok": true, "message": "Python 3.12"},
    {"name": "awp-wallet", "ok": false, "message": "Not found"}
  ],
  "fix_commands": [
    "npm install -g @aspect/awp-wallet"
  ]
}
```

### Agent status

```bash
python scripts/run_tool.py agent-status
```

Minimal output for agents:

```json
{
  "ready": false,
  "state": "missing_wallet",
  "message": "awp-wallet not installed",
  "next_action": "Install awp-wallet",
  "next_command": "npm install -g @aspect/awp-wallet"
}
```

## Verify installation

Run the full check:

```bash
python scripts/post_install_check.py
```

You should see:

```
================================================================================
✓ All checks passed!
================================================================================

Next steps:
  1. Initialize wallet: awp-wallet init
  2. Unlock wallet:    awp-wallet unlock --duration 3600
  3. Start mining:     python scripts/run_tool.py run-worker 60 1
```

## Still stuck?

### Collect diagnostics

```bash
# Versions
python --version
node --version
npm --version

# PATH
echo $PATH  # Linux / macOS
echo $env:PATH  # Windows

# npm config
npm config list

# Global packages
npm list -g --depth=0

# awp-wallet
npm list -g @aspect/awp-wallet
which awp-wallet  # Linux / macOS
where awp-wallet  # Windows
```

### Open an issue

See: https://github.com/clawtroop/mine/issues

Include:

- OS version
- Steps you took
- Full error messages
- Output of `post_install_check.py`

## Quick reference

| Issue | Command |
|------|---------|
| Check and fix | `python scripts/fix_installation.py` |
| Reinstall flow | `bash scripts/bootstrap.sh` |
| Diagnostics | `python scripts/run_tool.py doctor` |
| Install wallet CLI | `npm install -g @aspect/awp-wallet` |
| Initialize wallet | `awp-wallet init` |
| Unlock wallet | `awp-wallet unlock --duration 3600` |

## Prevention

Before installing the mine skill:

1. ✓ Node.js 20+ installed
2. ✓ Python 3.11+ installed
3. ✓ npm can install global packages (permissions OK)
4. ✓ Network can reach the npm registry

End-to-end example:

```bash
# 1. Preconditions
node --version  # >= v20.0.0
python --version  # >= 3.11

# 2. Install mine skill
openclaw install mine

# 3. Verify
cd ~/.openclaw/extensions/mine
python scripts/post_install_check.py

# 4. Wallet setup
awp-wallet init
awp-wallet unlock --duration 3600

# 5. Mining
python scripts/run_tool.py run-worker 60 1
```

## Related docs

- [AWP_WALLET_AUTO_INSTALL.md](docs/AWP_WALLET_AUTO_INSTALL.md) — automatic awp-wallet installation
- [EIP712_CONFIGURATION.md](docs/EIP712_CONFIGURATION.md) — EIP-712 signing configuration
- [SKILL.md](SKILL.md) — skill usage
