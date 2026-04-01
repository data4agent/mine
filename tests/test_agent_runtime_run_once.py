from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from pow_solver import UnsupportedChallenge
from run_artifacts import RunArtifactWriter
from run_models import CrawlerRunResult, WorkItem
import httpx


CRAWLER_WORKTREE = (Path(__file__).resolve().parents[2] / ".worktrees" / "social-data-crawler-e2e-run-once").resolve()


def test_run_artifact_writer_persists_challenge_payload(workspace_tmp_path) -> None:
    writer = RunArtifactWriter(workspace_tmp_path / "run-1")
    challenge = {"id": "pow-1", "question_type": "unknown", "prompt": "solve me"}

    writer.write_json("preflight/challenge.json", challenge)

    stored = (workspace_tmp_path / "run-1" / "preflight" / "challenge.json").read_text(encoding="utf-8")
    assert '"id": "pow-1"' in stored


def test_unsupported_challenge_is_explicit() -> None:
    error = UnsupportedChallenge("unknown")

    assert str(error) == "unsupported challenge type: unknown"


class _FakeClient:
    def send_unified_heartbeat(self, *, client_name: str, ip_address: str = "") -> dict:
        return {"ok": True}

    def send_miner_heartbeat(self, *, client_name: str) -> None:
        return None

    def check_url_occupancy(self, dataset_id: str, url: str) -> dict:
        return {"occupied": False}

    def submit_preflight(self, dataset_id: str, epoch_id: str) -> dict:
        return {"data": {"allowed": True, "challenge": {"id": "pow-1", "question_type": "unknown"}}}


class _FakeRunner:
    def __init__(self, result: CrawlerRunResult, *, output_root: Path | None = None) -> None:
        self.result = result
        self.output_root = output_root or result.output_dir.parent

    def run_item(self, item: WorkItem, command: str) -> CrawlerRunResult:
        self.result.output_dir.mkdir(parents=True, exist_ok=True)
        return self.result


class _FakeLocalClient(_FakeClient):
    def __init__(self) -> None:
        self.submissions: list[dict] = []
        self.datasets = [
            {"id": "dataset-1", "source_domains": ["en.wikipedia.org"]},
            {"id": "dataset-2", "source_domains": ["arxiv.org"]},
        ]

    def submit_preflight(self, dataset_id: str, epoch_id: str) -> dict:
        return {"data": {"allowed": True}}

    def fetch_dataset(self, dataset_id: str) -> dict:
        return {
            "id": dataset_id,
            "schema": {
                "content": {"type": "string", "required": True},
                "url": {"type": "string", "required": True},
            },
        }

    def submit_core_submissions(self, payload: dict) -> dict:
        self.submissions.append(payload)
        return {"data": [{"id": "submission-1", "payload": payload}]}

    def list_datasets(self) -> list[dict]:
        return list(self.datasets)


class _CaptchaRunner(_FakeRunner):
    pass


class _RateLimitedClient(_FakeLocalClient):
    def submit_core_submissions(self, payload: dict) -> dict:
        request = httpx.Request("POST", "http://example.test/api/core/v1/submissions")
        response = httpx.Response(429, request=request, headers={"Retry-After": "300"})
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)


class _UnauthorizedClient(_FakeClient):
    def claim_repeat_crawl_task(self) -> dict:
        request = httpx.Request("POST", "http://example.test/api/mining/v1/repeat-crawl-tasks/claim")
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    def claim_refresh_task(self) -> None:
        return None

    def list_datasets(self) -> list[dict]:
        return []


class _MissingSignatureTransport:
    def request(self, method: str, path: str, **kwargs):
        request = httpx.Request(method, f"http://example.test{path}")
        response = httpx.Response(
            401,
            request=request,
            json={
                "error": {
                    "code": "MISSING_HEADERS",
                    "message": "missing required signature headers",
                },
                "success": False,
            },
        )
        raise httpx.HTTPStatusError("missing signature", request=request, response=response)


def test_run_once_returns_explicit_unsolved_challenge_state(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import run_single_item_for_test

    result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out",
        records=[{"canonical_url": "https://example.com", "structured": {}, "plain_text": "hello", "crawl_timestamp": "2026-04-01T00:00:00Z"}],
        errors=[],
        summary={},
        exit_code=0,
        argv=["python", "-m", "crawler"],
    )
    item = WorkItem(
        item_id="backend_claim:repeat_crawl:task-1",
        source="backend_claim",
        url="https://example.com",
        dataset_id="dataset-1",
        platform="generic",
        resource_type="page",
        record={"url": "https://example.com", "platform": "generic", "resource_type": "page"},
        claim_task_id="task-1",
        claim_task_type="repeat_crawl",
        metadata={"epoch_id": "epoch-1"},
    )

    summary = run_single_item_for_test(
        item=item,
        client=_FakeClient(),
        runner=_FakeRunner(result),
        root=workspace_tmp_path,
    )

    assert summary["terminal_state"] == "challenge_received_but_unsolved"
    assert (workspace_tmp_path / "run-artifacts" / "preflight" / "challenge.json").exists()


def test_process_task_payload_accepts_local_task_envelope(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import AgentWorker, _build_test_config

    result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out",
        records=[{"canonical_url": "https://example.com", "structured": {}, "plain_text": "hello", "crawl_timestamp": "2026-04-01T00:00:00Z"}],
        errors=[],
        summary={},
        exit_code=0,
        argv=["python", "-m", "crawler"],
    )
    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_FakeRunner(result),
        config=_build_test_config(workspace_tmp_path),
    )

    message = worker.process_task_payload(
        "local_crawl",
        {
            "task_id": "local-1",
            "url": "https://example.com",
        },
    )

    assert "processed local_crawl:local-1" in message


def test_run_iteration_surfaces_claim_error_without_crashing(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import AgentWorker, _build_test_config

    result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out",
        records=[],
        errors=[],
        summary={},
        exit_code=0,
        argv=["python", "-m", "crawler"],
    )
    worker = AgentWorker(
        client=_UnauthorizedClient(),
        runner=_FakeRunner(result),
        config=_build_test_config(workspace_tmp_path),
    )

    summary = worker.run_iteration(1)

    assert any("claim source failed" in error for error in summary["errors"])


def test_run_once_returns_claim_error_before_no_task_message(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import AgentWorker, _build_test_config

    result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out",
        records=[],
        errors=[],
        summary={},
        exit_code=0,
        argv=["python", "-m", "crawler"],
    )
    worker = AgentWorker(
        client=_UnauthorizedClient(),
        runner=_FakeRunner(result),
        config=_build_test_config(workspace_tmp_path),
    )

    message = worker.run_once()

    assert "claim source failed" in message
    assert (workspace_tmp_path / "_run_once" / "last-summary.json").exists()


def test_captcha_error_moves_item_to_auth_pending(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import AgentWorker, _build_test_config

    result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out",
        records=[],
        errors=[{"error_code": "CAPTCHA", "retryable": False, "next_action": "complete login in auto-browser and retry"}],
        summary={},
        exit_code=1,
        argv=["python", "-m", "crawler"],
    )
    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_CaptchaRunner(result),
        config=_build_test_config(workspace_tmp_path),
    )

    summary = worker.process_task_payload(
        "local_crawl",
        {
            "task_id": "local-captcha",
            "url": "https://example.com/captcha",
        },
    )

    assert "CAPTCHA" in summary
    auth_pending = worker.state_store.load_auth_pending()
    assert len(auth_pending) == 1
    assert auth_pending[0]["item_id"] == "local_crawl:local-captcha"
    assert auth_pending[0]["error"]["next_action"] == "complete login in auto-browser and retry"
    assert auth_pending[0]["error"]["public_url"] == "https://example.com/captcha"


def test_auth_pending_item_resumes_and_clears_after_success(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import AgentWorker, _build_test_config

    config = replace(_build_test_config(workspace_tmp_path), auth_retry_interval_seconds=0)
    first_result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out-1",
        records=[],
        errors=[{"error_code": "CAPTCHA", "retryable": False, "next_action": "complete login in auto-browser and retry"}],
        summary={},
        exit_code=1,
        argv=["python", "-m", "crawler"],
    )
    second_result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out-1",
        records=[{"canonical_url": "https://example.com/captcha", "structured": {}, "plain_text": "ok"}],
        errors=[],
        summary={},
        exit_code=0,
        argv=["python", "-m", "crawler"],
    )

    class _SequenceRunner:
        def __init__(self, *results: CrawlerRunResult) -> None:
            self._results = list(results)
            self.output_root = workspace_tmp_path / "outputs"

        def run_item(self, item: WorkItem, command: str) -> CrawlerRunResult:
            return self._results.pop(0)

    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_SequenceRunner(first_result, second_result),
        config=config,
    )

    worker.process_task_payload(
        "local_crawl",
        {
            "task_id": "local-captcha",
            "url": "https://example.com/captcha",
        },
    )

    summary = worker.run_iteration(2)

    assert summary["resumed_items"] == 1
    assert summary["processed_items"] == 1
    assert worker.state_store.load_auth_pending() == []


def test_successful_reprocess_clears_stale_submit_pending_entry(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import AgentWorker, _build_test_config

    result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out",
        records=[{
            "canonical_url": "https://example.com/retry",
            "structured": {},
            "plain_text": "fresh content",
            "crawl_timestamp": "2026-03-31T10:00:00Z",
        }],
        errors=[],
        summary={},
        exit_code=0,
        argv=["python", "-m", "crawler"],
    )
    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_FakeRunner(result),
        config=_build_test_config(workspace_tmp_path),
    )

    stale_item = WorkItem(
        item_id="local_crawl:retry-1",
        source="local_file",
        url="https://example.com/retry",
        dataset_id="dataset-1",
        platform="generic",
        resource_type="page",
        record={"url": "https://example.com/retry", "platform": "generic", "resource_type": "page"},
    )
    worker.state_store.enqueue_submit_pending(
        stale_item,
        {
            "record": {
                "canonical_url": "https://example.com/retry",
                "structured": {},
                "plain_text": "stale content",
                "crawl_timestamp": "2026-03-31T09:00:00Z",
            },
            "report_result": None,
        },
    )

    worker.process_task_payload(
        "local_crawl",
        {
            "task_id": "retry-1",
            "url": "https://example.com/retry",
            "dataset_id": "dataset-1",
        },
    )

    assert worker.state_store.load_submit_pending() == []


def test_platform_client_surfaces_missing_signature_hint(monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import PlatformClient

    client = PlatformClient(
        base_url="http://example.test",
        token="",
        miner_id="miner-test",
        signer=None,
    )
    client._client = _MissingSignatureTransport()

    with __import__("pytest").raises(RuntimeError) as exc_info:
        client.send_miner_heartbeat(client_name="mine/0.2")

    assert "awpWalletToken" in str(exc_info.value)


def test_wikipedia_submission_payload_fills_required_schema_fields(monkeypatch) -> None:
    monkeypatch.setenv(
        "SOCIAL_CRAWLER_ROOT",
        str(CRAWLER_WORKTREE),
    )
    from agent_runtime import _augment_submission_payload_for_dataset

    payload = {
        "dataset_id": "dataset-1",
        "entries": [
            {
                "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
                "cleaned_data": "Artificial intelligence article body",
                "structured_data": {
                    "categories": ["Artificial intelligence"],
                },
                "crawl_timestamp": "2026-03-31T08:00:00Z",
            }
        ],
    }
    dataset = {
        "schema": {
            "title": {"type": "string", "required": True},
            "content": {"type": "string", "required": True},
            "url": {"type": "string", "required": True},
            "categories": {"type": "string[]", "required": False},
        }
    }
    record = {
        "canonical_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "plain_text": "Artificial intelligence article body",
        "crawl_timestamp": "2026-03-31T12:00:00Z",
        "metadata": {"title": "Artificial intelligence"},
        "structured": {"categories": ["Artificial intelligence"]},
    }
    item = WorkItem(
        item_id="refresh:wiki-1",
        source="backend_claim",
        url="https://en.wikipedia.org/wiki/Artificial_intelligence",
        dataset_id="dataset-1",
        platform="wikipedia",
        resource_type="article",
        record={"platform": "wikipedia", "resource_type": "article", "title": "Artificial intelligence"},
    )

    _augment_submission_payload_for_dataset(payload, dataset=dataset, record=record, item=item)

    assert payload["entries"][0]["structured_data"] == {
        "title": "Artificial intelligence",
        "content": "Artificial intelligence article body",
        "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "categories": ["Artificial intelligence"],
    }


def test_agent_runtime_imports_with_current_social_data_crawler_layout(monkeypatch) -> None:
    current_crawler_root = (Path(__file__).resolve().parents[2] / "social-data-crawler").resolve()
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(current_crawler_root))
    sys.modules.pop("agent_runtime", None)
    for module_name in tuple(sys.modules):
        if module_name == "crawler" or module_name.startswith("crawler."):
            sys.modules.pop(module_name, None)

    import agent_runtime

    assert callable(agent_runtime.export_core_submissions)


def test_crawler_runner_injects_openclaw_model_config_for_run_command(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "gateway-token")

    import agent_runtime
    from agent_runtime import CrawlerRunner, _build_test_config

    captured = {}

    def fake_run(argv, cwd, capture_output, text):
        captured["argv"] = list(argv)
        captured["cwd"] = cwd
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(agent_runtime.subprocess, "run", fake_run)
    config = replace(
        _build_test_config(workspace_tmp_path),
        openclaw_enrich_enabled=True,
        openclaw_model_config={
            "provider": "openclaw",
            "base_url": "http://127.0.0.1:18789/v1",
            "api_key": "gateway-token",
            "model": "openclaw/default",
        },
    )
    runner = CrawlerRunner(config)
    item = WorkItem(
        item_id="local_crawl:llm-1",
        source="local_file",
        url="https://example.com/llm",
        dataset_id=None,
        platform="generic",
        resource_type="page",
        record={"url": "https://example.com/llm", "platform": "generic", "resource_type": "page"},
    )

    result = runner.run_item(item, "run")

    assert result.exit_code == 0
    argv = captured["argv"]
    assert "--model-config" in argv
    model_config_path = Path(argv[argv.index("--model-config") + 1])
    assert model_config_path.exists()
    assert json.loads(model_config_path.read_text(encoding="utf-8")) == {
        "provider": "openclaw",
        "base_url": "http://127.0.0.1:18789/v1",
        "api_key": "gateway-token",
        "model": "openclaw/default",
    }


def test_build_worker_from_env_resolves_openclaw_secretref_token(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    monkeypatch.setenv("PLATFORM_BASE_URL", "http://example.test")
    monkeypatch.setenv("MINER_ID", "miner-test")
    monkeypatch.setenv("CRAWLER_OUTPUT_ROOT", str(workspace_tmp_path / "outputs"))
    monkeypatch.setenv("WORKER_STATE_ROOT", str(workspace_tmp_path / "state"))
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)

    secret_path = workspace_tmp_path / "gateway-token.json"
    secret_path.write_text(json.dumps({"token": "secretref-token"}), encoding="utf-8")
    openclaw_config_path = workspace_tmp_path / "openclaw.json"
    openclaw_config_path.write_text(
        json.dumps(
            {
                "gateway": {
                    "auth": {
                        "token": {
                            "source": "file",
                            "provider": "localfile",
                            "id": "/token",
                        }
                    }
                },
                "secrets": {
                    "providers": {
                        "localfile": {
                            "source": "file",
                            "path": str(secret_path),
                            "mode": "json",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config_path))

    from agent_runtime import build_worker_from_env

    worker = build_worker_from_env()

    assert worker.config.openclaw_enrich_enabled is True
    assert worker.config.openclaw_model_config["api_key"] == "secretref-token"


def test_build_worker_from_env_resolves_awp_wallet_token_secretref(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    monkeypatch.setenv("PLATFORM_BASE_URL", "http://example.test")
    monkeypatch.setenv("MINER_ID", "miner-test")
    monkeypatch.setenv("CRAWLER_OUTPUT_ROOT", str(workspace_tmp_path / "outputs"))
    monkeypatch.setenv("WORKER_STATE_ROOT", str(workspace_tmp_path / "state"))
    monkeypatch.setenv("AWP_WALLET_BIN", "awp-wallet")
    monkeypatch.setenv(
        "AWP_WALLET_TOKEN_SECRET_REF",
        json.dumps({"source": "file", "provider": "localfile", "id": "/token"}),
    )
    monkeypatch.delenv("AWP_WALLET_TOKEN", raising=False)

    secret_path = workspace_tmp_path / "wallet-token.json"
    secret_path.write_text(json.dumps({"token": "wallet-secretref-token"}), encoding="utf-8")
    openclaw_config_path = workspace_tmp_path / "openclaw.json"
    openclaw_config_path.write_text(
        json.dumps(
            {
                "secrets": {
                    "providers": {
                        "localfile": {
                            "source": "file",
                            "path": str(secret_path),
                            "mode": "json",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(openclaw_config_path))

    from common import resolve_wallet_config

    wallet_bin, wallet_token = resolve_wallet_config()

    assert wallet_bin == "awp-wallet"
    assert wallet_token == "wallet-secretref-token"


def test_export_and_submit_falls_back_to_create_when_report_submission_is_missing(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    from agent_runtime import _export_and_submit_core_submissions_for_task

    class _FallbackClient(_FakeLocalClient):
        def fetch_core_submission(self, submission_id: str) -> dict:
            request = httpx.Request("GET", f"http://example.test/api/core/v1/submissions/{submission_id}")
            response = httpx.Response(404, request=request, json={"error": {"code": "NOT_FOUND"}})
            raise httpx.HTTPStatusError("not found", request=request, response=response)

    client = _FallbackClient()
    output_dir = workspace_tmp_path / "crawl-out"
    output_dir.mkdir(parents=True, exist_ok=True)
    item = WorkItem(
        item_id="refresh:wiki-fallback",
        source="backend_claim",
        url="https://en.wikipedia.org/wiki/Artificial_intelligence",
        dataset_id="dataset-1",
        platform="wikipedia",
        resource_type="article",
        record={"platform": "wikipedia", "resource_type": "article"},
    )
    record = {
        "canonical_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "plain_text": "Artificial intelligence article body",
        "crawl_timestamp": "2026-03-31T12:00:00Z",
        "metadata": {"title": "Artificial intelligence"},
        "structured": {"categories": ["Artificial intelligence"]},
    }

    export_path, response_path = _export_and_submit_core_submissions_for_task(
        client,
        output_dir,
        record,
        item,
        report_result={"data": {"submission_id": "sub_fake_not_created"}},
    )

    assert export_path.exists()
    assert response_path.exists()
    assert len(client.submissions) == 1
    response_payload = json.loads(response_path.read_text(encoding="utf-8"))
    assert response_payload["data"][0]["id"] == "submission-1"


def test_check_status_returns_session_and_queue_summary(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    from agent_runtime import AgentWorker, _build_test_config

    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_FakeRunner(
            CrawlerRunResult(
                output_dir=workspace_tmp_path / "crawl-out",
                records=[],
                errors=[],
                summary={},
                exit_code=0,
                argv=["python", "-m", "crawler"],
            )
        ),
        config=_build_test_config(workspace_tmp_path),
    )
    worker.state_store.save_session({"mining_state": "paused", "epoch_submitted": 43, "epoch_target": 80})

    status = worker.check_status()

    assert status["mining_state"] == "paused"
    assert status["epoch_submitted"] == 43
    assert status["epoch_target"] == 80
    assert "queues" in status


def test_pause_resume_and_stop_update_session_state(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    from agent_runtime import AgentWorker, _build_test_config

    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_FakeRunner(
            CrawlerRunResult(
                output_dir=workspace_tmp_path / "crawl-out",
                records=[],
                errors=[],
                summary={},
                exit_code=0,
                argv=["python", "-m", "crawler"],
            )
        ),
        config=_build_test_config(workspace_tmp_path),
    )

    paused = worker.pause()
    resumed = worker.resume()
    stopped = worker.stop()

    assert paused["mining_state"] == "paused"
    assert resumed["mining_state"] == "running"
    assert stopped["mining_state"] == "stopped"


def test_run_iteration_respects_paused_session(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    from agent_runtime import AgentWorker, _build_test_config

    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_FakeRunner(
            CrawlerRunResult(
                output_dir=workspace_tmp_path / "crawl-out",
                records=[],
                errors=[],
                summary={},
                exit_code=0,
                argv=["python", "-m", "crawler"],
            )
        ),
        config=_build_test_config(workspace_tmp_path),
    )
    worker.state_store.save_session({"mining_state": "paused"})

    summary = worker.run_iteration(1)

    assert summary["processed_items"] == 0
    assert any("paused" in message for message in summary["messages"])


def test_start_working_persists_selected_datasets(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    from agent_runtime import AgentWorker, _build_test_config

    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_FakeRunner(
            CrawlerRunResult(
                output_dir=workspace_tmp_path / "crawl-out",
                records=[],
                errors=[],
                summary={},
                exit_code=0,
                argv=["python", "-m", "crawler"],
            )
        ),
        config=_build_test_config(workspace_tmp_path),
    )

    result = worker.start_working(selected_dataset_ids=["dataset-2"])

    assert result["mining_state"] == "running"
    assert result["selected_dataset_ids"] == ["dataset-2"]
    assert worker.state_store.load_session()["selected_dataset_ids"] == ["dataset-2"]


def test_selected_datasets_filter_discovery_items(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    from agent_runtime import AgentWorker, _build_test_config

    worker = AgentWorker(
        client=_FakeLocalClient(),
        runner=_FakeRunner(
            CrawlerRunResult(
                output_dir=workspace_tmp_path / "crawl-out",
                records=[],
                errors=[],
                summary={},
                exit_code=0,
                argv=["python", "-m", "crawler"],
            )
        ),
        config=replace(_build_test_config(workspace_tmp_path), dataset_refresh_seconds=0),
    )
    worker.state_store.save_session({"mining_state": "running", "selected_dataset_ids": ["dataset-2"]})

    summary = worker.run_iteration(1)

    assert summary["discovery_items"] == 1


def test_rate_limit_marks_dataset_cooldown_and_defers_item(workspace_tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SOCIAL_CRAWLER_ROOT", str(CRAWLER_WORKTREE))
    from agent_runtime import AgentWorker, _build_test_config

    result = CrawlerRunResult(
        output_dir=workspace_tmp_path / "crawl-out",
        records=[{"canonical_url": "https://example.com", "structured": {}, "plain_text": "hello", "crawl_timestamp": "2026-04-01T00:00:00Z"}],
        errors=[],
        summary={},
        exit_code=0,
        argv=["python", "-m", "crawler"],
    )
    worker = AgentWorker(
        client=_RateLimitedClient(),
        runner=_FakeRunner(result),
        config=_build_test_config(workspace_tmp_path),
    )

    message = worker.process_task_payload(
        "local_crawl",
        {
            "task_id": "local-429",
            "url": "https://example.com",
            "dataset_id": "dataset-1",
        },
    )

    assert "429" in message or "cooldown" in message
    assert worker.state_store.is_dataset_available("dataset-1", now=0) is not True
