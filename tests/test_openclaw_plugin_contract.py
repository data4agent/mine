from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest

import build_openclaw_plugin
import install_openclaw_integration


ROOT = Path(__file__).resolve().parents[1]


def test_plugin_metadata_uses_mine_identity() -> None:
    package_payload = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    manifest_payload = json.loads((ROOT / "openclaw.plugin.json").read_text(encoding="utf-8"))

    assert package_payload["name"] == "mine"
    assert manifest_payload["id"] == "mine"
    assert manifest_payload["name"] == "Mine"


def test_build_script_packages_current_project_root() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_openclaw_plugin.py"), "--no-archive"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    payload = json.loads(lines[-1])

    assert payload["dist"] == str((ROOT / "dist" / "openclaw-plugin").resolve())
    manifest = json.loads((ROOT / "dist" / "openclaw-plugin" / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"] == str(ROOT.resolve())
    assert "package.json" in manifest["files"]
    assert "openclaw.plugin.json" in manifest["files"]
    assert "tests/test_openclaw_plugin_contract.py" not in manifest["files"]


def test_install_skill_wrapper_uses_mine_identity(workspace_tmp_path: Path) -> None:
    skill_dir = install_openclaw_integration.install_skill_wrapper(
        workspace_tmp_path / ".openclaw",
        ROOT,
    )

    content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "name: mine" in content
    assert "Mine" in content
    assert str(ROOT / "SKILL.md") in content


def test_archive_source_requires_existing_tarball(workspace_tmp_path: Path) -> None:
    config_path = workspace_tmp_path / "openclaw.json"
    args = argparse.Namespace(
        python_bin="python",
        platform_base_url="https://platform.example.test",
        platform_token="",
        miner_id="miner-123",
        gateway_base_url="http://127.0.0.1:18789/v1",
        awp_wallet_bin="awp-wallet",
        awp_wallet_token_env="AWP_WALLET_TOKEN",
        plugin_source=install_openclaw_integration.PLUGIN_SOURCE_ARCHIVE,
    )

    missing_archive = ROOT / "dist" / "mine-openclaw-plugin.tar.gz"
    if missing_archive.exists():
        missing_archive.unlink()

    with pytest.raises(FileNotFoundError):
        install_openclaw_integration.update_openclaw_config(
            config_path=config_path,
            crawler_root=ROOT,
            plugin_root=(ROOT / "dist" / "openclaw-plugin"),
            args=args,
            awp_wallet_token="",
        )

    assert not config_path.exists()

