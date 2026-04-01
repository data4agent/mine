# Changelog

## [Unreleased] - 2026-04-01

### Added
- **Production environment support**
  - Verified production URL: `https://sd76fip34meovmfu5ftlg.apigateway-ap-southeast-1.volceapi.com`
  - Added `PRODUCTION_SETUP.md` with whitelist registration guide
  - Production requires wallet address whitelisting (returns `UNTRUSTED_HOST` error if not whitelisted)

### Changed
- **Simplified MINER_ID configuration**
  - **REMOVED** `MINER_ID` environment variable requirement (was redundant)
  - Platform automatically uses wallet address from EIP-712 signature
  - See `MINER_ID_REMOVED.md` for full details and upgrade guide
  - Updated all code to fetch miner_id dynamically from wallet: `signer.get_address()`

- **Environment configuration**
  - Updated `.env.example` to default to test environment (easier onboarding)
  - Added clear comments distinguishing test vs production environments
  - Test environment (`http://101.47.73.95`) has open access
  - Production environment requires whitelisting

- **Documentation improvements**
  - Simplified `SKILL.md` from 652 lines to 155 lines
  - Moved detailed content to separate focused documents
  - Added `DEPENDENCIES.md` documenting total size (~1GB)
  - Added `MINING_OUTPUTS.md` documenting output file structure
  - Cleaned up docs directory and removed development artifacts

### Fixed
- **EIP-712 signature authentication**
  - Fixed 401 Unauthorized errors by passing domain parameters through call chain
  - Verified working configuration:
    - `EIP712_DOMAIN_NAME`: `aDATA`
    - `EIP712_CHAIN_ID`: `8453` (Base chain)
    - `EIP712_VERIFYING_CONTRACT`: `0x0000000000000000000000000000000000000000`
  - Same configuration works for both test and production environments

- **AWP Wallet integration**
  - Updated prompts from "user wallet" to "agent wallet" (clearer messaging)
  - Added auto-installation in bootstrap scripts
  - Created `post_install_check.py` for comprehensive dependency checking

### Security
- Wallet management is fully agent-controlled (no user wallet access required)
- EIP-712 typed data signing for all API requests
- Automatic session renewal on token expiration

## Architecture Changes

### Code Updates

**`lib/platform_client.py`:**
- Removed `miner_id` parameter from `__init__`
- Added EIP-712 domain parameters: `eip712_domain_name`, `eip712_chain_id`, `eip712_verifying_contract`
- Updated query methods to get wallet address dynamically:
  ```python
  def fetch_miner_status(self):
      miner_id = self._signer.get_address() if self._signer else ""
      return self._request_optional_data("GET", f"/api/mining/v1/miners/{miner_id}/status")
  ```

**`scripts/signer.py`:**
- Added `domain_name` and `verifying_contract` parameters to `build_auth_headers()`
- Passes these to `build_typed_data()` for correct EIP-712 signature generation

**`scripts/run_models.py`:**
- Removed `miner_id` from `WorkerConfig` dataclass
- Added EIP-712 configuration fields with defaults:
  ```python
  eip712_domain_name: str = "Platform Service"
  eip712_chain_id: int = 1
  eip712_verifying_contract: str = "0x0000000000000000000000000000000000000000"
  ```

**`scripts/agent_runtime.py`:**
- Removed `MINER_ID` environment variable reading
- Added EIP-712 environment variable reading with defaults
- Passes EIP-712 config to `PlatformClient`

**`scripts/skill_runtime.py`:**
- Changed wallet status messages from "AWP Wallet" to "Agent identity"
- Emphasizes that wallet is agent-managed, not user-managed

### API Verification

**Test Environment:**
- URL: `http://101.47.73.95`
- Status: ✅ Working with EIP-712 config
- Access: Open (no whitelist)

**Production Environment:**
- URL: `https://sd76fip34meovmfu5ftlg.apigateway-ap-southeast-1.volceapi.com`
- Status: ✅ Accessible (45 endpoints verified)
- Access: ⚠ Requires wallet whitelisting
- EIP-712: Same config as test environment

## Migration Guide

### For Existing Users

**No action required!** 

The `MINER_ID` removal is fully backward compatible:
- Old `.env` files with `MINER_ID` will work (variable is ignored)
- No functional changes to mining workflow
- Wallet address is automatically used for identification

**Optional cleanup:**
```bash
# Remove this line from your .env if desired:
# export MINER_ID=miner-xxx
```

### For New Users

1. Install awp-wallet and dependencies:
   ```bash
   openclaw install mine
   ```

2. Initialize and unlock wallet:
   ```bash
   awp-wallet init
   awp-wallet unlock --duration 3600
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your wallet token
   ```

4. Start mining:
   ```bash
   python scripts/run_tool.py run-worker 60 1
   ```

See `SKILL.md` for complete setup guide.

## Production Deployment

To use production environment:

1. **Get your wallet address:**
   ```bash
   awp-wallet receive
   ```

2. **Request whitelisting:**
   - Contact platform team with your wallet address
   - Wait for whitelist approval

3. **Update configuration:**
   ```bash
   # In .env, change:
   export PLATFORM_BASE_URL=https://sd76fip34meovmfu5ftlg.apigateway-ap-southeast-1.volceapi.com
   ```

4. **Verify access:**
   ```bash
   python scripts/run_tool.py doctor
   # Should show: ✓ Platform Service — accessible
   ```

See `PRODUCTION_SETUP.md` for complete details.

## Known Issues

### Pending Updates (Non-Critical)
- `mine_setup.py` still checks for `MINER_ID` (diagnostic only)
- `post_install_check.py` still checks for `MINER_ID` (diagnostic only)
- `run_tool.py` may display `MINER_ID` in status (cosmetic only)

These do not affect core mining functionality and can be cleaned up later.

## Dependencies

Total installation size: **~1GB**
- Python dependencies: ~870MB
- awp-wallet (Node.js): ~180MB

See `DEPENDENCIES.md` for complete package list with versions.

## Output Files

Mining produces:
- `output/{crawler}/records.jsonl` - Crawled data records
- `output/{crawler}/summary.json` - Crawl summary statistics
- `state/{crawler}/state.json` - Crawler state persistence

See `MINING_OUTPUTS.md` for complete output documentation.
