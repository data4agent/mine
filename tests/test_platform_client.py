"""platform_client 模块的全面测试."""
from __future__ import annotations

import re
import time
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import httpx
import pytest

from platform_client import PlatformApiError, PlatformClient


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------
def _make_client(**overrides: Any) -> PlatformClient:
    """创建最小配置的 PlatformClient，跳过签名配置远程解析."""
    defaults = {
        "base_url": "https://api.example.com",
        "token": "test-token",
        "signer": None,
        "eip712_chain_id": 1,
        "eip712_domain_name": "test",
        "eip712_domain_version": "1",
        "eip712_verifying_contract": "0x0000000000000000000000000000000000000000",
    }
    defaults.update(overrides)
    return PlatformClient(**defaults)


def _mock_response(
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
) -> httpx.Response:
    """构造 httpx.Response 用于 mock."""
    resp = httpx.Response(
        status_code=status_code,
        headers=headers or {},
        content=content if content is not None else b"",
        request=httpx.Request("GET", "https://api.example.com/test"),
    )
    if json_body is not None:
        # 用 json content 覆盖
        import json as _json
        body_bytes = _json.dumps(json_body).encode()
        resp = httpx.Response(
            status_code=status_code,
            headers={**(headers or {}), "content-type": "application/json"},
            content=body_bytes,
            request=httpx.Request("GET", "https://api.example.com/test"),
        )
    return resp


# ===========================================================================
# PlatformApiError 测试
# ===========================================================================
class TestPlatformApiError:
    def test_init_fields(self) -> None:
        err = PlatformApiError("ERR_CODE", "something failed", "validation", 422, {"raw": True})
        assert err.code == "ERR_CODE"
        assert err.category == "validation"
        assert err.status_code == 422
        assert err.response == {"raw": True}

    def test_str_representation(self) -> None:
        err = PlatformApiError("CODE_X", "msg here", "internal", 500)
        assert str(err) == "CODE_X: msg here"

    def test_response_defaults_none(self) -> None:
        err = PlatformApiError("C", "M", "cat", 400)
        assert err.response is None

    def test_inherits_exception(self) -> None:
        err = PlatformApiError("C", "M", "cat", 400)
        assert isinstance(err, Exception)


# ===========================================================================
# _regex_matches 测试
# ===========================================================================
class TestRegexMatches:
    def test_full_match(self) -> None:
        assert PlatformClient._regex_matches(r"https://example\.com/.*", "https://example.com/page") is True

    def test_partial_no_match(self) -> None:
        """fullmatch 要求完整匹配，部分匹配应失败."""
        assert PlatformClient._regex_matches(r"example", "example.com") is False

    def test_no_match(self) -> None:
        assert PlatformClient._regex_matches(r"https://foo\.com/.*", "https://bar.com/x") is False

    def test_invalid_regex_returns_false(self) -> None:
        assert PlatformClient._regex_matches(r"[invalid", "anything") is False

    def test_exact_string(self) -> None:
        assert PlatformClient._regex_matches("hello", "hello") is True


# ===========================================================================
# _build_occupancy_structured_data 测试
# ===========================================================================
class TestBuildOccupancyStructuredData:
    def test_defaults_set(self) -> None:
        result = PlatformClient._build_occupancy_structured_data("https://x.com", None)
        assert result == {"canonical_url": "https://x.com", "url": "https://x.com"}

    def test_existing_values_preserved(self) -> None:
        sd = {"canonical_url": "https://custom.com", "extra": "val"}
        result = PlatformClient._build_occupancy_structured_data("https://x.com", sd)
        assert result["canonical_url"] == "https://custom.com"
        assert result["url"] == "https://x.com"
        assert result["extra"] == "val"

    def test_empty_values_filtered(self) -> None:
        sd = {"canonical_url": "https://x.com", "empty_str": "", "none_val": None, "empty_list": [], "empty_dict": {}}
        result = PlatformClient._build_occupancy_structured_data("https://x.com", sd)
        assert "empty_str" not in result
        assert "none_val" not in result
        assert "empty_list" not in result
        assert "empty_dict" not in result

    def test_zero_and_false_kept(self) -> None:
        """0 和 False 不在过滤列表中，应保留."""
        sd = {"count": 0, "active": False}
        result = PlatformClient._build_occupancy_structured_data("https://x.com", sd)
        assert result["count"] == 0
        assert result["active"] is False


# ===========================================================================
# _coerce_url_patterns 测试
# ===========================================================================
class TestCoerceUrlPatterns:
    def test_list_of_strings(self) -> None:
        dataset = {"url_patterns": ["https://a\\.com/.*", "https://b\\.com/.*"]}
        result = PlatformClient._coerce_url_patterns(dataset)
        assert result == ["https://a\\.com/.*", "https://b\\.com/.*"]

    def test_non_list_returns_empty(self) -> None:
        assert PlatformClient._coerce_url_patterns({"url_patterns": "single"}) == []
        assert PlatformClient._coerce_url_patterns({"url_patterns": 42}) == []
        assert PlatformClient._coerce_url_patterns({}) == []

    def test_blank_strings_filtered(self) -> None:
        dataset = {"url_patterns": ["valid", "", "  ", "ok"]}
        result = PlatformClient._coerce_url_patterns(dataset)
        assert result == ["valid", "ok"]

    def test_none_patterns(self) -> None:
        assert PlatformClient._coerce_url_patterns({"url_patterns": None}) == []


# ===========================================================================
# _request 重试逻辑（基于 mock）
# ===========================================================================
class TestRequestRetryLogic:
    """测试 _request 的重试/退避行为."""

    def test_429_with_retry_after_platform_api_error(self) -> None:
        """PlatformApiError 路径下 429 + Retry-After 头的重试."""
        client = _make_client()
        # 第一次返回 429 (success:false envelope)，第二次成功
        resp_429 = _mock_response(200, json_body={
            "success": False,
            "error": {"code": "RATE_LIMITED", "message": "slow down", "category": "rate_limit"},
        }, headers={"Retry-After": "1"})
        resp_ok = _mock_response(200, json_body={"success": True, "data": {"ok": True}})

        with patch.object(client._client, "request", side_effect=[resp_429, resp_ok]) as mock_req, \
             patch("platform_client.time.sleep") as mock_sleep:
            result = client._request("GET", "/test", None)
            assert result["data"]["ok"] is True
            assert mock_req.call_count == 2
            # 应根据 Retry-After header 休眠
            mock_sleep.assert_called_once()
            sleep_val = mock_sleep.call_args[0][0]
            assert sleep_val <= 60.0

    def test_429_with_retry_after_http_status_error(self) -> None:
        """HTTPStatusError 路径下 429 + Retry-After 头的重试."""
        client = _make_client()
        resp_429 = _mock_response(429, headers={"Retry-After": "2"})
        resp_ok = _mock_response(200, json_body={"success": True, "data": {}})

        with patch.object(client._client, "request", side_effect=[resp_429, resp_ok]) as mock_req, \
             patch("platform_client.time.sleep") as mock_sleep:
            result = client._request("GET", "/test", None)
            assert mock_req.call_count == 2
            mock_sleep.assert_called_once()
            assert mock_sleep.call_args[0][0] == 2.0

    def test_500_server_error_retry(self) -> None:
        """500 错误应自动重试."""
        client = _make_client()
        resp_500 = _mock_response(500)
        resp_ok = _mock_response(200, json_body={"success": True, "value": 1})

        with patch.object(client._client, "request", side_effect=[resp_500, resp_ok]) as mock_req, \
             patch("platform_client.time.sleep"):
            result = client._request("GET", "/test", None)
            assert mock_req.call_count == 2
            assert result["value"] == 1

    def test_401_session_renewal(self) -> None:
        """401 SESSION_EXPIRED 应触发 session 更新后重试."""
        mock_signer = MagicMock()
        mock_signer.build_auth_headers.return_value = {"X-Auth": "sig"}
        mock_signer.renew_session.return_value = {"token": "new-token"}

        client = _make_client(signer=mock_signer)

        resp_401 = _mock_response(401, json_body={
            "error": {"code": "SESSION_EXPIRED", "message": "expired session token"},
        })
        resp_ok = _mock_response(200, json_body={"success": True, "data": {}})

        with patch.object(client._client, "request", side_effect=[resp_401, resp_ok]):
            result = client._request("GET", "/test", None)
            assert result["data"] == {}
            mock_signer.renew_session.assert_called_once()
            assert client._last_wallet_refresh == {"token": "new-token"}

    def test_unknown_category_defaults_to_500(self) -> None:
        """success:false 中未知 category 应映射到 status_code 500."""
        client = _make_client()
        resp = _mock_response(200, json_body={
            "success": False,
            "error": {"code": "WEIRD", "message": "huh", "category": "totally_unknown"},
        })
        resp_ok = _mock_response(200, json_body={"success": True})

        with patch.object(client._client, "request", side_effect=[resp, resp_ok]) as mock_req, \
             patch("platform_client.time.sleep"):
            # 未知 category → status 500 → 可重试
            result = client._request("GET", "/test", None)
            assert mock_req.call_count == 2

    def test_unknown_category_raises_after_max_retries(self) -> None:
        """未知 category 重试耗尽后应抛出 PlatformApiError."""
        client = _make_client()
        resp_fail = _mock_response(200, json_body={
            "success": False,
            "error": {"code": "WEIRD", "message": "huh", "category": "totally_unknown"},
        })

        with patch.object(client._client, "request", return_value=resp_fail), \
             patch("platform_client.time.sleep"):
            with pytest.raises(PlatformApiError) as exc_info:
                client._request("GET", "/test", None)
            assert exc_info.value.status_code == 500

    def test_success_false_envelope(self) -> None:
        """success:false 信封应抛出 PlatformApiError."""
        client = _make_client()
        resp = _mock_response(200, json_body={
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "gone", "category": "not_found"},
        })

        with patch.object(client._client, "request", return_value=resp):
            with pytest.raises(PlatformApiError) as exc_info:
                client._request("GET", "/test", None)
            assert exc_info.value.status_code == 404
            assert exc_info.value.code == "NOT_FOUND"

    def test_429_no_retry_after_uses_backoff(self) -> None:
        """429 without Retry-After 应使用默认退避."""
        client = _make_client()
        resp_429 = _mock_response(429)  # 无 Retry-After 头
        resp_ok = _mock_response(200, json_body={"success": True})

        with patch.object(client._client, "request", side_effect=[resp_429, resp_ok]), \
             patch("platform_client.time.sleep") as mock_sleep:
            client._request("GET", "/test", None)
            mock_sleep.assert_called_once()
            # 默认退避: max(2.0, 1.0 * attempt)，attempt=1 → 2.0
            assert mock_sleep.call_args[0][0] == 2.0

    def test_empty_response_content(self) -> None:
        """空响应体返回空字典."""
        client = _make_client()
        resp = _mock_response(200, content=b"")

        with patch.object(client._client, "request", return_value=resp):
            result = client._request("GET", "/test", None)
            assert result == {}


# ===========================================================================
# report_evaluation 测试
# ===========================================================================
class TestReportEvaluation:
    def test_request_body_includes_required_fields(self) -> None:
        """验证 report_evaluation 发送的请求体包含 assignment_id, result, score."""
        client = _make_client()
        resp = _mock_response(200, json_body={"success": True, "data": {"id": "eval-1"}})

        with patch.object(client._client, "request", return_value=resp) as mock_req:
            result = client.report_evaluation(
                "task-123", score=85, assignment_id="assign-456", result="match",
            )
            assert result["data"]["id"] == "eval-1"
            call_kwargs = mock_req.call_args
            body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert body["assignment_id"] == "assign-456"
            assert body["result"] == "match"
            assert body["score"] == 85

    def test_custom_result_value(self) -> None:
        client = _make_client()
        resp = _mock_response(200, json_body={"success": True, "data": {}})

        with patch.object(client._client, "request", return_value=resp) as mock_req:
            client.report_evaluation("t1", score=0, assignment_id="a1", result="mismatch")
            body = mock_req.call_args.kwargs.get("json") or mock_req.call_args[1].get("json")
            assert body["result"] == "mismatch"


# ===========================================================================
# check_url_occupancy 测试
# ===========================================================================
class TestCheckUrlOccupancy:
    def test_404_returns_empty_dict(self) -> None:
        """PlatformApiError 404 应返回空字典."""
        client = _make_client()
        with patch.object(client, "_request", side_effect=PlatformApiError("NF", "not found", "not_found", 404)):
            result = client.check_url_occupancy("ds1", "https://example.com")
            assert result == {}

    def test_422_returns_empty_dict(self) -> None:
        """PlatformApiError 422 应返回空字典."""
        client = _make_client()
        with patch.object(client, "_request", side_effect=PlatformApiError("V", "invalid", "validation", 422)):
            result = client.check_url_occupancy("ds1", "https://example.com")
            assert result == {}

    def test_http_status_error_404(self) -> None:
        """HTTPStatusError 404 应返回空字典."""
        client = _make_client()
        resp_404 = _mock_response(404)
        error = httpx.HTTPStatusError("not found", request=resp_404.request, response=resp_404)
        with patch.object(client, "_request", side_effect=error):
            result = client.check_url_occupancy("ds1", "https://example.com")
            assert result == {}

    def test_http_status_error_422(self) -> None:
        """HTTPStatusError 422 应返回空字典."""
        client = _make_client()
        resp_422 = _mock_response(422)
        error = httpx.HTTPStatusError("invalid", request=resp_422.request, response=resp_422)
        with patch.object(client, "_request", side_effect=error):
            result = client.check_url_occupancy("ds1", "https://example.com")
            assert result == {}

    def test_other_error_propagated(self) -> None:
        """非 404/422 错误应向上抛出."""
        client = _make_client()
        with patch.object(client, "_request", side_effect=PlatformApiError("E", "err", "internal", 500)):
            with pytest.raises(PlatformApiError):
                client.check_url_occupancy("ds1", "https://example.com")

    def test_success_returns_data(self) -> None:
        client = _make_client()
        with patch.object(client, "_request", return_value={"data": {"occupied": True}}):
            result = client.check_url_occupancy("ds1", "https://example.com")
            assert result == {"occupied": True}

    def test_success_non_dict_data_returns_empty(self) -> None:
        client = _make_client()
        with patch.object(client, "_request", return_value={"data": "not a dict"}):
            result = client.check_url_occupancy("ds1", "https://example.com")
            assert result == {}


# ===========================================================================
# _validate_submission_payload 测试
# ===========================================================================
class TestValidateSubmissionPayload:
    def test_url_matches_pattern(self) -> None:
        """URL 匹配 pattern 时不应抛出异常."""
        client = _make_client()
        dataset = {"url_patterns": [r"https://example\.com/.*"]}
        with patch.object(client, "fetch_dataset", return_value=dataset):
            # 不应抛出
            client._validate_submission_payload({
                "dataset_id": "ds1",
                "entries": [{"url": "https://example.com/page"}],
            })

    def test_url_does_not_match_raises_runtime_error(self) -> None:
        """URL 不匹配任何 pattern 时应抛出 RuntimeError."""
        client = _make_client()
        dataset = {"url_patterns": [r"https://example\.com/.*"]}
        with patch.object(client, "fetch_dataset", return_value=dataset):
            with pytest.raises(RuntimeError, match="submission preflight failed"):
                client._validate_submission_payload({
                    "dataset_id": "ds1",
                    "entries": [{"url": "https://other.com/page"}],
                })

    def test_empty_dataset_id_skips_validation(self) -> None:
        """空 dataset_id 应跳过验证."""
        client = _make_client()
        # 不应调用 fetch_dataset
        client._validate_submission_payload({"dataset_id": "", "entries": [{"url": "x"}]})

    def test_no_entries_skips_validation(self) -> None:
        """没有 entries 或空列表应跳过验证."""
        client = _make_client()
        client._validate_submission_payload({"dataset_id": "ds1", "entries": []})
        client._validate_submission_payload({"dataset_id": "ds1"})

    def test_dataset_404_skips_validation(self) -> None:
        """数据集不存在（404）应跳过验证."""
        client = _make_client()
        with patch.object(client, "fetch_dataset", side_effect=PlatformApiError("NF", "not found", "not_found", 404)):
            # 不应抛出
            client._validate_submission_payload({
                "dataset_id": "ds1",
                "entries": [{"url": "https://any.com"}],
            })

    def test_dataset_http_404_skips_validation(self) -> None:
        """HTTPStatusError 404 应跳过验证."""
        client = _make_client()
        resp_404 = _mock_response(404)
        error = httpx.HTTPStatusError("nf", request=resp_404.request, response=resp_404)
        with patch.object(client, "fetch_dataset", side_effect=error):
            client._validate_submission_payload({
                "dataset_id": "ds1",
                "entries": [{"url": "https://any.com"}],
            })

    def test_no_patterns_allows_all(self) -> None:
        """数据集没有 url_patterns 时应允许所有 URL."""
        client = _make_client()
        with patch.object(client, "fetch_dataset", return_value={}):
            client._validate_submission_payload({
                "dataset_id": "ds1",
                "entries": [{"url": "https://anything.com"}],
            })

    def test_fullmatch_not_partial(self) -> None:
        """验证使用 re.fullmatch 而非 re.match / re.search."""
        client = _make_client()
        # 这个 pattern 能 match 前缀，但 fullmatch 要求完整匹配
        dataset = {"url_patterns": [r"https://example\.com"]}
        with patch.object(client, "fetch_dataset", return_value=dataset):
            with pytest.raises(RuntimeError):
                client._validate_submission_payload({
                    "dataset_id": "ds1",
                    "entries": [{"url": "https://example.com/extra"}],
                })

    def test_entry_without_url_skipped(self) -> None:
        """entries 中没有 url 的项应被跳过."""
        client = _make_client()
        dataset = {"url_patterns": [r"https://example\.com/.*"]}
        with patch.object(client, "fetch_dataset", return_value=dataset):
            # 不应抛出 — 空 url 的 entry 被 continue 跳过
            client._validate_submission_payload({
                "dataset_id": "ds1",
                "entries": [{"url": ""}, {"data": "no url key"}],
            })

    def test_non_dict_entry_skipped(self) -> None:
        """非 dict 的 entry 应被跳过."""
        client = _make_client()
        dataset = {"url_patterns": [r"https://example\.com/.*"]}
        with patch.object(client, "fetch_dataset", return_value=dataset):
            client._validate_submission_payload({
                "dataset_id": "ds1",
                "entries": ["not a dict", 42, None],
            })
