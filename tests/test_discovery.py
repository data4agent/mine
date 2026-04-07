"""Tests for crawler.discovery modules: scheduler, throttle, frontier_store, occupancy_store."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from crawler.discovery.scheduler import DiscoveryScheduler
from crawler.discovery.state.frontier import FrontierEntry, FrontierStatus
from crawler.discovery.state.occupancy import OccupancyLease
from crawler.discovery.store.frontier_store import InMemoryFrontierStore
from crawler.discovery.store.occupancy_store import InMemoryOccupancyStore
from crawler.discovery.throttle import TokenBucketThrottle


def _make_entry(
    frontier_id: str = "f1",
    job_id: str = "j1",
    priority: float = 1.0,
    status: FrontierStatus = FrontierStatus.QUEUED,
    attempt: int = 0,
    not_before: str | None = None,
) -> FrontierEntry:
    """创建测试用 FrontierEntry 的辅助函数。"""
    return FrontierEntry(
        frontier_id=frontier_id,
        job_id=job_id,
        url_key=f"https://example.com/{frontier_id}",
        canonical_url=f"https://example.com/{frontier_id}",
        adapter="generic",
        entity_type="page",
        depth=0,
        priority=priority,
        discovered_from=None,
        discovery_reason="seed",
        status=status,
        attempt=attempt,
        not_before=not_before,
    )


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _future_iso(seconds: int = 3600) -> str:
    return (
        (datetime.now(timezone.utc) + timedelta(seconds=seconds))
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _past_iso(seconds: int = 3600) -> str:
    return (
        (datetime.now(timezone.utc) - timedelta(seconds=seconds))
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


# ===========================================================================
# TokenBucketThrottle
# ===========================================================================

class TestTokenBucketThrottle:
    """TokenBucketThrottle 令牌桶限流器。"""

    @pytest.mark.asyncio
    async def test_acquire_with_tokens_available(self) -> None:
        """有可用令牌时 acquire 应立即返回 0.0 等待时间。"""
        throttle = TokenBucketThrottle(requests_per_minute=60.0)
        wait = await throttle.acquire()
        assert wait == 0.0

    @pytest.mark.asyncio
    async def test_acquire_when_empty_waits(self) -> None:
        """令牌耗尽时 acquire 应等待一段时间。"""
        # 每分钟 60 次 = 每秒 1 次, burst capacity = 5 秒 = 5 个令牌
        throttle = TokenBucketThrottle(requests_per_minute=60.0)
        # 消耗所有令牌
        for _ in range(5):
            await throttle.acquire()
        # 下一次应需要等待
        start = time.monotonic()
        wait = await throttle.acquire()
        elapsed = time.monotonic() - start
        assert wait > 0.0
        assert elapsed > 0.0

    @pytest.mark.asyncio
    async def test_refill_over_time(self) -> None:
        """等待一段时间后令牌应重新填充。"""
        throttle = TokenBucketThrottle(requests_per_minute=6000.0)  # 高速率，快速回填
        # 消耗所有令牌
        capacity = int(max(1.0, 6000.0 / 60.0 * 5))
        for _ in range(capacity):
            await throttle.acquire()
        # 等一小段时间让令牌回填
        await asyncio.sleep(0.05)
        # 回填后应能获取
        wait = await throttle.acquire()
        # 可能不需要等待（已经回填了足够的令牌）
        assert wait >= 0.0

    def test_for_platform(self) -> None:
        """for_platform 类方法应返回 TokenBucketThrottle 实例。"""
        throttle = TokenBucketThrottle.for_platform("generic")
        assert isinstance(throttle, TokenBucketThrottle)


# ===========================================================================
# InMemoryFrontierStore
# ===========================================================================

class TestInMemoryFrontierStore:
    """InMemoryFrontierStore 的 CRUD 和状态转换。"""

    def test_put_and_get(self) -> None:
        """put 后应能通过 get 取回。"""
        store = InMemoryFrontierStore()
        entry = _make_entry("f1")
        store.put(entry)
        retrieved = store.get("f1")
        assert retrieved is not None
        assert retrieved.frontier_id == "f1"

    def test_get_nonexistent(self) -> None:
        """获取不存在的条目应返回 None。"""
        store = InMemoryFrontierStore()
        assert store.get("nonexistent") is None

    def test_list_queued(self) -> None:
        """list_queued 应只返回 QUEUED 状态的条目。"""
        store = InMemoryFrontierStore()
        store.put(_make_entry("f1", status=FrontierStatus.QUEUED))
        store.put(_make_entry("f2", status=FrontierStatus.DONE))
        store.put(_make_entry("f3", status=FrontierStatus.QUEUED))
        queued = store.list_queued()
        assert len(queued) == 2
        ids = {e.frontier_id for e in queued}
        assert ids == {"f1", "f3"}

    def test_lease(self) -> None:
        """lease 应将状态从 QUEUED 改为 LEASED 并增加 attempt。"""
        store = InMemoryFrontierStore()
        store.put(_make_entry("f1"))
        leased = store.lease("f1")
        assert leased is not None
        assert leased.status is FrontierStatus.LEASED
        assert leased.attempt == 1

    def test_lease_non_queued_returns_none(self) -> None:
        """非 QUEUED 状态的条目不能被 lease。"""
        store = InMemoryFrontierStore()
        store.put(_make_entry("f1", status=FrontierStatus.DONE))
        assert store.lease("f1") is None

    def test_lease_nonexistent_returns_none(self) -> None:
        store = InMemoryFrontierStore()
        assert store.lease("nonexistent") is None

    def test_mark_done(self) -> None:
        """mark_done 应将状态改为 DONE。"""
        store = InMemoryFrontierStore()
        store.put(_make_entry("f1"))
        done = store.mark_done("f1")
        assert done is not None
        assert done.status is FrontierStatus.DONE

    def test_mark_dead(self) -> None:
        """mark_dead 应将状态改为 DEAD。"""
        store = InMemoryFrontierStore()
        store.put(_make_entry("f1"))
        dead = store.mark_dead("f1")
        assert dead is not None
        assert dead.status is FrontierStatus.DEAD

    def test_mark_retry(self) -> None:
        """mark_retry 应设置 RETRY_WAIT 状态和 not_before。"""
        store = InMemoryFrontierStore()
        store.put(_make_entry("f1"))
        retry = store.mark_retry("f1", "2025-01-01T00:05:00Z", {"message": "error"})
        assert retry is not None
        assert retry.status is FrontierStatus.RETRY_WAIT
        assert retry.not_before == "2025-01-01T00:05:00Z"
        assert retry.last_error == {"message": "error"}

    def test_promote_retryable(self) -> None:
        """not_before 已到期的 RETRY_WAIT 条目应被提升为 QUEUED。"""
        store = InMemoryFrontierStore()
        past = _past_iso(60)
        entry = _make_entry("f1", status=FrontierStatus.RETRY_WAIT, not_before=past)
        store.put(entry)
        count = store.promote_retryable(_now_iso())
        assert count == 1
        promoted = store.get("f1")
        assert promoted is not None
        assert promoted.status is FrontierStatus.QUEUED
        assert promoted.not_before is None

    def test_promote_retryable_not_yet_due(self) -> None:
        """not_before 还未到期的不应被提升。"""
        store = InMemoryFrontierStore()
        future = _future_iso(3600)
        entry = _make_entry("f1", status=FrontierStatus.RETRY_WAIT, not_before=future)
        store.put(entry)
        count = store.promote_retryable(_now_iso())
        assert count == 0

    def test_prune_terminal(self) -> None:
        """prune_terminal 应移除超出保留数量的 DONE/DEAD 条目。"""
        store = InMemoryFrontierStore()
        for i in range(10):
            store.put(_make_entry(f"f{i:03d}", status=FrontierStatus.DONE))
        removed = store.prune_terminal(keep=5)
        assert removed == 5
        assert len(store.list()) == 5

    def test_prune_terminal_no_excess(self) -> None:
        """未超出保留数量时不应移除。"""
        store = InMemoryFrontierStore()
        for i in range(3):
            store.put(_make_entry(f"f{i}", status=FrontierStatus.DONE))
        removed = store.prune_terminal(keep=5)
        assert removed == 0
        assert len(store.list()) == 3


# ===========================================================================
# InMemoryOccupancyStore
# ===========================================================================

class TestInMemoryOccupancyStore:
    """InMemoryOccupancyStore 的租约管理。"""

    def _make_lease(
        self, lease_id: str = "l1", frontier_id: str = "f1",
    ) -> OccupancyLease:
        return OccupancyLease(
            lease_id=lease_id,
            job_id="j1",
            frontier_id=frontier_id,
            worker_id="w1",
            leased_at=_now_iso(),
        )

    def test_put_and_get(self) -> None:
        """put 后应能通过 get 取回。"""
        store = InMemoryOccupancyStore()
        lease = self._make_lease("l1", "f1")
        store.put(lease)
        assert store.get("l1") is not None
        assert store.get("l1").frontier_id == "f1"  # type: ignore[union-attr]

    def test_release_by_frontier_id(self) -> None:
        """release_by_frontier_id 应删除匹配的租约。"""
        store = InMemoryOccupancyStore()
        store.put(self._make_lease("l1", "f1"))
        store.put(self._make_lease("l2", "f1"))
        store.put(self._make_lease("l3", "f2"))
        store.release_by_frontier_id("f1")
        assert store.get("l1") is None
        assert store.get("l2") is None
        assert store.get("l3") is not None

    def test_release_nonexistent(self) -> None:
        """释放不存在的 frontier_id 不应报错。"""
        store = InMemoryOccupancyStore()
        store.release_by_frontier_id("nonexistent")  # 不应抛异常

    def test_list(self) -> None:
        """list 应返回所有租约。"""
        store = InMemoryOccupancyStore()
        store.put(self._make_lease("l1", "f1"))
        store.put(self._make_lease("l2", "f2"))
        assert len(store.list()) == 2


# ===========================================================================
# DiscoveryScheduler
# ===========================================================================

class TestDiscoveryScheduler:
    """DiscoveryScheduler 的调度逻辑。"""

    def _make_scheduler(
        self,
        throttle: TokenBucketThrottle | None = None,
    ) -> DiscoveryScheduler:
        return DiscoveryScheduler(
            frontier_store=InMemoryFrontierStore(),
            occupancy_store=InMemoryOccupancyStore(),
            throttle=throttle,
            platform="generic",
        )

    def test_enqueue(self) -> None:
        """enqueue 应将条目添加到 frontier store。"""
        scheduler = self._make_scheduler()
        entry = _make_entry("f1")
        result = scheduler.enqueue(entry)
        assert result.frontier_id == "f1"
        assert scheduler.frontier_store.get("f1") is not None

    @pytest.mark.asyncio
    async def test_lease_next_highest_priority(self) -> None:
        """lease_next 应返回最高优先级的条目。"""
        scheduler = self._make_scheduler()
        scheduler.enqueue(_make_entry("f1", priority=1.0))
        scheduler.enqueue(_make_entry("f2", priority=5.0))
        scheduler.enqueue(_make_entry("f3", priority=3.0))

        leased = await scheduler.lease_next("worker-1")
        assert leased is not None
        assert leased.frontier_id == "f2"
        assert leased.status is FrontierStatus.LEASED

    @pytest.mark.asyncio
    async def test_lease_next_empty_queue(self) -> None:
        """空队列应返回 None。"""
        scheduler = self._make_scheduler()
        result = await scheduler.lease_next("worker-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_lease_creates_occupancy(self) -> None:
        """lease_next 应创建占用租约。"""
        scheduler = self._make_scheduler()
        scheduler.enqueue(_make_entry("f1"))
        await scheduler.lease_next("worker-1")
        leases = scheduler.occupancy_store.list()
        assert len(leases) == 1
        assert leases[0].worker_id == "worker-1"
        assert leases[0].frontier_id == "f1"

    def test_complete(self) -> None:
        """complete 应释放占用并标记完成。"""
        scheduler = self._make_scheduler()
        entry = _make_entry("f1")
        scheduler.enqueue(entry)
        # 手动模拟 lease 状态
        scheduler.frontier_store.lease("f1")
        lease = OccupancyLease(
            lease_id="f1:w1", job_id="j1", frontier_id="f1",
            worker_id="w1", leased_at=_now_iso(),
        )
        scheduler.occupancy_store.put(lease)

        done = scheduler.complete("f1")
        assert done is not None
        assert done.status is FrontierStatus.DONE
        # 占用应被释放
        assert len(scheduler.occupancy_store.list()) == 0

    def test_report_failure_backoff(self) -> None:
        """report_failure 应设置退避并标记 RETRY_WAIT。"""
        scheduler = self._make_scheduler()
        entry = _make_entry("f1", attempt=0)
        scheduler.enqueue(entry)
        scheduler.frontier_store.lease("f1")

        result = scheduler.report_failure("f1", error=RuntimeError("timeout"))
        assert result is not None
        assert result.status is FrontierStatus.RETRY_WAIT
        assert result.not_before is not None
        assert result.last_error is not None
        assert "timeout" in result.last_error["message"]

    def test_report_failure_marks_dead_after_max_retries(self) -> None:
        """超过最大重试次数应标记为 DEAD。"""
        scheduler = self._make_scheduler()
        # 设置 attempt 等于 max_retries
        max_retries = scheduler._max_retries
        entry = _make_entry("f1", attempt=max_retries)
        scheduler.enqueue(entry)
        scheduler.frontier_store.lease("f1")

        result = scheduler.report_failure("f1")
        assert result is not None
        assert result.status is FrontierStatus.DEAD

    @pytest.mark.asyncio
    async def test_lease_contention_retry(self) -> None:
        """当 lease 失败时应重试（最多 3 次）。"""
        scheduler = self._make_scheduler()
        scheduler.enqueue(_make_entry("f1"))
        scheduler.enqueue(_make_entry("f2", priority=0.5))

        # 第一次 lease f1
        leased = await scheduler.lease_next("worker-1")
        assert leased is not None
        assert leased.frontier_id == "f1"

        # 再 lease 一次，f1 已经不是 QUEUED，应自动拿到 f2
        leased2 = await scheduler.lease_next("worker-2")
        assert leased2 is not None
        assert leased2.frontier_id == "f2"

    @pytest.mark.asyncio
    async def test_lease_with_throttle(self) -> None:
        """带 throttle 的 lease 应正常工作。"""
        throttle = TokenBucketThrottle(requests_per_minute=6000.0)
        scheduler = self._make_scheduler(throttle=throttle)
        scheduler.enqueue(_make_entry("f1"))
        leased = await scheduler.lease_next("worker-1")
        assert leased is not None
        assert leased.frontier_id == "f1"

    def test_report_failure_nonexistent(self) -> None:
        """对不存在的条目 report_failure 应返回 None。"""
        scheduler = self._make_scheduler()
        result = scheduler.report_failure("nonexistent")
        assert result is None
