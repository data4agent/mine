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
    candidates: list[Path] = []
    if root:
        candidates.append(Path(root).resolve())
    candidates.append(Path(__file__).resolve().parents[1])
    for path in candidates:
        if path.exists():
            return path
    return None


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
        return False, f"Mine runtime — not ready ({python_line})"
    if sys.version_info < (3, 11):
        return False, f"Mine runtime — found, but Mine needs Python 3.11+ ({python_line})"
    return True, f"Mine runtime — installed ({python_line})"


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
                "- Bootstrap the Mine runtime in this project.",
                "- Mine needs Python 3.11+ for crawler execution.",
            ]
        )
    if not platform_ok:
        lines.append(f"- Set PLATFORM_BASE_URL explicitly, or continue with the current testnet default {DEFAULT_TESTNET_PLATFORM_URL}.")
    lines.extend(["", "Run these commands, then say check again and I’ll re-verify."])
    return "\n".join(lines)


def render_dataset_listing(client_or_datasets: Any) -> str:
    datasets = []
    if isinstance(client_or_datasets, list):
        datasets = client_or_datasets
    else:
        try:
            datasets = client_or_datasets.list_datasets()
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
        suffix = []
        if dataset.get("selected"):
            suffix.append("selected")
        if dataset.get("cooldown"):
            suffix.append("cooldown")
        suffix_text = f" [{' / '.join(suffix)}]" if suffix else ""
        lines.append(f"- {index}. {dataset_id} — {domain_text}{suffix_text}")
    return "\n".join(lines)


def render_start_working_response(worker: Any, *, selected_dataset_ids: list[str] | None = None) -> str:
    try:
        payload = worker.start_working(selected_dataset_ids=selected_dataset_ids)
    except Exception as exc:
        return (
            "Unable to start mining yet.\n"
            f"- Start-up check failed: {exc}\n"
            "- If this is a signing/session issue, run: awp-wallet unlock --duration 3600\n"
            "- Then say check status or start working again."
        )
    heartbeat = payload.get("heartbeat") or {}
    status = payload.get("status") or {}
    datasets = payload.get("datasets") or []

    lines = []
    if heartbeat.get("unified_ok") or heartbeat.get("miner_ok"):
        lines.append("Heartbeat sent — miner registered")
    for error in heartbeat.get("errors") or []:
        lines.append(f"Heartbeat warning: {error}")
    if status.get("credit_score") is not None:
        lines.append(f"Credit score: {status.get('credit_score')}")
    if status.get("credit_tier"):
        lines.append(f"Credit tier: {status.get('credit_tier')}")
    if status.get("epoch_id"):
        lines.append(f"Current epoch: {status.get('epoch_id')}")
    if status.get("epoch_target"):
        lines.append(f"Target: {status.get('epoch_target')} submissions this epoch.")

    if payload.get("selection_required"):
        lines.extend(["", f"Found {len(datasets)} active DataSets:"])
        for index, dataset in enumerate(datasets, start=1):
            dataset_id = str(dataset.get("id") or f"dataset-{index}")
            domains = dataset.get("source_domains")
            if isinstance(domains, list):
                domain_text = ", ".join(str(item) for item in domains[:2])
            else:
                domain_text = str(domains or "no source domains")
            lines.append(f"- {index}. {dataset_id} — {domain_text}")
        lines.extend(
            [
                "",
                "Which DataSet(s) to mine? Enter dataset ids or a comma-separated list.",
            ]
        )
        return "\n".join(lines)

    selected = payload.get("selected_dataset_ids") or []
    if selected:
        lines.extend(
            [
                "",
                f"Mining {', '.join(selected)}.",
                "Say pause or stop anytime.",
            ]
        )
    else:
        lines.append("Mining session is ready.")
    return "\n".join(lines)


def render_control_response(payload: dict[str, Any]) -> str:
    lines = [str(payload.get("message") or "State updated.")]
    lines.append(f"Mining state: {payload.get('mining_state')}")
    if payload.get("selected_dataset_ids"):
        lines.append(f"Selected datasets: {', '.join(payload.get('selected_dataset_ids') or [])}")
    queues = payload.get("queues") or {}
    if queues:
        lines.append(
            "Queues — backlog: {backlog}, auth pending: {auth}, submit pending: {submit}".format(
                backlog=queues.get("backlog", 0),
                auth=queues.get("auth_pending", 0),
                submit=queues.get("submit_pending", 0),
            )
        )
    if payload.get("epoch_target") is not None:
        lines.append(f"Epoch progress: {payload.get('epoch_submitted')} / {payload.get('epoch_target')}")
    progress = payload.get("progress")
    if isinstance(progress, dict):
        epoch_completion = progress.get("epoch_completion_percent")
        epoch_remaining = progress.get("epoch_remaining")
        if epoch_completion is not None:
            lines.append(f"Epoch completion: {epoch_completion}%")
        if epoch_remaining is not None:
            lines.append(f"Remaining this epoch: {epoch_remaining}")
    if payload.get("last_control_action"):
        lines.append(f"Last control action: {payload.get('last_control_action')}")
    lines.append("Current batch control: pause / resume / stop")
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
    if status.get("selected_dataset_ids"):
        lines.append(f"- Selected datasets: {', '.join(status.get('selected_dataset_ids') or [])}")
    progress = status.get("progress")
    if isinstance(progress, dict):
        if progress.get("epoch_completion_percent") is not None:
            lines.append(f"- Epoch completion: {progress.get('epoch_completion_percent')}%")
        if progress.get("epoch_remaining") is not None:
            lines.append(f"- Remaining this epoch: {progress.get('epoch_remaining')}")
        lines.append(
            "- Current session totals: processed {processed}, submitted {submitted}, failed {failed}".format(
                processed=progress.get("session_processed_items", 0),
                submitted=progress.get("session_submitted_items", 0),
                failed=progress.get("session_failed_items", 0),
            )
        )
    if status.get("last_control_action"):
        lines.append(f"- Last control action: {status.get('last_control_action')}")
    if status.get("credit_score") is not None:
        lines.append(f"- Credit score: {status.get('credit_score')}")
    if status.get("credit_tier"):
        lines.append(f"- Credit tier: {status.get('credit_tier')}")
    if status.get("settlement"):
        lines.append(f"- Settlement state: {status.get('settlement')}")
    return "\n".join(lines)
