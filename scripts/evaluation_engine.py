"""Evaluation Engine for Validator."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

from openclaw_llm import call_openclaw, parse_json_response

log = logging.getLogger("validator.evaluation")

DEFAULT_TIMEOUT = 120


@dataclass
class EvaluationResult:
    """Result of data evaluation."""
    verdict: str  # "accepted" | "rejected"
    consistent: bool
    score: int  # 0-100, meaningful only when consistent=True
    reason: str


class EvaluationEngine:
    """
    Two-phase evaluation engine for structured data quality.

    Phase 1: Consistency Check - Is structured_data consistent with cleaned_data?
    Phase 2: Quality Scoring - Score on 4 dimensions (completeness, accuracy, type, sufficiency)
    """

    def __init__(
        self,
        *,
        llm_call: Callable[[str], str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the evaluation engine.

        Args:
            llm_call: Optional callable for LLM calls. If None, uses default openclaw CLI.
            timeout: Timeout in seconds for LLM calls.
        """
        self.timeout = timeout
        if llm_call is None:
            self.llm_call = lambda prompt: call_openclaw(prompt, timeout=timeout)
        else:
            self.llm_call = llm_call

    def evaluate(
        self,
        cleaned_data: str | dict[str, Any],
        structured_data: dict[str, Any],
        schema_fields: list[str],
    ) -> EvaluationResult:
        """
        Evaluate structured data quality.

        Args:
            cleaned_data: Original cleaned data (source of truth).
            structured_data: Miner-extracted structured data.
            schema_fields: List of field names from schema.

        Returns:
            EvaluationResult with verdict, consistency status, score, and reason.
        """
        # Convert cleaned_data to string if it's a dict
        if isinstance(cleaned_data, dict):
            cleaned_data_str = json.dumps(cleaned_data, ensure_ascii=False, indent=2)
        else:
            cleaned_data_str = str(cleaned_data)

        # Phase 1: Consistency Check
        consistency_result = self._check_consistency(cleaned_data_str, structured_data)

        if not consistency_result["consistent"]:
            return EvaluationResult(
                verdict="rejected",
                consistent=False,
                score=0,
                reason=consistency_result["reason"],
            )

        # Phase 2: Quality Scoring
        try:
            scoring_result = self._score_quality(
                cleaned_data_str, structured_data, schema_fields
            )

            return EvaluationResult(
                verdict="accepted",
                consistent=True,
                score=scoring_result["final_score"],
                reason=scoring_result["notes"],
            )
        except Exception as e:
            # If scoring fails, reject the data
            log.error("评分阶段失败: %s", str(e))
            return EvaluationResult(
                verdict="rejected",
                consistent=True,  # Passed consistency but failed scoring
                score=0,
                reason=f"评分失败: {str(e)}",
            )

    def _check_consistency(
        self, cleaned_data: str, structured_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Phase 1: Check if structured data is consistent with cleaned data.

        Args:
            cleaned_data: Original cleaned data string.
            structured_data: Miner-extracted structured data.

        Returns:
            Dict with 'consistent' (bool) and 'reason' (str).
        """
        structured_json = json.dumps(structured_data, ensure_ascii=False, indent=2)

        prompt = f"""你是数据一致性检查器。判断 miner 提取的结构化数据是否与原始数据一致。

## 原始数据 (source of truth)
{cleaned_data}

## Miner 提取的结构化数据
{structured_json}

## 判断标准
- 一致 = 结构化数据中的值能在原始数据中找到对应信息,且没有明显捏造
- 不一致 = 结构化数据包含原始数据中不存在的信息,或严重歪曲原意

## 输出 (strict JSON, 不要markdown)
{{"consistent": true/false, "reason": "简要说明判断理由"}}"""

        try:
            response = self.llm_call(prompt)
            result = parse_json_response(response)

            if not result or "consistent" not in result:
                log.error("一致性检查响应解析失败: %s", response[:200])
                return {
                    "consistent": False,
                    "reason": "一致性检查解析失败: LLM 返回格式错误",
                }

            return {
                "consistent": result.get("consistent", False),
                "reason": result.get("reason", "无理由说明"),
            }

        except TimeoutError as e:
            log.error("一致性检查超时: %s", str(e))
            return {
                "consistent": False,
                "reason": f"一致性检查超时: {str(e)}",
            }
        except Exception as e:
            log.error("一致性检查失败: %s", str(e))
            return {
                "consistent": False,
                "reason": f"一致性检查错误: {str(e)}",
            }

    def _score_quality(
        self,
        cleaned_data: str,
        structured_data: dict[str, Any],
        schema_fields: list[str],
    ) -> dict[str, Any]:
        """
        Phase 2: Score data quality on multiple dimensions.

        Args:
            cleaned_data: Original cleaned data string.
            structured_data: Miner-extracted structured data.
            schema_fields: List of field names from schema.

        Returns:
            Dict with dimension scores and final_score.
        """
        structured_json = json.dumps(structured_data, ensure_ascii=False, indent=2)
        schema_json = json.dumps({"fields": schema_fields}, ensure_ascii=False, indent=2)

        prompt = f"""你是数据质量评分器。对 miner 提取的结构化数据进行质量评分。

## Schema 定义
{schema_json}

## 原始数据
{cleaned_data}

## Miner 提取的结构化数据
{structured_json}

## 评分维度
1. 完整性 (30%): 必填字段是否齐全?
2. 准确性 (40%): 提取的值是否准确?
3. 类型正确性 (15%): 值的类型是否符合 schema?
4. 信息充分性 (15%): 关键信息是否遗漏?

## 输出 (strict JSON, 不要markdown)
{{"completeness": 0-100, "accuracy": 0-100, "type_correctness": 0-100, "sufficiency": 0-100, "final_score": 0-100, "notes": "评分说明"}}"""

        try:
            response = self.llm_call(prompt)
            result = parse_json_response(response)

            if not result or "final_score" not in result:
                log.error("质量评分响应解析失败: %s", response[:200])
                raise ValueError("质量评分解析失败: LLM 返回格式错误")

            return {
                "completeness": result.get("completeness", 0),
                "accuracy": result.get("accuracy", 0),
                "type_correctness": result.get("type_correctness", 0),
                "sufficiency": result.get("sufficiency", 0),
                "final_score": result.get("final_score", 0),
                "notes": result.get("notes", "无评分说明"),
            }

        except TimeoutError as e:
            log.error("质量评分超时: %s", str(e))
            raise ValueError(f"质量评分超时: {str(e)}")
        except Exception as e:
            log.error("质量评分失败: %s", str(e))
            raise ValueError(f"质量评分错误: {str(e)}")
