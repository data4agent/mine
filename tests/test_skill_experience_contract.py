from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_skill_contains_productized_first_load_experience() -> None:
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "Welcome to Mine" in content
    assert "Quick start" in content
    assert "start working" in content
    assert "check status" in content
    assert "list datasets" in content
    assert "Security:" in content
    assert "private keys never leave awp-wallet" in content
    assert "Dependency check" in content
    assert "AWP Wallet" in content
    assert "social-data-crawler" in content
    assert "Platform Service base URL" in content
    assert "check again" in content


def test_skill_contains_openclaw_tool_priority_and_control_language() -> None:
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "mine_worker" in content
    assert "recommended default" in content
    assert "mine_run_once" in content
    assert "mine_process_task_file" in content
    assert "mine_heartbeat" in content
    assert "pause" in content
    assert "resume" in content
    assert "stop" in content
    assert "current batch" in content


def test_skill_contains_progress_and_recovery_guidance() -> None:
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "finding URLs" in content
    assert "dedup check" in content
    assert "preflight" in content
    assert "PoW" in content
    assert "crawling" in content
    assert "structuring" in content
    assert "submitting" in content
    assert "429" in content
    assert "AUTH_REQUIRED" in content
    assert "unlock --duration 3600" in content
