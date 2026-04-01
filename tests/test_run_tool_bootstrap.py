from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def test_run_tool_injects_skill_root_into_sys_path(monkeypatch) -> None:
    run_tool_path = Path(__file__).resolve().parents[1] / "scripts" / "run_tool.py"
    skill_root = run_tool_path.parents[1]
    cleaned_sys_path = [
        entry for entry in sys.path if Path(entry or ".").resolve() != skill_root.resolve()
    ]
    monkeypatch.setattr(sys, "path", cleaned_sys_path)

    module_name = "test_run_tool_bootstrap_target"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, run_tool_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert sys.path[0] == str(skill_root)
