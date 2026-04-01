from __future__ import annotations

import pytest

from crawler.discovery import bfs_engine
from crawler.discovery.adapters.base import BaseDiscoveryAdapter
from crawler.discovery.bfs_engine import BfsOptions
from crawler.discovery.expand.base import ExpandResult
from crawler.discovery.normalize.base import NormalizeResult
from crawler.discovery.state.frontier import FrontierStatus


class StubBfsAdapter(BaseDiscoveryAdapter):
    platform = "generic"
    supported_resource_types = ("page",)

    def can_handle_url(self, url: str) -> bool:
        return True

    def build_seed_records(self, input_record: dict[str, object]) -> list[object]:
        raise NotImplementedError

    async def map(self, seed: object, context: dict[str, object]) -> object:
        raise NotImplementedError

    async def crawl(self, candidate: object, context: dict[str, object]) -> object:
        raise NotImplementedError

    def normalize_url(self, url: str) -> NormalizeResult:
        return NormalizeResult(
            entity_type="page",
            canonical_url=url,
            original_url=url,
        )

    async def expand(self, candidate: object, fetch_fn: object, options: dict[str, object] | None = None) -> ExpandResult:
        return ExpandResult(urls=[])


@pytest.mark.asyncio
async def test_run_bfs_expand_closes_depth_limited_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class CapturingScheduler(bfs_engine.DiscoveryScheduler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            captured["scheduler"] = self

    monkeypatch.setattr(bfs_engine, "DiscoveryScheduler", CapturingScheduler)

    async def fake_fetch(url: str) -> str:
        return f"<html>{url}</html>"

    result, _ = await bfs_engine.run_bfs_expand(
        seed_urls=["https://example.com/root"],
        fetch_fn=fake_fetch,
        adapter=StubBfsAdapter(),
        options=BfsOptions(max_expand_depth=0, max_pages=5),
    )

    scheduler = captured["scheduler"]
    assert isinstance(scheduler, CapturingScheduler)
    assert result.expansions_run == 0
    assert scheduler.frontier_store.get("seed-0").status is FrontierStatus.DONE


@pytest.mark.asyncio
async def test_run_bfs_expand_closes_visited_duplicate_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class CapturingScheduler(bfs_engine.DiscoveryScheduler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            captured["scheduler"] = self

    monkeypatch.setattr(bfs_engine, "DiscoveryScheduler", CapturingScheduler)

    async def fake_fetch(url: str) -> str:
        return f"<html>{url}</html>"

    result, _ = await bfs_engine.run_bfs_expand(
        seed_urls=[
            "https://example.com/root",
            "https://example.com/root",
        ],
        fetch_fn=fake_fetch,
        adapter=StubBfsAdapter(),
        options=BfsOptions(max_expand_depth=2, max_pages=5),
    )

    scheduler = captured["scheduler"]
    assert isinstance(scheduler, CapturingScheduler)
    assert result.expansions_run == 1
    assert all(
        entry.status is FrontierStatus.DONE
        for entry in scheduler.frontier_store.list()
    )
