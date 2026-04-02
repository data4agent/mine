#!/usr/bin/env python3
"""
Reproduce the same enrich completion path as production **without** starting OpenClaw Gateway:

1) OpenClaw Gateway uses LLMClient ``/responses`` (provider=openclaw).
2) This script uses **OpenAI-compatible** ``POST {base_url}/chat/completions`` (same as LLMClient’s
   non-openclaw branch), then calls ``EnrichPipeline.fill_pending_agent_result`` like ``fill-enrichment``.

Typical usage (ensure records are ``pending_agent``, or use ``recover-pending`` first)::

    # Export prompts only (wire to any LLM)
    python scripts/mock_openclaw_enrich.py export-pending --records output/x/records.jsonl

    # Re-run enrich without LLM so failed groups become pending_agent (with prompt)
    python scripts/mock_openclaw_enrich.py recover-pending --records output/x/records.jsonl --in-place

    # Chat Completions fill (same chain as non-Gateway enrich)
    python scripts/mock_openclaw_enrich.py chat-complete --records output/x/records.jsonl \\
        --model-config references/model_config_chat_completions.example.json --output output/x/records.filled.jsonl

Environment variables override API keys in config: ``OPENAI_API_KEY`` or ``MINE_CHAT_API_KEY``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Allow running from mine repo root
_SCRIPT_DIR = Path(__file__).resolve().parent
_MINE_ROOT = _SCRIPT_DIR.parent
if str(_MINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MINE_ROOT))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )


def _extract_chat_content(data: dict[str, Any]) -> str:
    """Match ``LLMClient._extract_content`` for chat completions responses."""
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [p.get("text", "") for p in content if isinstance(p, dict)]
        return "".join(parts).strip()
    return ""


async def _recover_pending(record: dict[str, Any]) -> dict[str, Any]:
    """Re-run enrich without LLM so generative groups become pending_agent (with prompt)."""
    from crawler.enrich.pipeline import EnrichPipeline
    from crawler.platforms.registry import get_platform_adapter

    platform = str(record.get("platform") or "")
    adapter = get_platform_adapter(platform)
    req = adapter.build_enrichment_request(record)
    groups = list(req.get("field_groups") or ())
    if not groups:
        return record

    pipeline = EnrichPipeline(model_config={})
    enriched = await pipeline.enrich(record, groups)
    record["enrichment"] = {
        "doc_id": enriched.doc_id,
        "source_url": enriched.source_url,
        "platform": enriched.platform,
        "resource_type": enriched.resource_type,
        "enrichment_results": {k: v.to_dict() for k, v in enriched.enrichment_results.items()},
        "enriched_fields": dict(enriched.enriched_fields),
    }
    return record


def _needs_recover(record: dict[str, Any]) -> bool:
    enr = record.get("enrichment")
    if not isinstance(enr, dict):
        return False
    results = enr.get("enrichment_results")
    if not isinstance(results, dict):
        return False
    for payload in results.values():
        if not isinstance(payload, dict):
            continue
        if payload.get("status") != "failed":
            continue
        err = str(payload.get("error") or "")
        if "LLM" in err or "llm" in err.lower():
            return True
    return False


async def cmd_recover_pending(args: argparse.Namespace) -> int:
    path = Path(args.records)
    out_path = path if args.in_place else Path(args.output)
    records = [_load_json_line(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    out: list[dict[str, Any]] = []
    for rec in records:
        if args.all or _needs_recover(rec):
            out.append(await _recover_pending(dict(rec)))
        else:
            out.append(rec)
    _write_jsonl(out_path, out)
    print(f"Wrote {len(out)} records -> {out_path}")
    return 0


def _load_json_line(line: str) -> dict[str, Any]:
    return json.loads(line)


async def _chat_complete_record(
    record: dict[str, Any],
    *,
    base_url: str,
    api_key: str,
    model: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
) -> dict[str, Any]:
    import httpx

    from crawler.enrich.pipeline import EnrichPipeline

    enr = record.get("enrichment")
    if not isinstance(enr, dict):
        return record
    results = enr.get("enrichment_results")
    if not isinstance(results, dict):
        return record

    pipeline = EnrichPipeline(model_config={})
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        for field_group, payload in list(results.items()):
            if not isinstance(payload, dict):
                continue
            if payload.get("status") != "pending_agent":
                continue
            prompt = str(payload.get("agent_prompt") or "")
            system_prompt = str(payload.get("agent_system_prompt") or "")
            if not prompt.strip():
                continue
            messages: list[dict[str, str]] = []
            if system_prompt.strip():
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            resp = await client.post(
                url,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            text = _extract_chat_content(resp.json())
            filled = pipeline.fill_pending_agent_result(field_group, text, document=record)
            results[field_group] = filled.to_dict()
            for field in filled.fields:
                if field.value is not None:
                    enr.setdefault("enriched_fields", {})[field.field_name] = field.value

    return record


async def cmd_chat_complete(args: argparse.Namespace) -> int:
    cfg_path = Path(args.model_config)
    cfg = _load_json(cfg_path)
    api_key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("MINE_CHAT_API_KEY", "").strip()
        or str(cfg.get("api_key", "")).strip()
    )
    if not api_key or api_key.startswith("REPLACE"):
        print("Error: set api_key in model_config or OPENAI_API_KEY / MINE_CHAT_API_KEY", file=sys.stderr)
        return 1

    base_url = str(cfg.get("base_url", "https://api.openai.com/v1")).strip()
    model = str(cfg.get("model", "gpt-4o-mini")).strip()
    max_tokens = int(cfg.get("max_tokens", 768))
    temperature = float(cfg.get("temperature", 0.1))
    timeout = float(cfg.get("timeout", 120.0))

    path = Path(args.records)
    records = [_load_json_line(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    updated: list[dict[str, Any]] = []
    for rec in records:
        updated.append(
            await _chat_complete_record(
                rec,
                base_url=base_url,
                api_key=api_key,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
        )
    out_path = Path(args.output)
    _write_jsonl(out_path, updated)
    print(f"Wrote {len(updated)} filled records -> {out_path}")
    return 0


def cmd_export_pending(args: argparse.Namespace) -> int:
    path = Path(args.records)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = _load_json_line(line)
        enr = record.get("enrichment")
        if not isinstance(enr, dict):
            continue
        results = enr.get("enrichment_results")
        if not isinstance(results, dict):
            continue
        doc_id = enr.get("doc_id") or record.get("doc_id") or record.get("canonical_url")
        for field_group, payload in results.items():
            if not isinstance(payload, dict):
                continue
            if payload.get("status") != "pending_agent":
                continue
            rows.append(
                {
                    "doc_id": doc_id,
                    "field_group": field_group,
                    "agent_system_prompt": payload.get("agent_system_prompt"),
                    "agent_prompt": payload.get("agent_prompt"),
                }
            )
    out = Path(args.output)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(rows)} pending prompts -> {out}")
    return 0


def _dispatch(ns: argparse.Namespace) -> int:
    if ns.command == "recover-pending":
        return asyncio.run(cmd_recover_pending(ns))
    if ns.command == "chat-complete":
        return asyncio.run(cmd_chat_complete(ns))
    if ns.command == "export-pending":
        return cmd_export_pending(ns)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="LinkedIn-style enrich without Gateway (Chat Completions + fill_pending)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_rec = sub.add_parser("recover-pending", help="Recompute failed groups to pending_agent (no external LLM)")
    p_rec.add_argument("--records", required=True, help="Path to records.jsonl")
    p_rec.add_argument("--output", default="", help="Output path (unless --in-place)")
    p_rec.add_argument("--in-place", action="store_true", help="Overwrite the records file")
    p_rec.add_argument("--all", action="store_true", help="Re-run enrich for all records, not only failures")

    p_chat = sub.add_parser("chat-complete", help="Run Chat Completions for pending_agent groups (like fill-enrichment)")
    p_chat.add_argument("--records", required=True)
    p_chat.add_argument("--output", required=True)
    p_chat.add_argument("--model-config", required=True, help="OpenAI-compatible JSON; see references/model_config_chat_completions.example.json")

    p_exp = sub.add_parser("export-pending", help="Export pending_agent prompts as JSON")
    p_exp.add_argument("--records", required=True)
    p_exp.add_argument("--output", required=True)

    ns = parser.parse_args()
    if ns.command == "recover-pending":
        if not ns.in_place and not ns.output:
            print("Error: specify --output or --in-place", file=sys.stderr)
            return 1
    return _dispatch(ns)


if __name__ == "__main__":
    raise SystemExit(main())
