"""Tests for crawler.extract.pre_llm_optimizer module."""
from __future__ import annotations

from typing import Any

import pytest

from crawler.extract.pre_llm_optimizer import (
    _deduplicate_paragraphs,
    _remove_low_value_sections,
    _smart_truncate,
    optimize_for_llm,
)


# ---------------------------------------------------------------------------
# _smart_truncate
# ---------------------------------------------------------------------------

class TestSmartTruncate:
    """_smart_truncate 的截断逻辑。"""

    def test_within_limit(self) -> None:
        """文本未超过限制时应原样返回。"""
        text = "Short text\nSecond line"
        result = _smart_truncate(text, max_chars=100)
        assert result == text

    def test_exceeds_limit(self) -> None:
        """文本超过限制时应截断。"""
        lines = [f"Line {i}: " + "x" * 50 for i in range(20)]
        text = "\n".join(lines)
        result = _smart_truncate(text, max_chars=200)
        assert len(result) <= 200 + 100  # 允许末尾行的额外长度
        assert result.startswith("Line 0:")

    def test_first_line_exceeding_limit_kept(self) -> None:
        """第一行超过限制时应保留（i > 0 才跳出）。"""
        long_first_line = "A" * 500
        text = long_first_line + "\nSecond line"
        result = _smart_truncate(text, max_chars=100)
        # 第一行应被保留，因为循环条件 i > 0
        assert result == long_first_line

    def test_empty_text(self) -> None:
        """空文本应返回空字符串。"""
        result = _smart_truncate("", max_chars=100)
        assert result == ""


# ---------------------------------------------------------------------------
# _remove_low_value_sections
# ---------------------------------------------------------------------------

class TestRemoveLowValueSections:
    """_remove_low_value_sections 的节过滤逻辑。"""

    def test_removes_references_section(self) -> None:
        """应移除 References 节。"""
        text = "# Title\nContent here.\n## References\nRef 1\nRef 2\n## Next Section\nMore content"
        result = _remove_low_value_sections(text)
        assert "References" not in result
        assert "Ref 1" not in result
        assert "Next Section" in result
        assert "More content" in result

    def test_removes_bibliography(self) -> None:
        """应移除 Bibliography 节。"""
        text = "# Main\nBody text\n## Bibliography\nBook 1\nBook 2"
        result = _remove_low_value_sections(text)
        assert "Bibliography" not in result
        assert "Book 1" not in result
        assert "Body text" in result

    def test_removes_see_also(self) -> None:
        """应移除 See Also 节。"""
        text = "# Article\nParagraph\n## See Also\nLink 1\nLink 2"
        result = _remove_low_value_sections(text)
        assert "See Also" not in result
        assert "Link 1" not in result
        assert "Paragraph" in result

    def test_preserves_other_content(self) -> None:
        """非低价值节应完整保留。"""
        text = "# Title\nIntro\n## Methods\nMethod text\n## Results\nResult text"
        result = _remove_low_value_sections(text)
        assert "Methods" in result
        assert "Method text" in result
        assert "Results" in result
        assert "Result text" in result

    def test_nested_headings_within_low_value(self) -> None:
        """低价值节内的更深层标题应被一起移除。"""
        text = "# Title\nIntro\n## References\nRef text\n### Sub-reference\nSub text\n## Conclusion\nConclusion text"
        result = _remove_low_value_sections(text)
        assert "References" not in result
        assert "Sub-reference" not in result
        assert "Sub text" not in result
        assert "Conclusion" in result

    def test_resume_after_low_value_section(self) -> None:
        """遇到同级或更高级标题时应恢复收集。"""
        text = (
            "# Article\n"
            "Intro text\n"
            "## See Also\n"
            "See also content\n"
            "## History\n"
            "History content"
        )
        result = _remove_low_value_sections(text)
        assert "See Also" not in result
        assert "See also content" not in result
        assert "History" in result
        assert "History content" in result


# ---------------------------------------------------------------------------
# _deduplicate_paragraphs
# ---------------------------------------------------------------------------

class TestDeduplicateParagraphs:
    """_deduplicate_paragraphs 的去重逻辑。"""

    def test_removes_duplicate_paragraphs(self) -> None:
        """重复的长段落应只保留第一个。"""
        para = "This is a paragraph that is long enough to be considered for deduplication."
        text = f"{para}\n\n{para}\n\nAnother unique paragraph that is also long enough."
        result = _deduplicate_paragraphs(text)
        # 应只出现一次
        assert result.count(para) == 1
        assert "Another unique paragraph" in result

    def test_keeps_short_paragraphs(self) -> None:
        """短段落（< 20 字符）即使重复也应保留。"""
        text = "Hi\n\nHi\n\nThis is a longer paragraph that will be deduplicated."
        result = _deduplicate_paragraphs(text)
        # "Hi" 足够短，应保留两次
        assert result.count("Hi") == 2

    def test_case_insensitive_dedup(self) -> None:
        """去重比较应忽略大小写。"""
        para1 = "This is a test paragraph for deduplication checking."
        para2 = "this is a test paragraph for deduplication checking."
        text = f"{para1}\n\n{para2}"
        result = _deduplicate_paragraphs(text)
        # 只保留第一个
        parts = [p for p in result.split("\n\n") if p.strip()]
        assert len(parts) == 1

    def test_whitespace_normalized(self) -> None:
        """去重时应忽略多余空格。"""
        para1 = "A long enough paragraph with normal spacing for test."
        para2 = "A  long  enough  paragraph  with  normal  spacing  for  test."
        text = f"{para1}\n\n{para2}"
        result = _deduplicate_paragraphs(text)
        parts = [p for p in result.split("\n\n") if p.strip()]
        assert len(parts) == 1


# ---------------------------------------------------------------------------
# optimize_for_llm
# ---------------------------------------------------------------------------

class TestOptimizeForLlm:
    """optimize_for_llm 全流程测试。"""

    def test_full_pipeline(self) -> None:
        """完整优化流程应移除低价值节、引用标记并去重。"""
        text = (
            "# Test Article\n"
            "2024-01-15\n"
            "Main content here.[1]\n"
            "\n"
            "## References\n"
            "Ref 1\n"
            "Ref 2\n"
        )
        result_text, fields = optimize_for_llm(text, max_chars=50000)
        # 引用标记 [1] 应被移除
        assert "[1]" not in result_text
        # References 节应被移除
        assert "References" not in result_text
        assert "Ref 1" not in result_text
        # 主要内容应保留
        assert "Main content here." in result_text
        # pre_extracted 应包含字段
        assert "title" in fields
        assert fields["title"] == "Test Article"

    def test_pre_extracted_dict_preservation(self) -> None:
        """传入的 pre_extracted 字典应被保留并新增字段。"""
        pre = {"custom_key": "custom_value"}
        text = "# Article Title\n2024-03-15\nSome text."
        _, fields = optimize_for_llm(text, pre_extracted=pre)
        assert fields["custom_key"] == "custom_value"
        assert "title" in fields

    def test_empty_text(self) -> None:
        """空文本应直接返回。"""
        result_text, fields = optimize_for_llm("")
        assert result_text == ""
        assert fields == {}

    def test_pre_extracted_none_creates_new_dict(self) -> None:
        """pre_extracted 为 None 时应创建新字典。"""
        text = "# Title\nSome content"
        _, fields = optimize_for_llm(text)
        assert isinstance(fields, dict)
        assert "title" in fields

    def test_truncation_applied(self) -> None:
        """超长文本应被截断。"""
        long_text = "# Title\n" + "Content line.\n" * 5000
        result_text, _ = optimize_for_llm(long_text, max_chars=500)
        assert len(result_text) <= 600  # 允许一定余量（最后一行可能超出）

    def test_language_detection_chinese(self) -> None:
        """中文内容应检测为 zh。"""
        text = "# 标题\n这是一段中文内容，用于测试语言检测功能。"
        _, fields = optimize_for_llm(text)
        assert fields.get("language") == "zh"

    def test_breadcrumb_removal(self) -> None:
        """面包屑导航应被移除。"""
        text = "Home > Products > Widget\n# Widget\nDescription here."
        result_text, _ = optimize_for_llm(text)
        assert "Home > Products" not in result_text
        assert "Description here." in result_text
