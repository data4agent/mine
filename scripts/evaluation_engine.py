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
            log.error("scoring phase failed: %s", str(e))
            return EvaluationResult(
                verdict="rejected",
                consistent=True,  # Passed consistency but failed scoring
                score=0,
                reason=f"scoring failed: {str(e)}",
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

        prompt = f"""You are a data consistency checker. Decide whether the miner's structured data
is consistent with the original cleaned data.

## Original data (source of truth)
{cleaned_data}

## Structured data extracted by miner
{structured_json}

## Criteria
- Consistent: values in structured data are supported by the original text without fabrication.
- Inconsistent: structured data adds facts not in the original, or severely distorts meaning.

## Output (strict JSON only, no markdown)
{{"consistent": true/false, "reason": "brief rationale"}}"""

        try:
            response = self.llm_call(prompt)
            result = parse_json_response(response)

            if not result or "consistent" not in result:
                log.error("consistency check parse failed: %s", response[:200])
                return {
                    "consistent": False,
                    "reason": "consistency check parse failed: invalid LLM response",
                }

            return {
                "consistent": result.get("consistent", False),
                "reason": result.get("reason", "no reason given"),
            }

        except TimeoutError as e:
            log.error("consistency check timeout: %s", str(e))
            return {
                "consistent": False,
                "reason": f"consistency check timeout: {str(e)}",
            }
        except Exception as e:
            log.error("consistency check failed: %s", str(e))
            return {
                "consistent": False,
                "reason": f"consistency check error: {str(e)}",
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

        prompt = f"""You are a data quality scorer. Score the miner's structured extraction.

## Schema
{schema_json}

## Original data
{cleaned_data}

## Structured data extracted by miner
{structured_json}

## Dimensions
1. Completeness (30%): are required fields present?
2. Accuracy (40%): are extracted values correct?
3. Type correctness (15%): do values match schema types?
4. Information sufficiency (15%): is critical information missing?

## Output (strict JSON only, no markdown)
{{"completeness": 0-100, "accuracy": 0-100, "type_correctness": 0-100, "sufficiency": 0-100, "final_score": 0-100, "notes": "scoring notes"}}"""

        try:
            response = self.llm_call(prompt)
            result = parse_json_response(response)

            if not result or "final_score" not in result:
                log.error("quality scoring parse failed: %s", response[:200])
                raise ValueError("quality scoring parse failed: invalid LLM response")

            return {
                "completeness": result.get("completeness", 0),
                "accuracy": result.get("accuracy", 0),
                "type_correctness": result.get("type_correctness", 0),
                "sufficiency": result.get("sufficiency", 0),
                "final_score": result.get("final_score", 0),
                "notes": result.get("notes", "no scoring notes"),
            }

        except TimeoutError as e:
            log.error("quality scoring timeout: %s", str(e))
            raise ValueError(f"quality scoring timeout: {str(e)}")
        except Exception as e:
            log.error("quality scoring failed: %s", str(e))
            raise ValueError(f"quality scoring error: {str(e)}")
