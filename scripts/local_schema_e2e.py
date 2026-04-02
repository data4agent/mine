#!/usr/bin/env python3
"""
Local end-to-end tasks: run `crawler run` on local_tasks/*.json and check schema(1) alignment on successful records.

Usage (from mine repo root):
  python scripts/local_schema_e2e.py --dry-run
  python scripts/local_schema_e2e.py --only wikipedia-openai-local
  python scripts/local_schema_e2e.py --auto-login   # platforms that need a browser session (e.g. LinkedIn)

Alignment: for each record, call crawler.schema_contract.flatten_record_for_schema and verify every
schema `required` field has a non-empty value in the flattened map.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

for _p in (SKILL_ROOT, SCRIPT_DIR):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

from common import inject_crawler_root  # noqa: E402

inject_crawler_root()

from crawler.output import read_jsonl_file  # noqa: E402
from crawler.schema_contract import flatten_record_for_schema, get_schema_contract  # noqa: E402
from task_sources import local_task_from_payload, task_to_work_item  # noqa: E402

DEFAULT_SUITE = [
    "wikipedia-openai-local.json",
    "arxiv-transformers-local.json",
    "amazon-echo-local.json",
    "generic-python-docs-local.json",
]


@dataclass(slots=True)
class TaskReport:
    task_file: str
    task_id: str
    platform: str
    resource_type: str
    exit_code: int
    records_total: int
    records_ok: int
    schema_dataset: str | None
    required_total: int
    required_filled: int
    missing_required: list[str]
    flatten_error: str | None
    skipped_no_contract: bool
    note: str


def _load_task_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def _analyze_record(record: dict[str, Any]) -> tuple[TaskReport | None, dict[str, Any]]:
    """Return (report for first analyzable record, flattened map or error payload)."""
    platform = str(record.get("platform") or "").strip().lower()
    resource = str(record.get("resource_type") or "").strip().lower()
    if platform == "generic":
        return (
            TaskReport(
                task_file="",
                task_id="",
                platform=platform,
                resource_type=resource,
                exit_code=0,
                records_total=0,
                records_ok=0,
                schema_dataset=None,
                required_total=0,
                required_filled=0,
                missing_required=[],
                flatten_error=None,
                skipped_no_contract=True,
                note="generic/page has no schema(1) contract; alignment skipped",
            ),
            {},
        )
    try:
        contract = get_schema_contract(record)
    except ValueError as exc:
        return (
            TaskReport(
                task_file="",
                task_id="",
                platform=platform,
                resource_type=resource,
                exit_code=0,
                records_total=0,
                records_ok=0,
                schema_dataset=None,
                required_total=0,
                required_filled=0,
                missing_required=[],
                flatten_error=str(exc),
                skipped_no_contract=True,
                note="could not resolve schema contract",
            ),
            {"error": str(exc)},
        )

    try:
        flat = flatten_record_for_schema(record)
    except Exception as exc:
        return (
            TaskReport(
                task_file="",
                task_id="",
                platform=platform,
                resource_type=resource,
                exit_code=0,
                records_total=0,
                records_ok=0,
                schema_dataset=contract.dataset_name,
                required_total=len(contract.required_fields),
                required_filled=0,
                missing_required=list(contract.required_fields),
                flatten_error=str(exc),
                skipped_no_contract=False,
                note="flatten_record_for_schema failed",
            ),
            {"error": str(exc)},
        )

    missing: list[str] = []
    for name in contract.required_fields:
        v = flat.get(name)
        if v in (None, "", [], {}):
            missing.append(name)

    filled = len(contract.required_fields) - len(missing)
    return (
        TaskReport(
            task_file="",
            task_id="",
            platform=platform,
            resource_type=resource,
            exit_code=0,
            records_total=0,
            records_ok=0,
            schema_dataset=contract.dataset_name,
            required_total=len(contract.required_fields),
            required_filled=filled,
            missing_required=missing,
            flatten_error=None,
            skipped_no_contract=False,
            note="",
        ),
        flat,
    )


def _dry_run_meta(record: dict[str, Any]) -> TaskReport:
    """Resolve contract metadata from the task seed only (no flatten alignment; record incomplete before crawl)."""
    platform = str(record.get("platform") or "").strip().lower()
    resource = str(record.get("resource_type") or "").strip().lower()
    if platform == "generic":
        return TaskReport(
            task_file="",
            task_id="",
            platform=platform,
            resource_type=resource,
            exit_code=0,
            records_total=0,
            records_ok=0,
            schema_dataset=None,
            required_total=0,
            required_filled=0,
            missing_required=[],
            flatten_error=None,
            skipped_no_contract=True,
            note="generic/page has no schema(1) contract",
        )
    try:
        contract = get_schema_contract(record)
    except ValueError as exc:
        return TaskReport(
            task_file="",
            task_id="",
            platform=platform,
            resource_type=resource,
            exit_code=0,
            records_total=0,
            records_ok=0,
            schema_dataset=None,
            required_total=0,
            required_filled=0,
            missing_required=[],
            flatten_error=str(exc),
            skipped_no_contract=True,
            note="could not resolve schema contract",
        )
    return TaskReport(
        task_file="",
        task_id="",
        platform=platform,
        resource_type=resource,
        exit_code=0,
        records_total=0,
        records_ok=0,
        schema_dataset=contract.dataset_name,
        required_total=len(contract.required_fields),
        required_filled=0,
        missing_required=[],
        flatten_error=None,
        skipped_no_contract=False,
        note=f"required fields={len(contract.required_fields)}, total properties={len(contract.property_names)}",
    )


def run_one_task(
    task_path: Path,
    *,
    out_root: Path,
    auto_login: bool,
    dry_run: bool,
) -> TaskReport:
    payload = _load_task_json(task_path)
    envelope = local_task_from_payload({"task_type": "local_file", **payload})
    item = task_to_work_item(envelope)
    task_id = envelope.task_id
    out_dir = out_root / task_id
    input_path = out_dir / "task-input.jsonl"

    if dry_run:
        meta = _dry_run_meta(dict(item.record))
        return TaskReport(
            task_file=task_path.name,
            task_id=task_id,
            platform=str(item.platform or ""),
            resource_type=str(item.resource_type or ""),
            exit_code=0,
            records_total=0,
            records_ok=0,
            schema_dataset=meta.schema_dataset,
            required_total=meta.required_total,
            required_filled=0,
            missing_required=[],
            flatten_error=meta.flatten_error,
            skipped_no_contract=meta.skipped_no_contract,
            note=meta.note + " [dry-run: crawler not executed]",
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    input_path.write_text(json.dumps(item.record, ensure_ascii=False) + "\n", encoding="utf-8")

    argv = [
        sys.executable,
        "-m",
        "crawler",
        "run",
        "--input",
        str(input_path),
        "--output",
        str(out_dir),
    ]
    if auto_login:
        argv.append("--auto-login")

    proc = subprocess.run(argv, cwd=str(SKILL_ROOT), capture_output=True, text=True)
    records_path = out_dir / "records.jsonl"
    records = read_jsonl_file(records_path) if records_path.exists() else []
    errors_path = out_dir / "errors.jsonl"
    errors = read_jsonl_file(errors_path) if errors_path.exists() else []

    ok_records = [r for r in records if str(r.get("status") or "").lower() in {"success", "partial"}]

    if not records and proc.returncode != 0:
        return TaskReport(
            task_file=task_path.name,
            task_id=task_id,
            platform=str(item.platform or ""),
            resource_type=str(item.resource_type or ""),
            exit_code=proc.returncode,
            records_total=0,
            records_ok=0,
            schema_dataset=None,
            required_total=0,
            required_filled=0,
            missing_required=[],
            flatten_error=(proc.stderr or proc.stdout or "")[:2000],
            skipped_no_contract=False,
            note=f"no valid records; errors={len(errors)}; see output directory",
        )

    # Align against the first successful record (single-URL tasks usually have one)
    target = ok_records[0] if ok_records else (records[0] if records else None)
    if target is None:
        return TaskReport(
            task_file=task_path.name,
            task_id=task_id,
            platform=str(item.platform or ""),
            resource_type=str(item.resource_type or ""),
            exit_code=proc.returncode,
            records_total=len(records),
            records_ok=0,
            schema_dataset=None,
            required_total=0,
            required_filled=0,
            missing_required=[],
            flatten_error="records.jsonl is empty",
            skipped_no_contract=False,
            note="",
        )

    rep, _ = _analyze_record(target)
    if rep is None:
        raise RuntimeError("unexpected")
    return TaskReport(
        task_file=task_path.name,
        task_id=task_id,
        platform=str(target.get("platform") or item.platform or ""),
        resource_type=str(target.get("resource_type") or item.resource_type or ""),
        exit_code=proc.returncode,
        records_total=len(records),
        records_ok=len(ok_records),
        schema_dataset=rep.schema_dataset,
        required_total=rep.required_total,
        required_filled=rep.required_filled,
        missing_required=rep.missing_required,
        flatten_error=rep.flatten_error,
        skipped_no_contract=rep.skipped_no_contract,
        note=rep.note,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Local task schema(1) alignment E2E")
    parser.add_argument(
        "--tasks-dir",
        type=Path,
        default=SKILL_ROOT / "local_tasks",
        help="Directory containing local_tasks JSON files",
    )
    parser.add_argument("--only", type=str, default="", help="Run only tasks whose id or filename contains this substring")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve task metadata only; do not run the crawler",
    )
    parser.add_argument("--auto-login", action="store_true", help="Pass --auto-login to the crawler")
    parser.add_argument(
        "--out",
        type=Path,
        default=SKILL_ROOT / "test_output" / "local_schema_e2e",
        help="Root output directory for crawl artifacts",
    )
    args = parser.parse_args()

    tasks_dir: Path = args.tasks_dir
    files = [tasks_dir / name for name in DEFAULT_SUITE if (tasks_dir / name).exists()]
    if args.only:
        key = args.only.strip().lower()
        files = [p for p in files if key in p.name.lower() or key in p.stem.lower()]

    if not files:
        print(json.dumps({"error": "no task files matched", "tasks_dir": str(tasks_dir)}, ensure_ascii=False, indent=2))
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    reports: list[TaskReport] = []
    for path in files:
        reports.append(
            run_one_task(
                path,
                out_root=args.out,
                auto_login=args.auto_login,
                dry_run=args.dry_run,
            )
        )

    payload = {
        "tasks_dir": str(tasks_dir),
        "output_root": str(args.out),
        "dry_run": args.dry_run,
        "reports": [asdict(r) for r in reports],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    bad = [
        r
        for r in reports
        if not r.skipped_no_contract and r.missing_required and r.exit_code == 0
    ]
    if any(r.exit_code != 0 for r in reports) or bad:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
