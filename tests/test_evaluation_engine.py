"""evaluation_engine.py 的单元测试。"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from evaluation_engine import EvaluationEngine, EvaluationResult, _optimize_for_eval


# ---------------------------------------------------------------------------
# EvaluationEngine.evaluate()
# ---------------------------------------------------------------------------
class TestEngineEvaluate:
    """测试 evaluate() 的主流程和异常处理。"""

    def test_match_with_score(self) -> None:
        """LLM 返回 match + 高分 → accepted。"""

        def mock_llm(prompt: str) -> str:
            return '{"result": "match", "score": 85}'

        engine = EvaluationEngine(llm_call=mock_llm)
        result = engine.evaluate(
            cleaned_data="Hello world content",
            structured_data={"title": "Hello world"},
            schema_fields=["title"],
            repeat_cleaned_data="Hello world content",
        )
        assert result.result == "match"
        assert result.verdict == "accepted"
        assert result.consistent is True
        assert result.score == 85

    def test_mismatch(self) -> None:
        """LLM 返回 mismatch → rejected, score=0。"""

        def mock_llm(prompt: str) -> str:
            return '{"result": "mismatch", "score": 0}'

        engine = EvaluationEngine(llm_call=mock_llm)
        result = engine.evaluate(
            cleaned_data="Original content",
            structured_data={"title": "Original"},
            schema_fields=["title"],
            repeat_cleaned_data="Completely different content",
        )
        assert result.result == "mismatch"
        assert result.verdict == "rejected"
        assert result.consistent is False
        assert result.score == 0

    def test_no_repeat_data(self) -> None:
        """无 repeat data 时 result 为 match。"""

        def mock_llm(prompt: str) -> str:
            # 验证 prompt 中不包含 M1
            assert "Re-crawl (M1)" not in prompt
            return '{"result": "match", "score": 70}'

        engine = EvaluationEngine(llm_call=mock_llm)
        result = engine.evaluate(
            cleaned_data="Some content",
            structured_data={"field": "value"},
            schema_fields=["field"],
        )
        assert result.result == "match"
        assert result.score == 70

    def test_infrastructure_failure_returns_score_50(self) -> None:
        """LLM 调用异常时返回 score=50，不惩罚 miner。"""

        def mock_llm(prompt: str) -> str:
            raise RuntimeError("LLM service unavailable")

        engine = EvaluationEngine(llm_call=mock_llm)
        result = engine.evaluate(
            cleaned_data="content",
            structured_data={"x": 1},
            schema_fields=["x"],
        )
        assert result.result == "match"
        assert result.verdict == "accepted"
        assert result.score == 50

    def test_score_clamped_to_100(self) -> None:
        """分数超过 100 时应被截断。"""

        def mock_llm(prompt: str) -> str:
            return '{"result": "match", "score": 150}'

        engine = EvaluationEngine(llm_call=mock_llm)
        result = engine.evaluate(
            cleaned_data="content",
            structured_data={"x": 1},
            schema_fields=["x"],
        )
        assert result.score == 100

    def test_score_clamped_to_0(self) -> None:
        """负分应被截断为 0。"""

        def mock_llm(prompt: str) -> str:
            return '{"result": "match", "score": -10}'

        engine = EvaluationEngine(llm_call=mock_llm)
        result = engine.evaluate(
            cleaned_data="content",
            structured_data={"x": 1},
            schema_fields=["x"],
        )
        assert result.score == 0

    def test_dict_cleaned_data(self) -> None:
        """cleaned_data 为 dict 时应被序列化。"""

        def mock_llm(prompt: str) -> str:
            return '{"result": "match", "score": 60}'

        engine = EvaluationEngine(llm_call=mock_llm)
        result = engine.evaluate(
            cleaned_data={"html": "<p>test</p>"},
            structured_data={"title": "test"},
            schema_fields=["title"],
        )
        assert result.score == 60

    def test_zero_score_match_rejected(self) -> None:
        """match 但 score=0 → rejected。"""

        def mock_llm(prompt: str) -> str:
            return '{"result": "match", "score": 0}'

        engine = EvaluationEngine(llm_call=mock_llm)
        result = engine.evaluate(
            cleaned_data="content",
            structured_data={},
            schema_fields=["title"],
        )
        assert result.result == "match"
        assert result.verdict == "rejected"
        assert result.score == 0


# ---------------------------------------------------------------------------
# _extract_result_and_score
# ---------------------------------------------------------------------------
class TestExtractResultAndScore:
    """测试解析 LLM 响应的各种格式。"""

    def test_parsed_json(self) -> None:
        parsed = {"result": "match", "score": 75}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert result == "match"
        assert score == 75

    def test_mismatch_parsed(self) -> None:
        parsed = {"result": "mismatch", "score": 0}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert result == "mismatch"
        assert score == 0

    def test_raw_text_fallback_match(self) -> None:
        result, score = EvaluationEngine._extract_result_and_score(
            None, 'The data appears authentic. score: 80 out of 100.', True
        )
        assert result == "match"
        assert score == 80

    def test_raw_text_fallback_mismatch(self) -> None:
        result, score = EvaluationEngine._extract_result_and_score(
            None, 'Data is fabricated, mismatch detected. score: 0', True
        )
        assert result == "mismatch"
        assert score == 0

    def test_case_variation_true(self) -> None:
        parsed = {"result": "True", "score": 90}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert result == "match"

    def test_case_variation_yes(self) -> None:
        parsed = {"result": "yes", "score": 88}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert result == "match"

    def test_case_variation_false(self) -> None:
        parsed = {"result": "false", "score": 10}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert result == "mismatch"

    def test_case_variation_fabricated(self) -> None:
        parsed = {"result": "fabricated", "score": 0}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert result == "mismatch"

    def test_missing_score_defaults_zero(self) -> None:
        parsed = {"result": "match"}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert result == "match"
        assert score == 0

    def test_float_score(self) -> None:
        parsed = {"result": "match", "score": 72.5}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert score == 72

    def test_empty_result_with_score(self) -> None:
        """result 为空字符串但有 score 时应回退。"""
        parsed = {"result": "", "score": 65}
        result, score = EvaluationEngine._extract_result_and_score(parsed, "", True)
        assert result == "match"
        assert score == 65


# ---------------------------------------------------------------------------
# _optimize_for_eval
# ---------------------------------------------------------------------------
class TestOptimizeForEval:
    """测试文本优化/截断逻辑。"""

    def test_short_text_unchanged(self) -> None:
        text = "Hello world, this is a test."
        result = _optimize_for_eval(text)
        assert result == text

    def test_short_text_citation_stripped(self) -> None:
        text = "Some text [1] with citations [citation needed] and more [42]."
        result = _optimize_for_eval(text)
        assert "[1]" not in result
        assert "[citation needed]" not in result
        assert "[42]" not in result
        assert "Some text" in result

    def test_short_text_multi_blank_collapsed(self) -> None:
        text = "Para one\n\n\n\n\nPara two"
        result = _optimize_for_eval(text)
        assert "\n\n\n" not in result
        assert "Para one" in result
        assert "Para two" in result

    def test_long_text_heading_removal(self) -> None:
        """超过 20k 字符的文本应移除低价值 heading 下的内容。"""
        main_content = "Important content. " * 500
        references = "## References\n" + "Reference item. " * 500
        see_also = "## See Also\n" + "See also item. " * 500
        text = main_content + "\n\n" + references + "\n\n" + see_also
        if len(text) < 20000:
            text += "x" * (20001 - len(text))

        result = _optimize_for_eval(text)
        assert "Important content" in result
        assert "## References" not in result

    def test_long_text_dedup(self) -> None:
        """超过 20k 的文本中重复段落应被去除。"""
        paragraph = "This is a reasonably long paragraph with enough words to be deduped properly."
        text = ("\n\n".join([paragraph] * 300))
        if len(text) < 20000:
            text += "x" * (20001 - len(text))
        result = _optimize_for_eval(text)
        assert len(result) < len(text)

    def test_long_text_truncated(self) -> None:
        """超过 20k 限制的文本最终被截断。"""
        text = "A" * 50000
        result = _optimize_for_eval(text)
        # 截断到 _EVAL_MAX_CHARS (20000) + rsplit 调整 + "\n..." 后缀
        assert len(result) <= 20005

    def test_empty_text(self) -> None:
        assert _optimize_for_eval("") == ""
