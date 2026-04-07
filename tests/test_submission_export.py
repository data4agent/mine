"""Tests for crawler.submission_export module."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from crawler.submission_export import (
    _build_structured_data,
    build_submission_request,
    export_submission_request,
)


# ---------------------------------------------------------------------------
# build_submission_request
# ---------------------------------------------------------------------------

class TestBuildSubmissionRequest:
    """build_submission_request 的各种输入场景。"""

    def test_valid_records(self) -> None:
        """包含完整字段的记录应正确输出。"""
        records = [
            {
                "url": "https://example.com/page1",
                "crawl_timestamp": "2025-01-01T00:00:00Z",
                "plain_text": "Hello World",
            },
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert result["dataset_id"] == "ds_1"
        assert len(result["entries"]) == 1
        entry = result["entries"][0]
        assert entry["url"] == "https://example.com/page1"
        assert entry["cleaned_data"] == "Hello World"
        assert entry["crawl_timestamp"] == "2025-01-01T00:00:00Z"
        assert isinstance(entry["structured_data"], dict)

    def test_canonical_url_preferred(self) -> None:
        """canonical_url 应优先于 url 字段。"""
        records = [
            {
                "canonical_url": "https://example.com/canonical",
                "url": "https://example.com/raw",
                "crawl_timestamp": "2025-01-01T00:00:00Z",
                "plain_text": "text",
            },
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert result["entries"][0]["url"] == "https://example.com/canonical"

    def test_missing_url_skipped(self) -> None:
        """url 为空的记录应被跳过。"""
        records = [
            {"crawl_timestamp": "2025-01-01T00:00:00Z", "plain_text": "no url"},
            {"url": "", "crawl_timestamp": "2025-01-01T00:00:00Z"},
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert len(result["entries"]) == 0

    def test_missing_timestamp_skipped(self) -> None:
        """crawl_timestamp 为空且没有 generated_at 的记录应被跳过。"""
        records = [
            {"url": "https://example.com", "plain_text": "no ts"},
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert len(result["entries"]) == 0

    def test_generated_at_fallback(self) -> None:
        """crawl_timestamp 为空时应回退到 generated_at。"""
        records = [
            {"url": "https://example.com/a", "plain_text": "data"},
        ]
        result = build_submission_request(
            records, dataset_id="ds_1", generated_at="2025-06-01T00:00:00Z",
        )
        assert len(result["entries"]) == 1
        assert result["entries"][0]["crawl_timestamp"] == "2025-06-01T00:00:00Z"

    def test_cleaned_data_fallback_plain_text(self) -> None:
        """plain_text 优先级最高。"""
        records = [
            {
                "url": "https://example.com",
                "crawl_timestamp": "2025-01-01T00:00:00Z",
                "plain_text": "plain",
                "cleaned_data": "cleaned",
                "markdown": "md",
            },
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert result["entries"][0]["cleaned_data"] == "plain"

    def test_cleaned_data_fallback_cleaned_data(self) -> None:
        """plain_text 为空时应回退到 cleaned_data。"""
        records = [
            {
                "url": "https://example.com",
                "crawl_timestamp": "2025-01-01T00:00:00Z",
                "cleaned_data": "cleaned",
                "markdown": "md",
            },
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert result["entries"][0]["cleaned_data"] == "cleaned"

    def test_cleaned_data_fallback_markdown(self) -> None:
        """plain_text 和 cleaned_data 都为空时应回退到 markdown。"""
        records = [
            {
                "url": "https://example.com",
                "crawl_timestamp": "2025-01-01T00:00:00Z",
                "markdown": "md content",
            },
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert result["entries"][0]["cleaned_data"] == "md content"

    def test_cleaned_data_all_none(self) -> None:
        """所有文本字段为 None 时 cleaned_data 应为空字符串。"""
        records = [
            {
                "url": "https://example.com",
                "crawl_timestamp": "2025-01-01T00:00:00Z",
            },
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert result["entries"][0]["cleaned_data"] == ""

    def test_empty_string_plain_text_falls_through(self) -> None:
        """plain_text 为空字符串时应回退。"""
        records = [
            {
                "url": "https://example.com",
                "crawl_timestamp": "2025-01-01T00:00:00Z",
                "plain_text": "",
                "cleaned_data": "fallback",
            },
        ]
        result = build_submission_request(records, dataset_id="ds_1")
        assert result["entries"][0]["cleaned_data"] == "fallback"


# ---------------------------------------------------------------------------
# _build_structured_data
# ---------------------------------------------------------------------------

class TestBuildStructuredData:
    """_build_structured_data 的正常和异常路径。"""

    def test_success_delegates_to_flatten(self) -> None:
        """flatten_record_for_schema 正常返回时直接使用其结果。"""
        record: dict[str, Any] = {"url": "https://example.com", "structured": {"a": 1}}
        with patch(
            "crawler.submission_export.flatten_record_for_schema",
            return_value={"flat": True},
        ):
            result = _build_structured_data(record)
        assert result == {"flat": True}

    def test_value_error_fallback(self) -> None:
        """flatten_record_for_schema 抛出 ValueError 时回退到 record['structured']。"""
        record: dict[str, Any] = {"structured": {"key": "val"}}
        with patch(
            "crawler.submission_export.flatten_record_for_schema",
            side_effect=ValueError("no schema"),
        ):
            result = _build_structured_data(record)
        assert result == {"key": "val"}

    def test_os_error_fallback(self) -> None:
        """flatten_record_for_schema 抛出 OSError 时回退到 record['structured']。"""
        record: dict[str, Any] = {"structured": {"x": 1}}
        with patch(
            "crawler.submission_export.flatten_record_for_schema",
            side_effect=OSError("file not found"),
        ):
            result = _build_structured_data(record)
        assert result == {"x": 1}

    def test_fallback_no_structured_key(self) -> None:
        """record 中没有 structured 键时回退应返回空字典。"""
        record: dict[str, Any] = {"url": "https://example.com"}
        with patch(
            "crawler.submission_export.flatten_record_for_schema",
            side_effect=ValueError("missing"),
        ):
            result = _build_structured_data(record)
        assert result == {}

    def test_fallback_structured_not_dict(self) -> None:
        """structured 值不是字典时应返回空字典。"""
        record: dict[str, Any] = {"structured": "not a dict"}
        with patch(
            "crawler.submission_export.flatten_record_for_schema",
            side_effect=ValueError("bad"),
        ):
            result = _build_structured_data(record)
        assert result == {}


# ---------------------------------------------------------------------------
# export_submission_request
# ---------------------------------------------------------------------------

class TestExportSubmissionRequest:
    """export_submission_request 的文件写入测试。"""

    def test_writes_to_output_path(self, tmp_path: Path) -> None:
        """应将 payload 写入 output_path。"""
        input_file = tmp_path / "input.jsonl"
        input_file.write_text(
            json.dumps({"url": "https://example.com", "crawl_timestamp": "2025-01-01T00:00:00Z", "plain_text": "hi"}) + "\n",
            encoding="utf-8",
        )
        output_file = tmp_path / "output.json"

        with patch(
            "crawler.submission_export.flatten_record_for_schema",
            return_value={},
        ):
            result = export_submission_request(
                input_path=input_file,
                output_path=output_file,
                dataset_id="ds_test",
                generated_at="2025-01-01T00:00:00Z",
            )

        assert result == output_file
        assert output_file.exists()
        payload = json.loads(output_file.read_text(encoding="utf-8"))
        assert payload["dataset_id"] == "ds_test"
        assert len(payload["entries"]) == 1

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """output_path 的父目录不存在时应自动创建。"""
        input_file = tmp_path / "input.jsonl"
        input_file.write_text(
            json.dumps({"url": "https://example.com", "crawl_timestamp": "2025-01-01T00:00:00Z"}) + "\n",
            encoding="utf-8",
        )
        output_file = tmp_path / "nested" / "deep" / "output.json"

        with patch(
            "crawler.submission_export.flatten_record_for_schema",
            return_value={},
        ):
            result = export_submission_request(
                input_path=input_file,
                output_path=output_file,
                dataset_id="ds_test",
                generated_at="2025-01-01T00:00:00Z",
            )

        assert output_file.exists()
        assert result == output_file
