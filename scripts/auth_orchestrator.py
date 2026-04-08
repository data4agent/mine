from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from run_models import WorkItem
from worker_state import WorkerStateStore


AUTH_ERROR_CODES = {
    "AUTH_REQUIRED",
    "AUTH_EXPIRED",
    "AUTH_INTERACTIVE_TIMEOUT",
    "AUTH_SESSION_EXPORT_FAILED",
    "AUTH_AUTO_LOGIN_FAILED",
    "CAPTCHA",
}


class AuthOrchestrator:
    def __init__(self, state_store: WorkerStateStore, *, retry_after_seconds: int) -> None:
        self.state_store = state_store
        self.retry_after_seconds = retry_after_seconds

    def handle_errors(self, item: WorkItem, errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        auth_pending: list[dict[str, Any]] = []
        for error in errors:
            if str(error.get("error_code") or "") not in AUTH_ERROR_CODES:
                continue
            normalized_error = self._normalize_error(item, error)
            self.state_store.upsert_auth_pending(
                item,
                normalized_error,
                retry_after_seconds=self.retry_after_seconds,
            )
            auth_pending.append({
                "item_id": item.item_id,
                "url": item.url,
                "platform": item.platform,
                "error_code": normalized_error.get("error_code"),
                "next_action": normalized_error.get("next_action"),
                "public_url": normalized_error.get("public_url"),
                "login_url": normalized_error.get("login_url"),
            })
        return auth_pending

    def clear_if_recovered(self, item: WorkItem) -> None:
        self.state_store.clear_auth_pending(item.item_id)

    def _normalize_error(self, item: WorkItem, error: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(error)
        error_code = str(normalized.get("error_code") or "")
        next_action = str(normalized.get("next_action") or "").strip()
        public_url = str(normalized.get("public_url") or "").strip()
        login_url = str(normalized.get("login_url") or "").strip()
        browser_platform = self._resolve_browser_platform(item, normalized)

        if browser_platform and error_code in {
            "AUTH_REQUIRED",
            "AUTH_EXPIRED",
            "AUTH_INTERACTIVE_TIMEOUT",
            "AUTH_SESSION_EXPORT_FAILED",
            "AUTH_AUTO_LOGIN_FAILED",
        }:
            normalized["next_action"] = f"run browser-session {browser_platform} and retry"
            normalized["browser_session_command"] = f"python scripts/run_tool.py browser-session {browser_platform}"
            normalized["browser_session_status_command"] = (
                f"python scripts/run_tool.py browser-session-status {browser_platform}"
            )
        elif error_code == "CAPTCHA" and next_action in {"", "notify_user", "escalate backend"}:
            normalized["next_action"] = f"open Cloudflare/VNC link from browser-session {browser_platform or 'platform'} and complete login"
            if browser_platform:
                normalized["browser_session_command"] = f"python scripts/run_tool.py browser-session {browser_platform}"
                normalized["browser_session_status_command"] = (
                    f"python scripts/run_tool.py browser-session-status {browser_platform}"
                )

        if not public_url:
            normalized["public_url"] = login_url or item.url
        if error_code == "CAPTCHA" and not login_url:
            normalized["login_url"] = public_url or item.url
        return normalized

    def _resolve_browser_platform(self, item: WorkItem, error: dict[str, Any]) -> str:
        platform = str(item.platform or error.get("platform") or "").strip().lower()
        if platform and platform != "generic":
            return platform

        dataset_id = str(getattr(item, "dataset_id", "") or "").strip().lower()
        if dataset_id.startswith("ds_linkedin_"):
            return "linkedin"

        for candidate in (
            str(error.get("login_url") or "").strip(),
            str(error.get("public_url") or "").strip(),
            str(item.url or "").strip(),
        ):
            if not candidate:
                continue
            host = urlparse(candidate).netloc.lower()
            if "linkedin.com" in host:
                return "linkedin"
        return ""
