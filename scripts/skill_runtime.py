from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from common import resolve_wallet_config


DEFAULT_TESTNET_PLATFORM_URL = "http://101.47.73.95"


def _resolve_crawler_root() -> Path | None:
    root = os.environ.get("SOCIAL_CRAWLER_ROOT", "").strip()
    if not root:
        return None
    path = Path(root).resolve()
    return path if path.exists() else None


def _wallet_ready() -> tuple[bool, str]:
    wallet_bin, wallet_token = resolve_wallet_config()
    resolved = shutil.which(wallet_bin) or wallet_bin
    wallet_installed = bool(shutil.which(wallet_bin) or Path(wallet_bin).exists())
    if not wallet_installed:
        return False, f"AWP Wallet — missing ({resolved})"
    if wallet_token.strip():
        return True, "AWP Wallet — installed, unlocked"
    return False, "AWP Wallet — installed, but locked"


def _crawler_ready() -> tuple[bool, str]:
    crawler_root = _resolve_crawler_root()
    python_line = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if crawler_root is None:
        return False, f"social-data-crawler — not installed ({python_line})"
    if sys.version_info < (3, 11):
        return False, f"social-data-crawler — repository found, but Mine needs Python 3.11+ ({python_line})"
    return True, f"social-data-crawler — installed ({python_line})"


def _platform_line() -> tuple[bool, str]:
    configured = os.environ.get("PLATFORM_BASE_URL", "").strip()
    if configured:
        return True, f"Platform Service base URL — {configured}"
    return False, f"Platform Service base URL — not set, using default ({DEFAULT_TESTNET_PLATFORM_URL})"


def render_first_load_experience() -> str:
    wallet_ok, wallet_line = _wallet_ready()
    crawler_ok, crawler_line = _crawler_ready()
    platform_ok, platform_line = _platform_line()

    lines = [
        "Welcome to Mine — the data service WorkNet!",
        "",
        "Your agent mines the internet for structured data and earns $aMine.",
        "Crawl, clean, structure, submit — with the agent handling the workflow for you.",
        "",
        "Quick start:",
        "- start working — begin autonomous mining",
        "- check status — see credit score, epoch status, and reward-related state",
        "- list datasets — inspect active datasets before starting",
        "",
        "Security: your private keys never leave awp-wallet.",
        "Mine only uses time-limited session tokens for signing.",
        "",
        "Dependency check:",
        f"- {wallet_line}",
        f"- {crawler_line}",
        f"- {platform_line}",
    ]

    if wallet_ok and crawler_ok:
        lines.extend(["", "All dependencies ready.", "", "Or just tell me what you'd like to do."])
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "Next steps to fix the environment:",
        ]
    )
    if not wallet_ok:
        lines.extend(
            [
                "- Install or expose awp-wallet on PATH.",
                "- If it is installed but locked, run: awp-wallet unlock --duration 3600",
            ]
        )
    if not crawler_ok:
        lines.extend(
            [
                "- Clone social-data-crawler and bootstrap it.",
                "- Mine needs Python 3.11+ for crawler execution.",
            ]
        )
    if not platform_ok:
        lines.append(f"- Set PLATFORM_BASE_URL explicitly, or continue with the current testnet default {DEFAULT_TESTNET_PLATFORM_URL}.")
    lines.extend(["", "Run these commands, then say check again and I’ll re-verify."])
    return "\n".join(lines)


def render_dataset_listing(client: Any) -> str:
    datasets = []
    try:
        datasets = client.list_datasets()
    except Exception as exc:  # pragma: no cover - defensive formatting path
        return f"Active datasets\n- dataset listing failed: {exc}"
    if not datasets:
        return "Active datasets\n- none available"
    lines = ["Active datasets"]
    for index, dataset in enumerate(datasets, start=1):
        dataset_id = str(dataset.get("id") or f"dataset-{index}")
        domains = dataset.get("source_domains")
        if isinstance(domains, list):
            domain_text = ", ".join(str(item) for item in domains[:3])
        else:
            domain_text = str(domains or "no source domains")
        lines.append(f"- {index}. {dataset_id} — {domain_text}")
    return "\n".join(lines)


def render_status_summary(worker: Any) -> str:
    status = worker.check_status()
    datasets = []
    try:
        datasets = worker.client.list_datasets()
    except Exception:
        datasets = []

    lines = [
        "Mine status",
        f"- Miner ID: {worker.config.miner_id}",
        f"- Platform Service: {worker.config.base_url}",
        f"- Mining state: {status.get('mining_state')}",
        f"- Known active datasets: {len(datasets)}",
        f"- Backlog: {status['queues']['backlog']}",
        f"- Auth pending: {status['queues']['auth_pending']}",
        f"- Submit pending: {status['queues']['submit_pending']}",
        f"- Epoch progress: {status.get('epoch_submitted')} / {status.get('epoch_target')}",
        f"- Current batch control: pause / resume / stop",
    ]
    if status.get("credit_score") is not None:
        lines.append(f"- Credit score: {status.get('credit_score')}")
    if status.get("credit_tier"):
        lines.append(f"- Credit tier: {status.get('credit_tier')}")
    if status.get("settlement"):
        lines.append(f"- Settlement state: {status.get('settlement')}")
    return "\n".join(lines)
