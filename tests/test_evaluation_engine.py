"""Tests for Evaluation Engine."""
import json
import pytest
from unittest.mock import MagicMock

import sys
sys.path.insert(0, "scripts")

from evaluation_engine import EvaluationResult, EvaluationEngine


class TestEvaluationResult:
    def test_rejected_result(self):
        """Rejected result should have consistent=False and meaningful reason."""
        result = EvaluationResult(
            verdict="rejected",
            consistent=False,
            score=0,
            reason="数据不一致：原始数据中没有提到年龄为25岁"
        )

        assert result.verdict == "rejected"
        assert result.consistent is False
        assert result.score == 0
        assert "不一致" in result.reason

    def test_accepted_result(self):
        """Accepted result should have consistent=True and score 0-100."""
        result = EvaluationResult(
            verdict="accepted",
            consistent=True,
            score=85,
            reason="数据质量良好，所有必填字段完整且准确"
        )

        assert result.verdict == "accepted"
        assert result.consistent is True
        assert 0 <= result.score <= 100
        assert len(result.reason) > 0


class TestConsistencyCheck:
    def test_inconsistent_data_returns_rejected(self):
        """When structured data contradicts cleaned data, should return rejected."""
        mock_llm = MagicMock(return_value='{"consistent": false, "reason": "原始数据中没有提到年龄"}')
        engine = EvaluationEngine(llm_call=mock_llm)

        cleaned_data = "John Smith, software engineer"
        structured_data = {"name": "John Smith", "age": 25, "title": "software engineer"}
        schema_fields = ["name", "age", "title"]

        result = engine.evaluate(cleaned_data, structured_data, schema_fields)

        assert result.verdict == "rejected"
        assert result.consistent is False
        assert result.score == 0
        assert len(result.reason) > 0

    def test_consistent_data_proceeds_to_scoring(self):
        """When data is consistent, should proceed to scoring phase."""
        # Mock LLM to return consistent check, then quality scores
        mock_llm = MagicMock()
        mock_llm.side_effect = [
            '{"consistent": true, "reason": "数据一致"}',
            '{"completeness": 90, "accuracy": 95, "type_correctness": 100, "sufficiency": 85, "final_score": 92, "notes": "质量良好"}'
        ]
        engine = EvaluationEngine(llm_call=mock_llm)

        cleaned_data = "John Smith, 30岁, 软件工程师"
        structured_data = {"name": "John Smith", "age": 30, "title": "软件工程师"}
        schema_fields = ["name", "age", "title"]

        result = engine.evaluate(cleaned_data, structured_data, schema_fields)

        assert result.verdict == "accepted"
        assert result.consistent is True
        assert result.score == 92
        assert "质量良好" in result.reason


class TestEvaluationEngineInit:
    def test_default_init(self):
        """Engine should initialize with default openclaw LLM."""
        engine = EvaluationEngine()
        assert engine.timeout == 120
        assert engine.llm_call is not None

    def test_custom_llm(self):
        """Engine should accept custom LLM callable."""
        mock_llm = MagicMock(return_value='{"test": "response"}')
        engine = EvaluationEngine(llm_call=mock_llm, timeout=60)

        assert engine.llm_call == mock_llm
        assert engine.timeout == 60


class TestQualityScoring:
    def test_high_quality_data_gets_high_score(self):
        """Complete and accurate data should score 80+."""
        mock_llm = MagicMock()
        mock_llm.side_effect = [
            '{"consistent": true, "reason": "数据一致"}',
            '{"completeness": 100, "accuracy": 95, "type_correctness": 100, "sufficiency": 90, "final_score": 96, "notes": "优质数据"}'
        ]
        engine = EvaluationEngine(llm_call=mock_llm)

        cleaned_data = "Jane Doe, 28岁, 高级数据科学家, 擅长机器学习和深度学习"
        structured_data = {
            "name": "Jane Doe",
            "age": 28,
            "title": "高级数据科学家",
            "skills": ["机器学习", "深度学习"]
        }
        schema_fields = ["name", "age", "title", "skills"]

        result = engine.evaluate(cleaned_data, structured_data, schema_fields)

        assert result.verdict == "accepted"
        assert result.score >= 80

    def test_incomplete_data_gets_lower_score(self):
        """Missing required fields should lower completeness score."""
        mock_llm = MagicMock()
        mock_llm.side_effect = [
            '{"consistent": true, "reason": "数据一致"}',
            '{"completeness": 50, "accuracy": 90, "type_correctness": 100, "sufficiency": 60, "final_score": 68, "notes": "缺少必填字段"}'
        ]
        engine = EvaluationEngine(llm_call=mock_llm)

        cleaned_data = "John, engineer"
        structured_data = {"name": "John", "title": "engineer"}
        schema_fields = ["name", "age", "title", "email"]

        result = engine.evaluate(cleaned_data, structured_data, schema_fields)

        assert result.verdict == "accepted"
        assert result.score < 80

    def test_type_mismatch_detected(self):
        """Wrong data types should be detected in scoring."""
        mock_llm = MagicMock()
        mock_llm.side_effect = [
            '{"consistent": true, "reason": "数据一致"}',
            '{"completeness": 100, "accuracy": 80, "type_correctness": 40, "sufficiency": 90, "final_score": 72, "notes": "类型错误：age应为数字"}'
        ]
        engine = EvaluationEngine(llm_call=mock_llm)

        cleaned_data = "John Smith, 30岁, engineer"
        structured_data = {"name": "John Smith", "age": "thirty", "title": "engineer"}
        schema_fields = ["name", "age", "title"]

        result = engine.evaluate(cleaned_data, structured_data, schema_fields)

        assert result.verdict == "accepted"
        assert "类型" in result.reason


class TestPromptGeneration:
    def test_consistency_prompt_includes_both_data(self):
        """Consistency check prompt should include both cleaned and structured data."""
        mock_llm = MagicMock()
        mock_llm.side_effect = [
            '{"consistent": true, "reason": "ok"}',
            '{"completeness": 80, "accuracy": 80, "type_correctness": 80, "sufficiency": 80, "final_score": 80, "notes": "ok"}'
        ]
        engine = EvaluationEngine(llm_call=mock_llm)

        cleaned_data = "test cleaned data"
        structured_data = {"test": "structured"}

        engine.evaluate(cleaned_data, structured_data, ["test"])

        # Check that first call includes both data
        first_call = mock_llm.call_args_list[0][0][0]
        assert "test cleaned data" in first_call
        assert '"test": "structured"' in first_call or "test" in first_call

    def test_scoring_prompt_includes_schema(self):
        """Scoring prompt should include schema definition."""
        mock_llm = MagicMock()
        mock_llm.side_effect = [
            '{"consistent": true, "reason": "ok"}',
            '{"completeness": 80, "accuracy": 80, "type_correctness": 80, "sufficiency": 80, "final_score": 80, "notes": "ok"}'
        ]
        engine = EvaluationEngine(llm_call=mock_llm)

        schema_fields = ["name", "age", "title"]
        engine.evaluate("data", {"name": "test"}, schema_fields)

        # Check that second call includes schema
        second_call = mock_llm.call_args_list[1][0][0]
        assert "name" in second_call
        assert "age" in second_call
        assert "title" in second_call


class TestEdgeCases:
    def test_empty_structured_data(self):
        """Empty structured data should be rejected."""
        mock_llm = MagicMock(return_value='{"consistent": false, "reason": "结构化数据为空"}')
        engine = EvaluationEngine(llm_call=mock_llm)

        result = engine.evaluate("some data", {}, ["field1"])

        assert result.verdict == "rejected"
        assert result.consistent is False

    def test_malformed_llm_response_consistency(self):
        """Malformed JSON in consistency check should be handled gracefully."""
        mock_llm = MagicMock(return_value='not valid json')
        engine = EvaluationEngine(llm_call=mock_llm)

        result = engine.evaluate("data", {"test": "value"}, ["test"])

        # Should reject on parse error
        assert result.verdict == "rejected"
        assert "解析失败" in result.reason or "错误" in result.reason

    def test_malformed_llm_response_scoring(self):
        """Malformed JSON in scoring should be handled gracefully."""
        mock_llm = MagicMock()
        mock_llm.side_effect = [
            '{"consistent": true, "reason": "ok"}',
            'invalid json response'
        ]
        engine = EvaluationEngine(llm_call=mock_llm)

        result = engine.evaluate("data", {"test": "value"}, ["test"])

        # Should reject on scoring parse error
        assert result.verdict == "rejected"
        assert "评分失败" in result.reason or "错误" in result.reason

    def test_timeout_error_handled(self):
        """LLM timeout should be handled gracefully."""
        mock_llm = MagicMock(side_effect=TimeoutError("Request timed out"))
        engine = EvaluationEngine(llm_call=mock_llm)

        result = engine.evaluate("data", {"test": "value"}, ["test"])

        assert result.verdict == "rejected"
        assert "超时" in result.reason or "timeout" in result.reason.lower()
