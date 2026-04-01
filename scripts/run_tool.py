from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mine")
    parser.add_argument(
        "command",
        choices=(
            "first-load",
            "check-again",
            "start-working",
            "check-status",
            "status-json",
            "list-datasets",
            "pause",
            "resume",
            "stop",
            "heartbeat",
            "run-once",
            "run-loop",
            "run-worker",
            "process-task-file",
            "export-core-submissions",
            "route-intent",
            "classify-intent",
            "intent-help",
        ),
    )
    parser.add_argument("args", nargs="*")
    return parser


def main() -> int:
    namespace = build_parser().parse_args()
    from skill_runtime import (
        classify_intent,
        render_control_response,
        render_dataset_listing,
        render_first_load_experience,
        render_intent_help,
        render_start_working_response,
        render_status_summary,
        route_and_execute,
    )

    if namespace.command in {"first-load", "check-again"}:
        print(render_first_load_experience())
        return 0

    if namespace.command == "intent-help":
        print(render_intent_help())
        return 0

    if namespace.command == "classify-intent":
        if not namespace.args:
            print("Usage: classify-intent <user_input>")
            return 1
        user_input = " ".join(namespace.args)
        result = classify_intent(user_input)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if namespace.command == "route-intent":
        if not namespace.args:
            print("Usage: route-intent <user_input>")
            return 1
        user_input = " ".join(namespace.args)
        from agent_runtime import build_worker_from_env
        worker = build_worker_from_env()
        result = route_and_execute(user_input, worker)
        if result.get("executed"):
            print(result.get("output", ""))
        else:
            print(result.get("output", ""))
            if result.get("needs_confirmation"):
                print("\n(Awaiting confirmation)")
        return 0

    from agent_runtime import build_worker_from_env, export_core_submissions
    worker = build_worker_from_env()

    if namespace.command == "start-working":
        selected_dataset_ids = []
        if namespace.args:
            selected_dataset_ids = [dataset_id.strip() for dataset_id in namespace.args[0].split(",") if dataset_id.strip()]
        print(render_start_working_response(worker, selected_dataset_ids=selected_dataset_ids or None))
        return 0

    if namespace.command == "check-status":
        print(render_status_summary(worker))
        return 0

    if namespace.command == "status-json":
        print(json.dumps(worker.check_status(), ensure_ascii=False, indent=2))
        return 0

    if namespace.command == "list-datasets":
        print(render_dataset_listing(worker.list_datasets()["datasets"] if hasattr(worker, "list_datasets") else worker.client))
        return 0

    if namespace.command == "pause":
        print(render_control_response(worker.pause()))
        return 0

    if namespace.command == "resume":
        print(render_control_response(worker.resume()))
        return 0

    if namespace.command == "stop":
        print(render_control_response(worker.stop()))
        return 0

    if namespace.command == "heartbeat":
        worker.client.send_miner_heartbeat(client_name=worker.config.client_name)
        print("heartbeat sent")
        return 0

    if namespace.command == "run-once":
        print(worker.run_once())
        return 0

    if namespace.command == "run-loop":
        interval = int(namespace.args[0]) if namespace.args else 60
        max_iter = int(namespace.args[1]) if len(namespace.args) > 1 else 0
        print(worker.run_loop(interval=interval, max_iterations=max_iter))
        return 0

    if namespace.command == "run-worker":
        interval = int(namespace.args[0]) if namespace.args else 60
        max_iter = int(namespace.args[1]) if len(namespace.args) > 1 else 1
        print(json.dumps(worker.run_worker(interval=interval, max_iterations=max_iter), ensure_ascii=False, indent=2))
        return 0

    if namespace.command == "process-task-file":
        if len(namespace.args) != 2:
            raise SystemExit("process-task-file requires: <taskType> <taskJsonPath>")
        task_type, task_json_path = namespace.args
        payload = json.loads(Path(task_json_path).read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise SystemExit("task payload file must contain a JSON object")
        print(worker.process_task_payload(task_type, payload))
        return 0

    if len(namespace.args) != 3:
        raise SystemExit("export-core-submissions requires: <inputPath> <outputPath> <datasetId>")
    output = export_core_submissions(namespace.args[0], namespace.args[1], namespace.args[2])
    print(f"exported core submissions to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
