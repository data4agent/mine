from __future__ import annotations

import ast
import hashlib
import operator
from typing import Any


class UnsupportedChallenge(RuntimeError):
    def __init__(self, challenge_type: str) -> None:
        super().__init__(f"unsupported challenge type: {challenge_type}")


def solve_challenge(challenge: dict[str, Any]) -> str:
    challenge_type = str(challenge.get("question_type") or "unknown")
    if challenge_type == "content_understanding":
        return str(challenge.get("accepted_answer") or challenge.get("answer") or "accepted")
    if challenge_type in {"math", "arithmetic"}:
        expression = str(challenge.get("expression") or challenge.get("prompt") or "").strip()
        if not expression:
            raise UnsupportedChallenge(challenge_type)
        return str(_evaluate_math_expression(expression))
    if challenge_type in {"sha256_nonce", "hashcash"}:
        return _solve_sha256_nonce(challenge)
    raise UnsupportedChallenge(challenge_type)


def _solve_sha256_nonce(challenge: dict[str, Any]) -> str:
    prefix = str(challenge.get("prefix") or "")
    if not prefix:
        difficulty = int(challenge.get("difficulty") or 0)
        prefix = "0" * max(0, difficulty)
    seed = str(challenge.get("input") or challenge.get("seed") or challenge.get("prompt") or "")
    separator = str(challenge.get("separator") or "")
    max_nonce = max(1, int(challenge.get("max_nonce") or 100_000))

    for nonce in range(max_nonce + 1):
        candidate = (
            seed.replace("{nonce}", str(nonce))
            if "{nonce}" in seed
            else f"{seed}{separator}{nonce}"
        )
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        if digest.startswith(prefix):
            answer_format = str(challenge.get("answer_format") or "nonce")
            if answer_format == "candidate":
                return candidate
            return str(nonce)
    raise UnsupportedChallenge(str(challenge.get("question_type") or "sha256_nonce"))


def _evaluate_math_expression(expression: str) -> int:
    tree = ast.parse(expression, mode="eval")
    return int(_eval_node(tree.body))


def _eval_node(node: ast.AST) -> int | float:
    binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    unary_ops = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in binary_ops:
        return binary_ops[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in unary_ops:
        return unary_ops[type(node.op)](_eval_node(node.operand))
    raise ValueError("unsupported math expression")
