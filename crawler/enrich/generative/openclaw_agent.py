"""OpenClaw agent execution aligned with awp-core/s1-benchmark-skill.

This module is the preferred execution path for mine LLM enrich calls. It
mirrors the benchmark worker's approach:

- resolve the OpenClaw binary up front
- use a dedicated agent instead of `main`
- create the agent if missing
- purge session transcripts before and after every CLI call
- parse structured JSON responses when available
- back off briefly after rate-limit style failures
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_CLI_TIMEOUT: int = 120
DEFAULT_AGENT_ID: str = "mine-enrich"
DEFAULT_RATE_LIMIT_BACKOFF_SECONDS: int = 60

_RATE_LIMIT_HINTS = ("429", "rate limit", "extra usage", "too many requests")

_openclaw_bin: str = ""
_ready_agents: set[str] = set()
_rate_limit_until: float = 0.0
_agent_lock = threading.Lock()
_agent_call_locks: dict[str, threading.Lock] = {}
_agent_selection_counter: int = 0


@dataclass(slots=True)
class EnrichResponse:
    """Response from benchmark-skill style agent enrichment."""

    content: str
    success: bool
    source: str
    error: str | None = None
    model: str | None = None
    tokens_used: int | None = None


class OpenClawAgentError(RuntimeError):
    """Raised when the OpenClaw agent CLI call fails."""


def benchmark_skill_available() -> bool:
    """Return whether an OpenClaw CLI binary is available."""
    return bool(_resolve_openclaw_path(required=False))


def _configured_agent_id() -> str:
    explicit = os.environ.get("MINE_ENRICH_AGENT_ID", "").strip()
    if explicit:
        return explicit
    suffix = os.environ.get("MINE_ENRICH_AGENT_SUFFIX", "").strip()
    return f"{DEFAULT_AGENT_ID}-{suffix}" if suffix else DEFAULT_AGENT_ID


def _configured_agent_pool_size() -> int:
    raw = os.environ.get("MINE_ENRICH_AGENT_POOL_SIZE", "").strip()
    if not raw:
        return 1
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def _pooled_agent_ids() -> list[str]:
    base_agent_id = _configured_agent_id()
    pool_size = _configured_agent_pool_size()
    if pool_size <= 1:
        return [base_agent_id]
    return [base_agent_id, *[f"{base_agent_id}-{index}" for index in range(2, pool_size + 1)]]


def _runtime_agent_id() -> str:
    """Resolve the runtime OpenClaw agent id.

    Default to a stable shared agent because recent OpenClaw gateway builds do
    not reliably expose just-created per-thread agents immediately. Thread-
    scoped agents remain available behind an explicit opt-in for environments
    that have verified that behavior.
    """
    base_agent_id = _configured_agent_id()
    use_thread_agents = os.environ.get("MINE_ENRICH_THREAD_AGENTS", "").strip().lower()
    if use_thread_agents in {"1", "true", "yes", "on"}:
        return f"{base_agent_id}-p{os.getpid()}-t{threading.get_ident()}"
    agent_ids = _pooled_agent_ids()
    if len(agent_ids) == 1:
        return agent_ids[0]
    global _agent_selection_counter
    with _agent_lock:
        agent_id = agent_ids[_agent_selection_counter % len(agent_ids)]
        _agent_selection_counter += 1
    return agent_id


def _runtime_session_id(agent_id: str) -> str:
    return f"{agent_id}-s{time.time_ns()}"


def _workspace_for_agent(agent_id: str) -> str:
    return str(Path.home() / ".openclaw" / f"workspace-{agent_id}")


def _session_dir_for_agent(agent_id: str) -> Path:
    return Path.home() / ".openclaw" / "agents" / agent_id / "sessions"


def _resolve_openclaw_path(*, required: bool = True) -> str:
    """Find the OpenClaw binary using the same heuristics as benchmark-worker."""
    global _openclaw_bin

    if _openclaw_bin:
        return _openclaw_bin

    configured = os.environ.get("OPENCLAW_BIN", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            _openclaw_bin = str(candidate)
            return _openclaw_bin

    for name in ("openclaw", "openclaw.mjs", "openclaw.cmd"):
        path = shutil.which(name)
        if path:
            _openclaw_bin = path
            log.info("[AGENT] openclaw found: %s", path)
            return _openclaw_bin

    search_dirs = [
        os.path.expanduser("~/.local/bin"),
        "/usr/local/bin",
        os.path.expanduser("~/.openclaw/bin"),
        os.path.expanduser("~/bin"),
        os.path.expanduser("~/.openclaw"),
        "/usr/bin",
        os.path.expanduser("~/AppData/Roaming/npm"),
        "C:/nvm4w/nodejs",
    ]
    for directory in search_dirs:
        for name in ("openclaw", "openclaw.mjs", "openclaw.cmd"):
            candidate = Path(directory) / name
            if candidate.is_file():
                _openclaw_bin = str(candidate)
                log.info("[AGENT] openclaw found at: %s", candidate)
                return _openclaw_bin

    fallback_candidates = [
        os.path.expanduser("~/.openclaw/openclaw.mjs"),
        os.path.expanduser("~/.openclaw/node_modules/.bin/openclaw"),
        os.path.expanduser("~/.npm-global/bin/openclaw"),
        "/usr/lib/node_modules/openclaw/openclaw.mjs",
    ]
    for raw_candidate in fallback_candidates:
        candidate = Path(raw_candidate)
        if candidate.is_file():
            _openclaw_bin = str(candidate)
            log.info("[AGENT] openclaw found at: %s", candidate)
            return _openclaw_bin

    if required:
        raise OpenClawAgentError("openclaw command not found")
    return ""


def _agent_exists(agent_id: str) -> bool:
    openclaw = _resolve_openclaw_path(required=False)
    if not openclaw:
        return False
    try:
        result = subprocess.run(
            [openclaw, "agents", "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    return result.returncode == 0 and agent_id in result.stdout


def _create_agent(agent_id: str) -> bool:
    openclaw = _resolve_openclaw_path(required=False)
    if not openclaw:
        return False
    try:
        result = subprocess.run(
            [
                openclaw,
                "agents",
                "add",
                agent_id,
                "--workspace",
                _workspace_for_agent(agent_id),
                "--non-interactive",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        log.warning("[AGENT] failed to create agent %s: %s", agent_id, exc)
        return False

    if result.returncode == 0:
        log.info("[AGENT] created agent: %s", agent_id)
        return True

    log.warning("[AGENT] failed to create agent %s: %s", agent_id, (result.stderr or "").strip()[:200])
    return False


def _purge_agent_sessions(agent_id: str) -> None:
    """Delete benchmark-style transcript files so each call starts clean."""
    session_dir = _session_dir_for_agent(agent_id)
    if not session_dir.is_dir():
        return

    count = 0
    for path in session_dir.iterdir():
        try:
            if path.name == "sessions.json":
                path.write_text("{}", encoding="utf-8")
                count += 1
            elif path.is_file() and (path.name.endswith(".jsonl") or path.name.endswith(".lock")):
                path.unlink()
                count += 1
        except OSError:
            pass

    if count:
        log.info("[AGENT] purged %d session files from %s", count, session_dir)


def ensure_agent(agent_id: str | None = None) -> str:
    """Ensure the dedicated enrich agent exists."""
    with _agent_lock:
        resolved_agent_id = agent_id or _runtime_agent_id()
        _resolve_openclaw_path()
        if resolved_agent_id in _ready_agents and _agent_exists(resolved_agent_id):
            return resolved_agent_id
        if _agent_exists(resolved_agent_id):
            log.info("[AGENT] found existing agent: %s", resolved_agent_id)
        else:
            log.info("[AGENT] agent '%s' not found, creating...", resolved_agent_id)
            created = _create_agent(resolved_agent_id)
            if not created or not _agent_exists(resolved_agent_id):
                fallback_agent_id = _configured_agent_id()
                if resolved_agent_id != fallback_agent_id and _agent_exists(fallback_agent_id):
                    log.warning(
                        "[AGENT] falling back from unavailable runtime agent %s to configured agent %s",
                        resolved_agent_id,
                        fallback_agent_id,
                    )
                    _ready_agents.add(fallback_agent_id)
                    return fallback_agent_id
                raise OpenClawAgentError(f"agent {resolved_agent_id!r} not available after creation attempt")
        _ready_agents.add(resolved_agent_id)
        return resolved_agent_id


@contextmanager
def _serialized_agent_call(agent_id: str):
    with _agent_lock:
        lock = _agent_call_locks.setdefault(agent_id, threading.Lock())
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


def _mark_rate_limited(stderr: str) -> None:
    global _rate_limit_until

    message = stderr.lower()
    if any(hint in message for hint in _RATE_LIMIT_HINTS):
        with _agent_lock:
            _rate_limit_until = time.monotonic() + DEFAULT_RATE_LIMIT_BACKOFF_SECONDS
        log.warning("[AGENT] rate limit detected, backing off %ss", DEFAULT_RATE_LIMIT_BACKOFF_SECONDS)


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _extract_content(text: str) -> str:
    """Extract assistant text from raw or structured OpenClaw output."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text.strip()

    if isinstance(data, dict):
        output = data.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            block_text = block.get("text")
                            if isinstance(block_text, str) and block_text.strip():
                                parts.append(block_text.strip())
                item_text = item.get("text")
                if isinstance(item_text, str) and item_text.strip():
                    parts.append(item_text.strip())
            if parts:
                return "\n".join(parts).strip()

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()

        for key in ("content", "text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return text.strip()


def call_agent(
    prompt: str,
    *,
    timeout: float = DEFAULT_CLI_TIMEOUT,
    purge_sessions: bool = True,
) -> EnrichResponse:
    """Call the dedicated OpenClaw agent with benchmark-skill session hygiene."""
    started_at = time.monotonic()
    if time.monotonic() < _rate_limit_until:
        remaining = int(_rate_limit_until - time.monotonic())
        return EnrichResponse(
            content="",
            success=False,
            source="benchmark_skill",
            error=f"rate limit backoff in effect ({remaining}s remaining)",
        )

    try:
        agent_id = ensure_agent()
        session_id = _runtime_session_id(agent_id)
        openclaw = _resolve_openclaw_path()
    except OpenClawAgentError as exc:
        return EnrichResponse(content="", success=False, source="benchmark_skill", error=str(exc))

    with _serialized_agent_call(agent_id):
        log.info(
            "[AGENT] CLI start agent_id=%s session_id=%s prompt_chars=%d timeout=%.1fs purge_sessions=%s",
            agent_id,
            session_id,
            len(prompt),
            timeout,
            purge_sessions,
        )

        if purge_sessions:
            _purge_agent_sessions(agent_id)

        try:
            proc = subprocess.Popen(
                [
                    openclaw,
                    "agent",
                    "--agent",
                    agent_id,
                    "--session-id",
                    session_id,
                    "--message",
                    prompt,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (FileNotFoundError, OSError) as exc:
            return EnrichResponse(content="", success=False, source="benchmark_skill", error=str(exc))

        timed_out = False
        deadline = time.monotonic() + timeout
        try:
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    timed_out = True
                    _terminate_process(proc)
                    break
                time.sleep(0.25)

            stdout = proc.stdout.read() if proc.stdout else ""
            stderr = proc.stderr.read() if proc.stderr else ""
        finally:
            if purge_sessions:
                _purge_agent_sessions(agent_id)

    if timed_out:
        log.warning(
            "[AGENT] CLI end agent_id=%s session_id=%s status=timeout elapsed_ms=%d",
            agent_id,
            session_id,
            int((time.monotonic() - started_at) * 1000),
        )
        return EnrichResponse(
            content="",
            success=False,
            source="benchmark_skill",
            error=f"CLI timeout ({timeout}s)",
        )

    if proc.returncode != 0:
        error_msg = stderr.strip() or f"exit code {proc.returncode}"
        _mark_rate_limited(error_msg)
        log.warning(
            "[AGENT] CLI end agent_id=%s session_id=%s status=failed elapsed_ms=%d returncode=%s error=%s",
            agent_id,
            session_id,
            int((time.monotonic() - started_at) * 1000),
            proc.returncode,
            error_msg[:200],
        )
        return EnrichResponse(
            content="",
            success=False,
            source="benchmark_skill",
            error=error_msg,
        )

    if not stdout.strip():
        log.warning(
            "[AGENT] CLI end agent_id=%s session_id=%s status=failed elapsed_ms=%d error=empty response",
            agent_id,
            session_id,
            int((time.monotonic() - started_at) * 1000),
        )
        return EnrichResponse(
            content="",
            success=False,
            source="benchmark_skill",
            error="empty response",
        )

    content = _extract_content(stdout.strip())
    if not content:
        log.warning(
            "[AGENT] CLI end agent_id=%s session_id=%s status=failed elapsed_ms=%d error=unable to extract response content",
            agent_id,
            session_id,
            int((time.monotonic() - started_at) * 1000),
        )
        return EnrichResponse(
            content="",
            success=False,
            source="benchmark_skill",
            error="unable to extract response content",
        )

    log.info(
        "[AGENT] CLI end agent_id=%s session_id=%s status=success elapsed_ms=%d response_chars=%d",
        agent_id,
        session_id,
        int((time.monotonic() - started_at) * 1000),
        len(content),
    )
    return EnrichResponse(
        content=content,
        success=True,
        source="benchmark_skill",
        model="openclaw/agent",
    )


def parse_json_response(content: str) -> dict[str, Any] | list[Any]:
    """Parse JSON from an agent response. Delegates to the robust llm_client parser."""
    from crawler.enrich.generative.llm_client import parse_json_response as _parse
    result = _parse(content)
    return result if result is not None else {"raw": content}


async def enrich_with_llm(
    prompt: str,
    *,
    timeout: float = DEFAULT_CLI_TIMEOUT,
) -> EnrichResponse:
    """Async wrapper around the benchmark-skill style OpenClaw agent call."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: call_agent(prompt, timeout=timeout))
