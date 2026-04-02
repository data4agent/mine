#!/usr/bin/env python3
"""
在不启动 OpenClaw Gateway 的情况下，复现与线上相同的 enrich 收尾路径：

1) OpenClaw Gateway 走的是 LLMClient 的 ``/responses``（provider=openclaw）。
2) 本脚本改为使用 **OpenAI 兼容** 的 ``POST {base_url}/chat/completions``，
   与 LLMClient 在非 openclaw 分支一致，然后调用与 ``fill-enrichment`` 相同的
   ``EnrichPipeline.fill_pending_agent_result`` 写回记录。

典型用法（先保证记录里是 pending_agent，或对本脚本使用 --recover-failed）::

    # 仅导出 prompt，便于外接任意 LLM
    python scripts/mock_openclaw_enrich.py export-pending --records output/x/records.jsonl

    # 将失败于 Gateway 的 enrich 先重算为 pending_agent（无 LLM）
    python scripts/mock_openclaw_enrich.py recover-pending --records output/x/records.jsonl --in-place

    # 用 Chat Completions 补全（模仿非 Gateway 的 enrich 调用链）
    python scripts/mock_openclaw_enrich.py chat-complete --records output/x/records.jsonl \\
        --model-config references/model_config_chat_completions.example.json --output output/x/records.filled.jsonl

环境变量可覆盖配置文件中的 api_key：OPENAI_API_KEY（或 MINE_CHAT_API_KEY）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# 允许从 mine 根目录直接运行
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
    """与 crawler.enrich.generative.llm_client.LLMClient._extract_content 行为一致（chat completions）。"""
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
    """对单条记录重新跑一遍无 LLM 的 enrich，使生成类组变为 pending_agent（带 prompt）。"""
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
    print(f"已写入 {len(out)} 条 -> {out_path}")
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
        print("错误: 请在 model_config 中配置 api_key，或设置环境变量 OPENAI_API_KEY / MINE_CHAT_API_KEY", file=sys.stderr)
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
    print(f"已补全并写入 {len(updated)} 条 -> {out_path}")
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
    print(f"已导出 {len(rows)} 条 pending prompt -> {out}")
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
    parser = argparse.ArgumentParser(description="模仿非 Gateway 的 LinkedIn enrich（Chat Completions + fill_pending）")
    sub = parser.add_subparsers(dest="command", required=True)

    p_rec = sub.add_parser("recover-pending", help="将 LLM 失败的组重算为 pending_agent（不调用外部 LLM）")
    p_rec.add_argument("--records", required=True, help="records.jsonl 路径")
    p_rec.add_argument("--output", default="", help="输出路径（与 --in-place 二选一）")
    p_rec.add_argument("--in-place", action="store_true", help="覆盖原 records 文件")
    p_rec.add_argument("--all", action="store_true", help="无论是否失败都重算 enrich")

    p_chat = sub.add_parser("chat-complete", help="对 pending_agent 组走 Chat Completions 并写回（等同手动 fill-enrichment）")
    p_chat.add_argument("--records", required=True)
    p_chat.add_argument("--output", required=True)
    p_chat.add_argument("--model-config", required=True, help="OpenAI 兼容配置 JSON，见 references/model_config_chat_completions.example.json")

    p_exp = sub.add_parser("export-pending", help="导出 pending_agent 的 prompt 列表 JSON")
    p_exp.add_argument("--records", required=True)
    p_exp.add_argument("--output", required=True)

    ns = parser.parse_args()
    if ns.command == "recover-pending":
        if not ns.in_place and not ns.output:
            print("错误: 请指定 --output 或使用 --in-place", file=sys.stderr)
            return 1
    return _dispatch(ns)


if __name__ == "__main__":
    raise SystemExit(main())
