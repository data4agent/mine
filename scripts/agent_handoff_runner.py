"""子 agent 执行入口：读取 handoff 条目，执行 crawl + enrich 回填，写回产物结果。

由主 worker 以独立子进程启动，不做平台提交，只负责产物生成。
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# 运行时路径设置，与仓库其他 scripts 一致
SCRIPTS_DIR = Path(__file__).resolve().parent
MINE_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(MINE_ROOT))

from common import inject_crawler_root
CRAWLER_ROOT = inject_crawler_root()

from mine_gateway import resolve_mine_gateway_model_config, write_model_config
from run_models import WorkItem, CrawlerRunResult
from worker_state import WorkerStateStore
from crawler.output import read_json_file, read_jsonl_file

log = logging.getLogger("agent_handoff_runner")


def _write_result(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "agent_result.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_enrich_argv(argv: list[str], *, output_dir: Path, model_config: dict[str, Any]) -> None:
    import shutil

    if shutil.which("openclaw") or shutil.which("openclaw.cmd") or shutil.which("openclaw.mjs"):
        argv.append("--use-openclaw")
        return
    if model_config:
        config_path = write_model_config(output_dir / "_runtime" / "mine-model-config.json", model_config)
        argv.extend(["--model-config", str(config_path)])


def _run_crawler(
    item: WorkItem,
    output_dir: Path,
    *,
    crawler_root: Path,
    python_bin: str,
    model_config: dict[str, Any],
    default_backend: str | None,
) -> CrawlerRunResult:
    """调用现有 CrawlerRunner 逻辑执行 crawl + enrich。"""
    import subprocess

    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = output_dir / "task-input.jsonl"
    input_path.write_text(json.dumps(item.record, ensure_ascii=False) + "\n", encoding="utf-8")

    command = item.crawler_command or "run"
    argv = [python_bin, "-m", "crawler", command, "--input", str(input_path), "--output", str(output_dir), "--auto-login"]
    _append_enrich_argv(argv, output_dir=output_dir, model_config=model_config)
    if item.resume:
        argv.append("--resume")
    if default_backend:
        argv.extend(["--preferred-backend", default_backend])

    timeout = int(os.environ.get("HANDOFF_CRAWL_TIMEOUT", "600"))
    try:
        completed = subprocess.run(
            argv,
            cwd=str(crawler_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return CrawlerRunResult(
            output_dir=output_dir,
            records=[],
            errors=[{"error_code": "TIMEOUT", "message": f"crawler timed out after {timeout}s"}],
            summary={},
            exit_code=-1,
            argv=argv,
        )

    records_path = output_dir / "records.jsonl"
    errors_path = output_dir / "errors.jsonl"
    records = read_jsonl_file(records_path) if records_path.exists() else []
    errors = read_jsonl_file(errors_path) if errors_path.exists() else []
    summary_path = output_dir / "summary.json"
    summary = read_json_file(summary_path) if summary_path.exists() else {}
    if not isinstance(summary, dict):
        summary = {}
    return CrawlerRunResult(
        output_dir=output_dir,
        records=records,
        errors=errors,
        summary=summary,
        exit_code=completed.returncode,
        argv=argv,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _fill_pending_enrichments(records_path: Path, *, model_config: dict[str, Any]) -> int:
    """对 records.jsonl 中仍 pending_agent 的字段调用 LLM 回填。返回填充数。"""
    from crawler.enrich.pipeline import EnrichPipeline
    from crawler.enrich.generative.llm_enrich import enrich_with_llm, llm_execution_available

    records = read_jsonl_file(records_path) if records_path.exists() else []
    if not records:
        return 0

    if not llm_execution_available(model_config):
        return 0

    pipeline = EnrichPipeline(cache_dir=records_path.parent / ".cache" / "enrich", model_config=model_config)
    filled_total = 0

    import asyncio

    async def _fill_record(record: dict[str, Any]) -> int:
        enrichment = record.get("enrichment")
        if not isinstance(enrichment, dict):
            return 0
        results = enrichment.get("enrichment_results")
        if not isinstance(results, dict):
            return 0

        pending_groups = [
            (group_name, group_result)
            for group_name, group_result in results.items()
            if isinstance(group_result, dict) and group_result.get("status") == "pending_agent"
        ]
        if not pending_groups:
            return 0

        filled = 0
        for group_name, group_result in pending_groups:
            prompt = group_result.get("agent_prompt") or ""
            system_prompt = group_result.get("agent_system_prompt")
            if not prompt:
                continue
            try:
                response = await enrich_with_llm(
                    prompt,
                    model_config=model_config or None,
                    system_prompt=system_prompt or "",
                    timeout=180.0,
                )
                if response.success and response.content:
                    result = pipeline.fill_pending_agent_result(group_name, response.content, document=record)
                    results[group_name] = result.to_dict()
                    if result.fields:
                        for field in result.fields:
                            if field.value is not None:
                                enrichment.setdefault("enriched_fields", {})[field.field_name] = field.value
                    filled += 1
            except Exception as exc:
                log.warning("enrich fill failed for %s: %s", group_name, exc)
        return filled

    for record in records:
        filled_total += asyncio.run(_fill_record(record))

    if filled_total > 0:
        import tempfile
        content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        fd, tmp = tempfile.mkstemp(dir=str(records_path.parent), suffix=".tmp")
        try:
            os.write(fd, content.encode("utf-8"))
            os.close(fd)
            fd = -1
            os.replace(tmp, str(records_path))
        except BaseException:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    return filled_total


def _records_have_pending_agent(records: list[dict[str, Any]]) -> bool:
    for record in records:
        enrichment = record.get("enrichment")
        if not isinstance(enrichment, dict):
            continue
        for result in (enrichment.get("enrichment_results") or {}).values():
            if isinstance(result, dict) and result.get("status") == "pending_agent":
                return True
    return False


def run_handoff(state_root: str, handoff_id: str) -> None:
    store = WorkerStateStore(Path(state_root))
    entries = store.load_handoffs()
    entry = next((e for e in entries if e.get("handoff_id") == handoff_id), None)
    if entry is None:
        log.error("handoff %s not found", handoff_id)
        return

    item_data = entry.get("item")
    if not isinstance(item_data, dict):
        store.update_handoff(handoff_id, {"status": "failed", "last_error": "invalid item data"})
        return

    item = WorkItem.from_dict(item_data)
    output_dir = Path(entry["output_dir"]) if entry.get("output_dir") else (Path(state_root).parent / "agent-runs" / item.source / item.item_id)

    python_bin = os.environ.get("PYTHON_BIN") or os.environ.get("PLUGIN_PYTHON_BIN") or sys.executable
    model_config = resolve_mine_gateway_model_config()
    default_backend = os.environ.get("DEFAULT_BACKEND") or None
    records_path = output_dir / "records.jsonl"

    existing_records = read_jsonl_file(records_path) if records_path.exists() else []
    if existing_records and not _records_have_pending_agent(existing_records):
        final_records = existing_records
        log.info("[handoff] reusing existing crawl artifacts for %s", handoff_id)
    else:
        if existing_records:
            final_records = existing_records
            log.info("[handoff] reusing existing records for enrich retry: %s", handoff_id)
        else:
            log.info("[handoff] starting crawl for %s -> %s", handoff_id, item.url)
            result = _run_crawler(
                item,
                output_dir,
                crawler_root=CRAWLER_ROOT,
                python_bin=python_bin,
                model_config=model_config,
                default_backend=default_backend,
            )
            if not result.records:
                error_msg = "; ".join(str(e.get("message", e.get("error_code", "unknown"))) for e in result.errors) if result.errors else f"exit_code={result.exit_code}"
                _write_result(output_dir, {"handoff_id": handoff_id, "status": "failed", "error": error_msg, "records_count": 0})
                store.update_handoff(handoff_id, {"status": "failed", "last_error": error_msg})
                return
            final_records = result.records

    # 尝试回填 pending_agent enrichment
    try:
        filled = _fill_pending_enrichments(records_path, model_config=model_config)
        log.info("[handoff] filled %d pending_agent groups for %s", filled, handoff_id)
    except Exception as exc:
        log.warning("[handoff] enrich fill error for %s: %s", handoff_id, exc)

    # 重新读取 records 检查是否仍有 pending_agent
    final_records = read_jsonl_file(records_path) if records_path.exists() else []
    pending_remaining = 0
    for rec in final_records:
        enrichment = rec.get("enrichment")
        if isinstance(enrichment, dict):
            for _g, r in (enrichment.get("enrichment_results") or {}).items():
                if isinstance(r, dict) and r.get("status") == "pending_agent":
                    pending_remaining += 1

    child_status = "completed" if pending_remaining == 0 else "pending_enrichment"
    _write_result(output_dir, {
        "handoff_id": handoff_id,
        "status": child_status,
        "records_count": len(final_records),
        "pending_groups_remaining": pending_remaining,
        "error": None if pending_remaining == 0 else "pending_agent fields remain after child run",
        "completed_at": int(time.time()),
    })
    if child_status == "completed":
        store.update_handoff(handoff_id, {"status": child_status, "last_error": None})
    log.info("[handoff] %s finished: records=%d, pending=%d", handoff_id, len(final_records), pending_remaining)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="子 agent handoff 执行器")
    parser.add_argument("--state-root", required=True, help="WorkerStateStore 根目录")
    parser.add_argument("--handoff-id", required=True, help="要执行的 handoff ID")
    args = parser.parse_args()
    run_handoff(args.state_root, args.handoff_id)


if __name__ == "__main__":
    main()
