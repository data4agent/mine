from __future__ import annotations

import json
import sys
from pathlib import Path

from secret_refs import read_mine_config, resolve_secret_ref


def resolve_crawler_root() -> Path:
    import os

    root = os.environ.get("SOCIAL_CRAWLER_ROOT", "").strip()
    candidates: list[Path] = []
    if root:
        candidates.append(Path(root).resolve())
    candidates.append(Path(__file__).resolve().parents[1])
    for path in candidates:
        if path.exists():
            return path
    if root:
        raise RuntimeError(f"SOCIAL_CRAWLER_ROOT does not exist: {Path(root).resolve()}")
    raise RuntimeError("SOCIAL_CRAWLER_ROOT does not exist and the local Mine runtime root could not be resolved")


def inject_crawler_root() -> Path:
    root = resolve_crawler_root()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def resolve_wallet_config() -> tuple[str, str]:
    """Return ``(wallet_bin, wallet_token)`` from environment variables.

    * ``AWP_WALLET_BIN``   – path to awp-wallet CLI (default ``"awp-wallet"``)
    * ``AWP_WALLET_TOKEN`` – session token from ``awp-wallet unlock --duration 3600``
    * ``AWP_WALLET_TOKEN_SECRET_REF`` – JSON SecretRef resolved against Mine config providers
    """
    import os

    wallet_token = os.environ.get("AWP_WALLET_TOKEN", "").strip()
    if not wallet_token:
        ref_raw = os.environ.get("AWP_WALLET_TOKEN_SECRET_REF", "").strip()
        if ref_raw:
            try:
                ref = json.loads(ref_raw)
            except json.JSONDecodeError:
                ref = None
            if ref is not None:
                wallet_token = resolve_secret_ref(ref, read_mine_config())

    return (
        os.environ.get("AWP_WALLET_BIN", "awp-wallet"),
        wallet_token,
    )
