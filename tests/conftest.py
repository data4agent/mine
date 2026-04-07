"""Shared fixtures for mine test suite."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Add scripts/ and project root to sys.path so modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LIB_DIR = PROJECT_ROOT / "lib"

for p in [str(PROJECT_ROOT), str(SCRIPTS_DIR), str(LIB_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def mock_platform_client() -> MagicMock:
    """Mock PlatformClient for testing without network."""
    client = MagicMock()
    client.list_datasets.return_value = [
        {"dataset_id": "ds_test", "source_domains": ["example.com"]},
    ]
    client.claim_repeat_crawl_task.return_value = None
    client.claim_refresh_task.return_value = None
    client.send_unified_heartbeat.return_value = {"data": {}}
    client.send_miner_heartbeat.return_value = {"data": {}}
    client.submit_core_submissions.return_value = {"success": True, "data": {}}
    client.check_url_occupancy.return_value = {}
    return client


@pytest.fixture
def sample_work_item() -> dict[str, Any]:
    """Minimal WorkItem-compatible dict."""
    return {
        "item_id": "test:item-1",
        "source": "backend_claim",
        "url": "https://en.wikipedia.org/wiki/Test",
        "dataset_id": "ds_test",
        "platform": "wikipedia",
        "resource_type": "article",
        "record": {"url": "https://en.wikipedia.org/wiki/Test", "platform": "wikipedia"},
        "metadata": {},
    }
