"""Tests for OpenClaw CLI wrapper."""
import json
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, "scripts")

from openclaw_llm import call_openclaw, parse_json_response


class TestCallOpenclaw:
    def test_returns_stdout_on_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"consistent": true, "reason": "test"}'
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = call_openclaw("test prompt")

            assert result == '{"consistent": true, "reason": "test"}'
            mock_run.assert_called_once()

    def test_raises_on_nonzero_exit(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error message"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="OpenClaw CLI failed"):
                call_openclaw("test prompt")


class TestParseJsonResponse:
    def test_extracts_json_from_response(self):
        response = 'Some text\n{"key": "value"}\nMore text'
        result = parse_json_response(response)
        assert result == {"key": "value"}

    def test_returns_empty_dict_on_invalid_json(self):
        response = "no json here"
        result = parse_json_response(response)
        assert result == {}

    def test_handles_nested_json(self):
        response = '```json\n{"consistent": true, "metadata": {"score": 0.95}}\n```'
        result = parse_json_response(response)
        assert result == {"consistent": True, "metadata": {"score": 0.95}}

    def test_handles_markdown_code_block(self):
        response = 'Here is the result:\n```json\n{"status": "ok"}\n```\nDone!'
        result = parse_json_response(response)
        assert result == {"status": "ok"}

    def test_returns_first_valid_json_when_multiple(self):
        response = 'First: {"a": 1} Second: {"b": 2}'
        result = parse_json_response(response)
        assert result == {"a": 1}

    def test_handles_empty_string(self):
        result = parse_json_response("")
        assert result == {}


class TestCallOpenclawEdgeCases:
    def test_raises_when_cli_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="OpenClaw CLI not found"):
                call_openclaw("test", cli_path="/nonexistent/openclaw")

    def test_passes_custom_timeout(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "response"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            call_openclaw("test", timeout=60)

            args, kwargs = mock_run.call_args
            assert kwargs["timeout"] == 60

    def test_passes_custom_cli_path(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "response"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            call_openclaw("test", cli_path="/custom/path/openclaw")

            args, _ = mock_run.call_args
            assert args[0][0] == "/custom/path/openclaw"
