"""OpenClaw CLI wrapper for LLM calls."""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

log = logging.getLogger("validator.llm")

DEFAULT_OPENCLAW_CLI = "openclaw"
DEFAULT_TIMEOUT = 120


def _purge_openclaw_sessions() -> None:
    """Delete all session transcripts to prevent context overflow.

    OpenClaw session structure:
      ~/.openclaw/agents/{agent_id}/sessions/
        sessions.json   (index)
        {uuid}.jsonl     (transcript — grows unbounded)
        {uuid}.jsonl.lock

    We purge ALL agent session dirs, not just a specific agent,
    since `openclaw chat` may use different agent IDs.
    """
    agents_dir = Path.home() / ".openclaw" / "agents"
    if not agents_dir.is_dir():
        return
    count = 0
    for agent_dir in agents_dir.iterdir():
        session_dir = agent_dir / "sessions"
        if not session_dir.is_dir():
            continue
        for f in session_dir.iterdir():
            try:
                if f.name == "sessions.json":
                    f.write_text("{}")
                    count += 1
                elif f.suffix in (".jsonl", ".lock"):
                    f.unlink()
                    count += 1
            except OSError:
                pass
    if count > 0:
        log.info("purged %d openclaw session files", count)


def call_openclaw(
    prompt: str,
    *,
    cli_path: str = DEFAULT_OPENCLAW_CLI,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    Call OpenClaw CLI with a prompt and return the response.
    Purges session files before each call to prevent context overflow.

    Args:
        prompt: The prompt to send to the LLM.
        cli_path: Path to the openclaw CLI binary.
        timeout: Timeout in seconds.

    Returns:
        Raw stdout from the CLI.

    Raises:
        RuntimeError: If the CLI exits with non-zero status.
        subprocess.TimeoutExpired: If the call times out.
    """
    _purge_openclaw_sessions()

    try:
        result = subprocess.run(
            [cli_path, "chat", "-m", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"OpenClaw CLI not found at '{cli_path}'") from exc

    if result.returncode != 0:
        raise RuntimeError(f"OpenClaw CLI failed: {result.stderr}")

    return result.stdout


def parse_json_response(response: str) -> dict[str, Any]:
    """
    Extract JSON object from LLM response.

    LLM responses may contain markdown or explanatory text around the JSON.
    This function finds and parses the first valid JSON object.

    Args:
        response: Raw LLM response text.

    Returns:
        Parsed JSON as dict, or empty dict if no valid JSON found.
    """
    # Try to find JSON object pattern
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, response, re.DOTALL)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    # Fallback: try parsing the entire response
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        log.warning("Could not parse JSON from response: %s", response[:200])
        return {}
