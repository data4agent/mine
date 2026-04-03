"""Tests for ValidatorStateStore."""
import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, "scripts")

from worker_state import ValidatorStateStore


@pytest.fixture
def store(tmp_path: Path) -> ValidatorStateStore:
    return ValidatorStateStore(tmp_path / "validator_state")


class TestInit:
    def test_creates_state_root(self, tmp_path: Path):
        root = tmp_path / "new_root"
        assert not root.exists()
        store = ValidatorStateStore(root)
        assert root.exists()
        assert store.state_root == root

    def test_existing_directory(self, tmp_path: Path):
        root = tmp_path / "existing"
        root.mkdir()
        store = ValidatorStateStore(root)
        assert store.state_root == root


class TestSession:
    def test_load_empty_session(self, store: ValidatorStateStore):
        assert store.load_session() == {}

    def test_save_and_load(self, store: ValidatorStateStore):
        data = {"validator_state": "running", "epoch_id": "ep-1"}
        store.save_session(data)
        loaded = store.load_session()
        assert loaded == data

    def test_save_overwrites(self, store: ValidatorStateStore):
        store.save_session({"a": 1})
        store.save_session({"b": 2})
        assert store.load_session() == {"b": 2}

    def test_update_session_merges(self, store: ValidatorStateStore):
        store.save_session({"a": 1, "b": 2})
        store.update_session(b=3, c=4)
        assert store.load_session() == {"a": 1, "b": 3, "c": 4}

    def test_update_empty_session(self, store: ValidatorStateStore):
        store.update_session(x="hello")
        assert store.load_session() == {"x": "hello"}

    def test_corrupt_session_returns_empty(self, store: ValidatorStateStore):
        session_path = store.state_root / ValidatorStateStore.SESSION_FILE
        session_path.write_text("not json", encoding="utf-8")
        assert store.load_session() == {}

    def test_session_with_non_dict_returns_empty(self, store: ValidatorStateStore):
        session_path = store.state_root / ValidatorStateStore.SESSION_FILE
        session_path.write_text("[1, 2, 3]", encoding="utf-8")
        assert store.load_session() == {}


class TestBackgroundSession:
    def test_load_empty(self, store: ValidatorStateStore):
        assert store.load_background_session() == {}

    def test_save_and_load(self, store: ValidatorStateStore):
        store.save_background_session(pid=12345, session_id="sess-abc")
        bg = store.load_background_session()
        assert bg["pid"] == 12345
        assert bg["session_id"] == "sess-abc"
        assert "started_at" in bg

    def test_clear(self, store: ValidatorStateStore):
        store.save_background_session(pid=1, session_id="s1")
        assert store.load_background_session() != {}
        store.clear_background_session()
        assert store.load_background_session() == {}

    def test_clear_nonexistent(self, store: ValidatorStateStore):
        # Should not raise
        store.clear_background_session()

    def test_corrupt_background_returns_empty(self, store: ValidatorStateStore):
        bg_path = store.state_root / ValidatorStateStore.BACKGROUND_FILE
        bg_path.write_text("{bad json", encoding="utf-8")
        assert store.load_background_session() == {}


class TestAtomicWrite:
    def test_write_is_atomic(self, store: ValidatorStateStore):
        """Verify that save uses atomic write (temp file + replace)."""
        store.save_session({"key": "value"})
        session_path = store.state_root / ValidatorStateStore.SESSION_FILE
        assert session_path.exists()
        content = json.loads(session_path.read_text(encoding="utf-8"))
        assert content == {"key": "value"}
        # No leftover .tmp files
        tmp_files = list(store.state_root.glob("*.tmp"))
        assert tmp_files == []
