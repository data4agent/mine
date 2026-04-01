from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from worker_state import WorkerStateStore


class _FakeClient:
    def __init__(self) -> None:
        self.datasets = [
            {"id": "wiki-articles", "source_domains": ["en.wikipedia.org"]},
            {"id": "arxiv-papers", "source_domains": ["arxiv.org"]},
        ]

    def list_datasets(self) -> list[dict]:
        return list(self.datasets)


def test_render_first_load_experience_contains_welcome_and_dependency_guidance(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(workspace_tmp_path / "social-data-crawler"))
    (workspace_tmp_path / "social-data-crawler").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PLATFORM_BASE_URL", "http://101.47.73.95")
    monkeypatch.setenv("AWP_WALLET_TOKEN", "token-ready")

    from skill_runtime import render_first_load_experience

    text = render_first_load_experience()

    assert "Welcome to Mine" in text
    assert "Quick start" in text
    assert "start working" in text
    assert "check status" in text
    assert "list datasets" in text
    assert "Security:" in text
    assert "AWP Wallet" in text
    assert "social-data-crawler" in text
    assert "All dependencies ready." in text


def test_render_first_load_experience_surfaces_missing_dependency_actions(monkeypatch) -> None:
    monkeypatch.delenv("SOCIAL_CRAWLER_ROOT", raising=False)
    monkeypatch.delenv("PLATFORM_BASE_URL", raising=False)
    monkeypatch.delenv("AWP_WALLET_TOKEN", raising=False)
    monkeypatch.setenv("AWP_WALLET_BIN", "awp-wallet")

    from skill_runtime import render_first_load_experience

    text = render_first_load_experience()

    assert "check again" in text
    assert "unlock --duration 3600" in text
    assert "social-data-crawler" in text
    assert "Platform Service base URL" in text


def test_render_status_summary_includes_state_counts(workspace_tmp_path, monkeypatch) -> None:
    from skill_runtime import render_status_summary

    state_store = WorkerStateStore(workspace_tmp_path / "state")
    state_store._write_json(state_store._backlog_path, [{"item_id": "a"}])
    state_store._write_json(state_store._auth_pending_path, [{"item_id": "b"}])
    state_store._write_json(state_store._submit_pending_path, [{"item_id": "c"}])
    worker = SimpleNamespace(
        state_store=state_store,
        client=_FakeClient(),
        config=SimpleNamespace(miner_id="miner-001", base_url="http://101.47.73.95"),
        check_status=lambda: {
            "mining_state": "idle",
            "epoch_submitted": 0,
            "epoch_target": 80,
            "queues": {
                "backlog": 1,
                "auth_pending": 1,
                "submit_pending": 1,
            },
            "settlement": {},
        },
    )

    text = render_status_summary(worker)

    assert "Mine status" in text
    assert "miner-001" in text
    assert "Known active datasets" in text
    assert "Backlog" in text
    assert "Auth pending" in text
    assert "Submit pending" in text


def test_render_dataset_listing_formats_dataset_output(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(workspace_tmp_path / "social-data-crawler"))
    (workspace_tmp_path / "social-data-crawler").mkdir(parents=True, exist_ok=True)

    from skill_runtime import render_dataset_listing

    text = render_dataset_listing(_FakeClient())

    assert "Active datasets" in text
    assert "wiki-articles" in text
    assert "arxiv-papers" in text
