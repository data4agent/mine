from __future__ import annotations

import hashlib
import random
import re
import threading
import time
from typing import Any
from urllib.parse import unquote, urlparse

from lib.canonicalize import canonicalize_url
from run_models import TaskEnvelope, WorkItem
from worker_state import WorkerStateStore
from ws_client import WSDisconnected


class SkipClaimedTask(Exception):
    """Claimed task cannot be materialized (placeholder submission, missing URL, etc.); not a local config fault."""

    pass


def optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def claimed_task_from_payload(
    task_type: str,
    payload: dict[str, Any],
    *,
    client: Any | None = None,  # kept for backward compat, no longer used
) -> TaskEnvelope:
    task_id = str(payload.get("id") or "").strip()
    if not task_id:
        raise ValueError("task payload is missing id")
    url = canonicalize_url(str(payload.get("url") or payload.get("target_url") or "").strip())
    if not url:
        raise SkipClaimedTask(f"task {task_id} ({task_type}) has no url in claim response")
    platform, resource_type, _ = infer_platform_task(url)
    metadata = dict(payload)
    metadata.pop("id", None)
    metadata.pop("url", None)
    metadata.pop("target_url", None)
    return TaskEnvelope(
        task_id=task_id,
        task_source="backend_claim",
        task_type=task_type,
        url=url,
        dataset_id=optional_string(payload.get("dataset_id")),
        platform=optional_string(payload.get("platform")) or platform,
        resource_type=optional_string(payload.get("resource_type")) or resource_type,
        metadata=metadata,
    )




def infer_platform_task(url: str) -> tuple[str, str, dict[str, str]]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path

    if host.endswith("en.wikipedia.org") and path.startswith("/wiki/"):
        title = unquote(path.split("/wiki/", 1)[1]).replace("_", " ")
        return "wikipedia", "article", {"title": title}

    if host.endswith("arxiv.org") and path.startswith("/abs/"):
        arxiv_id = path.split("/abs/", 1)[1].strip("/")
        return "arxiv", "paper", {"arxiv_id": arxiv_id}

    if host.endswith("www.linkedin.com"):
        linkedin_patterns = (
            (r"^/in/([^/]+)/?$", "profile", "public_identifier"),
            (r"^/company/([^/]+)/?$", "company", "company_slug"),
            (r"^/jobs/view/(\d+)/?$", "job", "job_id"),
            (r"^/feed/update/([^/]+)/?$", "post", "activity_urn"),
        )
        for pattern, resource_type, field_name in linkedin_patterns:
            match = re.match(pattern, path)
            if match:
                return "linkedin", resource_type, {field_name: match.group(1)}

    if host.endswith("www.amazon.com"):
        dp_match = re.search(r"/dp/([A-Z0-9]{10})(?:/|$)", path)
        if dp_match:
            return "amazon", "product", {"asin": dp_match.group(1)}

    if host.endswith("basescan.org") or host.endswith("base.org"):
        for prefix, resource_type, field_name in (
            ("/address/", "address", "address"),
            ("/tx/", "transaction", "tx_hash"),
            ("/token/", "token", "contract_address"),
        ):
            if path.startswith(prefix):
                return "base", resource_type, {field_name: path.split(prefix, 1)[1].strip("/")}

    return "generic", "page", {"url": url}


def build_platform_record(url: str, *, platform: str | None = None, resource_type: str | None = None) -> dict[str, Any]:
    canonical_url = canonicalize_url(url)
    inferred_platform, inferred_resource_type, discovered_fields = infer_platform_task(canonical_url)
    resolved_platform = platform or inferred_platform
    resolved_resource_type = resource_type or inferred_resource_type
    record: dict[str, Any] = {
        "platform": resolved_platform,
        "resource_type": resolved_resource_type,
    }
    if resolved_platform == "generic":
        record["url"] = canonical_url
    else:
        record.update(discovered_fields)
    return record


def local_task_from_payload(payload: dict[str, Any]) -> TaskEnvelope:
    metadata = dict(payload)
    url = canonicalize_url(str(metadata.pop("url", "") or "").strip())
    if not url:
        raise ValueError("local task payload is missing url")
    task_id_value = metadata.pop("task_id", "")
    if not task_id_value:
        task_id_value = metadata.pop("id", "")
    task_id = str(task_id_value or "").strip()
    if not task_id:
        raise ValueError("local task payload is missing task_id")
    task_type_value = str(metadata.pop("task_type", "") or "local_file")
    dataset_id = optional_string(metadata.pop("dataset_id", None))
    platform_override = optional_string(metadata.pop("platform", None))
    resource_override = optional_string(metadata.pop("resource_type", None))
    inferred_platform, inferred_resource, _ = infer_platform_task(url)
    return TaskEnvelope(
        task_id=task_id,
        task_source="local_file",
        task_type=task_type_value,
        url=url,
        dataset_id=dataset_id,
        platform=platform_override or inferred_platform,
        resource_type=resource_override or inferred_resource,
        metadata=metadata,
    )


def task_to_work_item(task: TaskEnvelope) -> WorkItem:
    record = build_platform_record(task.url, platform=task.platform, resource_type=task.resource_type)
    for key, value in task.metadata.items():
        if key in {"dataset_id", "platform", "resource_type"} or value in (None, ""):
            continue
        record[key] = value
    claim_task_id = task.task_id if task.task_source == "backend_claim" else None
    claim_task_type = task.task_type if task.task_source == "backend_claim" else None
    return WorkItem(
        item_id=f"{task.task_type}:{task.task_id}",
        source=task.task_source,
        url=task.url,
        dataset_id=task.dataset_id,
        platform=task.platform,
        resource_type=task.resource_type,
        record=record,
        metadata=dict(task.metadata),
        claim_task_id=claim_task_id,
        claim_task_type=claim_task_type,
    )




def build_report_payload(item: WorkItem, record: dict[str, Any]) -> dict[str, Any]:
    """Build report payload for repeat-crawl and refresh tasks.

    Per API spec, the report body contains only `cleaned_data`.
    """
    cleaned_data = record.get("plain_text")
    if cleaned_data in (None, ""):
        cleaned_data = record.get("cleaned_data")
    if cleaned_data in (None, ""):
        cleaned_data = record.get("markdown")
    return {
        "cleaned_data": "" if cleaned_data is None else str(cleaned_data),
    }


class ResumeQueueSource:
    def __init__(self, state_store: WorkerStateStore) -> None:
        self.state_store = state_store

    def collect(self, *, limit: int) -> list[WorkItem]:
        backlog = self.state_store.pop_backlog(limit)
        auth_due = self.state_store.pop_due_auth_pending(limit)
        merged: dict[str, WorkItem] = {}
        for item in [*auth_due, *backlog]:
            merged[item.item_id] = item
        return list(merged.values())[:limit]


class BackendClaimSource:
    def __init__(self, client: Any) -> None:
        self.client = client
        self.last_errors: list[str] = []
        self.last_skips: list[str] = []

    def collect(self) -> list[WorkItem]:
        self.last_errors = []
        self.last_skips = []
        items: list[WorkItem] = []
        repeat_payload = self._safe_claim(self.client.claim_repeat_crawl_task, "repeat_crawl")
        if isinstance(repeat_payload, dict):
            item = self._safe_build_work_item("repeat_crawl", repeat_payload)
            if item is not None:
                items.append(item)
        refresh_payload = self._safe_claim(self.client.claim_refresh_task, "refresh")
        if isinstance(refresh_payload, dict):
            item = self._safe_build_work_item("refresh", refresh_payload)
            if item is not None:
                items.append(item)
        return items

    def _safe_claim(self, claim_fn: Any, task_type: str) -> dict[str, Any] | None:
        try:
            payload = claim_fn()
        except Exception as exc:
            self.last_errors.append(f"claim source failed: {task_type} claim request failed: {exc}")
            return None
        return payload if isinstance(payload, dict) else None

    def _safe_build_work_item(self, task_type: str, payload: dict[str, Any]) -> WorkItem | None:
        try:
            task = claimed_task_from_payload(task_type, payload, client=self.client)
            return task_to_work_item(task)
        except SkipClaimedTask as exc:
            task_id = optional_string(payload.get("id")) or "unknown"
            self.last_skips.append(f"claim skipped {task_type} task {task_id}: {exc}")
            return None
        except Exception as exc:
            task_id = optional_string(payload.get("id")) or "unknown"
            self.last_errors.append(f"claim source failed: {task_type} task {task_id} skipped: {exc}")
            return None


class WebSocketClaimSource:
    """Receives repeat_crawl_task messages via WebSocket push.

    The WS connection runs in a background thread, receiving tasks into
    an internal queue. `collect()` drains the queue non-blockingly.
    """

    def __init__(self, ws_client: Any) -> None:
        self.ws_client = ws_client
        self._queue: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self.last_errors: list[str] = []
        self.last_skips: list[str] = []

    def start(self) -> None:
        """Start the background WS receive thread."""
        if self._running:
            return
        self._running = True
        # Reset closed flag so reconnect_with_backoff works after a previous stop()
        self.ws_client.reopen()
        self._thread = threading.Thread(target=self._receive_loop, name="miner-ws", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        try:
            self.ws_client.close()
        except Exception:
            pass

    def _receive_loop(self) -> None:
        import logging
        log = logging.getLogger("miner.ws")
        first_connect = True
        while self._running:
            if not self.ws_client.connected:
                try:
                    if first_connect:
                        # First connection — connect immediately, no backoff
                        self.ws_client.connect()
                        first_connect = False
                    else:
                        self.ws_client.reconnect_with_backoff()
                except Exception as exc:
                    first_connect = False
                    log.warning("WS connect failed: %s", exc)
                    continue
                if not self.ws_client.connected:
                    continue
            try:
                msg = self.ws_client.receive(timeout=30.0)
            except WSDisconnected:
                continue
            if msg is None:
                continue
            if msg.type == "repeat_crawl_task":
                task_id = msg.repeat_crawl_task_id
                if task_id:
                    # ACK within 30s deadline
                    try:
                        self.ws_client.send_ack_repeat_crawl(task_id)
                    except WSDisconnected as exc:
                        # Connection lost — try best-effort reject, then let task expire on server
                        log.warning("ACK failed for %s (connection lost): %s — task will return to pool after 30s", task_id, exc)
                        continue
                    with self._lock:
                        self._queue.append(msg.data)
                    log.info("Received repeat_crawl_task via WS: %s", task_id)

    def collect(self) -> list[WorkItem]:
        """Drain the internal queue and convert to WorkItems."""
        self.last_errors.clear()
        self.last_skips.clear()
        with self._lock:
            payloads = list(self._queue)
            self._queue.clear()
        items: list[WorkItem] = []
        for payload in payloads:
            try:
                task = claimed_task_from_payload("repeat_crawl", payload)
                items.append(task_to_work_item(task))
            except SkipClaimedTask as exc:
                task_id = optional_string(payload.get("id")) or "unknown"
                self.last_skips.append(f"ws claim skipped repeat_crawl task {task_id}: {exc}")
            except Exception as exc:
                task_id = optional_string(payload.get("id")) or "unknown"
                self.last_errors.append(f"ws claim failed: repeat_crawl task {task_id}: {exc}")
        return items


class DatasetDiscoverySource:
    _DISCOVERY_HISTORY_TTL_SECONDS = 6 * 60 * 60
    _DIRECT_URLS_PER_DOMAIN = 12

    def __init__(self, client: Any, state_store: WorkerStateStore) -> None:
        self.client = client
        self.state_store = state_store

    def collect(self, *, min_interval_seconds: int) -> list[WorkItem]:
        items: list[WorkItem] = []
        datasets = self.client.list_datasets()
        now = int(time.time())

        # Smart rotation: prioritize datasets by gap to target and availability
        prioritized = self._prioritize_datasets(datasets, min_interval_seconds=min_interval_seconds)

        for dataset in prioritized:
            dataset_id = optional_string(dataset.get("dataset_id")) or optional_string(dataset.get("id"))
            if not dataset_id:
                continue
            recent_urls = self.state_store.recent_discovery_urls(
                dataset_id,
                within_seconds=self._DISCOVERY_HISTORY_TTL_SECONDS,
                now=now,
            )
            selected_urls: list[str] = []
            for domain in self._ordered_dataset_domains(dataset, dataset_id=dataset_id, now=now):
                host = domain.strip().lower()
                direct_urls = self._direct_discovery_urls(
                    domain,
                    dataset_id=dataset_id,
                    recent_urls=recent_urls,
                    now=now,
                )
                if direct_urls:
                    for url in direct_urls:
                        platform, resource_type, inferred_fields = infer_platform_task(url)
                        record = {"url": url, "platform": platform, "resource_type": resource_type}
                        record.update(inferred_fields)
                        items.append(
                            WorkItem(
                                item_id=f"discovery:{dataset_id}:{url}",
                                source="dataset_discovery",
                                url=url,
                                dataset_id=dataset_id,
                                platform=platform,
                                resource_type=resource_type,
                                record=record,
                                crawler_command="run",
                                metadata={"dataset": dataset, "source_domain": domain},
                            )
                        )
                    selected_urls.extend(direct_urls)
                    recent_urls.update(direct_urls)
                    if direct_urls:
                        continue

                for seed_url in _discovery_seed_urls(domain, dataset_id=dataset_id, recent_urls=recent_urls, now=now):
                    platform, resource_type, _ = infer_platform_task(seed_url)
                    items.append(
                        WorkItem(
                            item_id=f"discovery:{dataset_id}:{seed_url}",
                            source="dataset_discovery",
                            url=seed_url,
                            dataset_id=dataset_id,
                            platform=platform,
                            resource_type=resource_type,
                            record={
                                "url": seed_url,
                                "platform": platform,
                                "resource_type": resource_type,
                            },
                            crawler_command="discover-crawl",
                            metadata={"dataset": dataset, "source_domain": domain},
                        )
                    )
                    selected_urls.append(seed_url)
                    recent_urls.add(seed_url)
            if selected_urls:
                self.state_store.remember_discovery_urls(dataset_id, selected_urls, now=now)
            self.state_store.mark_dataset_scheduled(dataset_id)
        return items

    def _ordered_dataset_domains(self, dataset: dict[str, Any], *, dataset_id: str, now: int) -> list[str]:
        domains = _dataset_domains(dataset)
        if len(domains) <= 1:
            return domains
        rng = random.Random(_stable_seed("dataset-domains", dataset_id, bucket=now // 900))
        ordered = list(domains)
        rng.shuffle(ordered)
        return ordered

    def _direct_discovery_urls(
        self,
        domain: str,
        *,
        dataset_id: str,
        recent_urls: set[str],
        now: int,
    ) -> list[str]:
        raw = domain.strip()
        seed_url = raw if "://" in raw else f"https://{raw.strip('/')}/"
        parsed = urlparse(seed_url)
        host = (parsed.netloc or parsed.path).lower()
        normalized_host = "en.wikipedia.org" if host == "wikipedia.org" else host

        if normalized_host == "arxiv.org" or normalized_host.endswith(".arxiv.org"):
            candidates = _arxiv_recent_papers(
                count=self._DIRECT_URLS_PER_DOMAIN * 2,
                dataset_id=dataset_id,
                now=now,
            )
            return _prefer_unseen_urls(candidates, recent_urls, limit=self._DIRECT_URLS_PER_DOMAIN)

        if normalized_host == "en.wikipedia.org" or normalized_host.endswith(".wikipedia.org"):
            candidates = _wikipedia_random_articles(normalized_host, count=self._DIRECT_URLS_PER_DOMAIN * 2)
            return _prefer_unseen_urls(candidates, recent_urls, limit=self._DIRECT_URLS_PER_DOMAIN)

        return []

    def _prioritize_datasets(
        self,
        datasets: list[dict[str, Any]],
        *,
        min_interval_seconds: int,
    ) -> list[dict[str, Any]]:
        """Sort datasets by priority: largest gap to target first, then by staleness.

        Priority factors:
        1. Not in cooldown (rate limited datasets go last)
        2. Gap to target (datasets further from target get priority)
        3. Time since last scheduled (stale datasets get priority)
        """
        import time

        now = int(time.time())
        cooldowns = self.state_store.active_dataset_cooldowns(now=now)

        scored: list[tuple[float, dict[str, Any]]] = []
        for dataset in datasets:
            dataset_id = optional_string(dataset.get("dataset_id")) or optional_string(dataset.get("id"))
            if not dataset_id:
                continue

            # Skip if not due for scheduling
            if not self.state_store.should_schedule_dataset(dataset_id, min_interval_seconds=min_interval_seconds):
                continue

            # Calculate priority score (higher = more priority)
            score = 0.0

            # Skip datasets in cooldown entirely
            if dataset_id in cooldowns:
                continue

            # Factor 2: Gap to target (from dataset metadata if available)
            epoch_submitted = int(dataset.get("epoch_submitted") or dataset.get("submitted") or 0)
            epoch_target = int(dataset.get("epoch_target") or dataset.get("target") or 80)
            gap = max(0, epoch_target - epoch_submitted)
            score += gap * 10  # Larger gap = higher priority

            # Factor 3: Completion percentage (less complete = higher priority)
            if epoch_target > 0:
                completion_ratio = epoch_submitted / epoch_target
                score += (1 - completion_ratio) * 100  # 0% complete = +100, 100% complete = 0

            # Factor 4: Time since last scheduled (staleness bonus)
            # Datasets that haven't been touched recently get a small boost
            # This is already handled by should_schedule_dataset, but we add a tiebreaker

            scored.append((score, dataset))

        # Sort by score descending (highest priority first)
        scored.sort(key=lambda x: x[0], reverse=True)

        return [dataset for _score, dataset in scored]


def _is_content_url(url: str) -> bool:
    """Filter out obvious navigation/non-content pages that will fail dedup checks."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = parsed.path.lower().rstrip("/")

    # Amazon: only product pages (/dp/ASIN or /gp/product/ASIN) are valid content
    if host.endswith(".amazon.com") or host == "amazon.com" or host.endswith(".amazon.co.uk") or host == "amazon.co.uk" or host.endswith(".amazon.de") or host == "amazon.de":
        if re.search(r"/(?:dp|gp/product)/[A-Z0-9]{10}", parsed.path, re.IGNORECASE):
            return True
        return False

    # Wikipedia: only article pages (/wiki/ArticleName), not special pages
    if host == "wikipedia.org" or host.endswith(".wikipedia.org"):
        if path.startswith("/wiki/") and ":" not in path.split("/wiki/", 1)[-1]:
            return True
        return False

    # arXiv: only paper detail pages; listing pages are discovery seeds only
    if host == "arxiv.org" or host.endswith(".arxiv.org"):
        return path.startswith("/abs/") or path.startswith("/pdf/")

    # Default: allow
    return True


def build_follow_up_items_from_discovery(
    parent: WorkItem,
    records: list[dict[str, Any]],
    *,
    state_store: WorkerStateStore | None = None,
    history_ttl_seconds: int = 6 * 60 * 60,
) -> list[WorkItem]:
    items: list[WorkItem] = []
    recent_urls: set[str] = set()
    if state_store is not None and parent.dataset_id:
        recent_urls = state_store.recent_discovery_urls(
            parent.dataset_id,
            within_seconds=history_ttl_seconds,
        )
    selected_urls: list[str] = []
    for record in records:
        canonical_url = optional_string(record.get("canonical_url"))
        if not canonical_url:
            continue
        canonical_url = canonicalize_url(canonical_url)
        if not _is_content_url(canonical_url):
            continue
        if canonical_url in recent_urls:
            continue
        platform = optional_string(record.get("platform")) or infer_platform_task(canonical_url)[0]
        resource_type = optional_string(record.get("resource_type")) or infer_platform_task(canonical_url)[1]
        items.append(
            WorkItem(
                item_id=f"followup:{parent.dataset_id or 'unknown'}:{canonical_url}",
                source="discovery_followup",
                url=canonical_url,
                dataset_id=parent.dataset_id,
                platform=platform,
                resource_type=resource_type,
                record=build_platform_record(canonical_url, platform=platform, resource_type=resource_type),
                crawler_command="run",
                metadata={
                    "discovered_from": parent.item_id,
                    "execution_mode": "agent_handoff",
                    "origin": "discovery_followup",
                    "origin_item_id": parent.item_id,
                },
            )
        )
        selected_urls.append(canonical_url)
        recent_urls.add(canonical_url)
    if state_store is not None and parent.dataset_id and selected_urls:
        state_store.remember_discovery_urls(parent.dataset_id, selected_urls)
    return items


def _dataset_domains(dataset: dict[str, Any]) -> list[str]:
    domains = dataset.get("source_domains")
    if isinstance(domains, list):
        return [str(item).strip() for item in domains if str(item).strip()]
    if isinstance(domains, str):
        return [chunk.strip() for chunk in domains.split(",") if chunk.strip()]
    return []


def _arxiv_recent_papers(count: int = 10, *, dataset_id: str = "", now: int | None = None) -> list[str]:
    """Fetch diversified /abs/ URLs via the arXiv API."""
    import urllib.request
    import re as _re

    categories = ["cs", "math", "physics", "q-fin", "stat", "econ", "q-bio", "eess"]
    current = int(time.time()) if now is None else now
    bucket = current // 900
    rng = random.Random(_stable_seed("arxiv", dataset_id or "global", bucket=bucket))
    selected_categories = categories[:]
    rng.shuffle(selected_categories)
    selected_categories = selected_categories[: min(4, len(selected_categories))]
    plans: list[tuple[str, int, int, str]] = []
    for category in selected_categories:
        start = rng.randint(0, 180)
        max_results = max(6, min(24, count))
        sort_by = rng.choice(["submittedDate", "lastUpdatedDate"])
        plans.append((category, start, max_results, sort_by))
    urls: list[str] = []
    seen: set[str] = set()
    for category, start, max_results, sort_by in plans:
        api_url = (
            "http://export.arxiv.org/api/query"
            f"?search_query=cat:{category}.*&sortBy={sort_by}&sortOrder=descending"
            f"&start={start}&max_results={max_results}"
        )
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "mine-agent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode()
        except Exception:
            continue
        for match in _re.finditer(r"<id>\s*https?://arxiv\.org/abs/([^<\s]+)\s*</id>", text):
            arxiv_id = _re.sub(r"v\d+$", "", match.group(1).strip())
            url = canonicalize_url(f"https://arxiv.org/abs/{arxiv_id}")
            if url not in seen:
                seen.add(url)
                urls.append(url)
            if len(urls) >= count:
                return urls[:count]
    return urls[:count]


def _wikipedia_random_articles(wiki_host: str, count: int = 10) -> list[str]:
    """Fetch random article URLs from MediaWiki API.

    Uses the MediaWiki list=random API to get article titles, then constructs
    full URLs. Much faster and more reliable than discover-crawl on Main_Page.
    """
    import urllib.request
    import urllib.error

    api_url = (
        f"https://{wiki_host}/w/api.php"
        f"?action=query&list=random&rnnamespace=0&rnlimit={count}&format=json"
    )
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "mine-agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            import json
            data = json.loads(resp.read())
        pages = data.get("query", {}).get("random", [])
        urls = []
        for page in pages:
            title = page.get("title", "")
            if title:
                encoded = title.replace(" ", "_")
                urls.append(canonicalize_url(f"https://{wiki_host}/wiki/{encoded}"))
        return urls
    except Exception:
        return []


def _discovery_seed_urls(
    domain: str,
    *,
    dataset_id: str = "",
    recent_urls: set[str] | None = None,
    now: int | None = None,
) -> list[str]:
    raw = domain.strip()
    seed_url = raw if "://" in raw else f"https://{raw.strip('/')}/"
    parsed = urlparse(seed_url)
    host = (parsed.netloc or parsed.path).lower()
    normalized_path = parsed.path.rstrip("/")
    current = int(time.time()) if now is None else now
    bucket = current // 900
    if (host == "wikipedia.org" or host.endswith(".wikipedia.org")) and normalized_path in {"", "/"}:
        if host == "wikipedia.org":
            host = "en.wikipedia.org"
        return _prefer_unseen_urls(
            [
                canonicalize_url(f"{parsed.scheme or 'https'}://{host}/wiki/Portal:Current_events"),
                canonicalize_url(f"{parsed.scheme or 'https'}://{host}/wiki/Special:Random"),
                canonicalize_url(f"{parsed.scheme or 'https'}://{host}/wiki/Main_Page"),
            ],
            recent_urls or set(),
            limit=2,
        )
    # Amazon: redirect homepage to bestsellers page which links to actual products
    if (host.endswith(".amazon.com") or host == "amazon.com" or host.endswith(".amazon.co.uk") or host == "amazon.co.uk" or host.endswith(".amazon.de") or host == "amazon.de") and normalized_path in {"", "/"}:
        seeds = [
            canonicalize_url(f"{parsed.scheme or 'https'}://{host}/gp/bestsellers/"),
            canonicalize_url(f"{parsed.scheme or 'https'}://{host}/gp/new-releases/"),
            canonicalize_url(f"{parsed.scheme or 'https'}://{host}/gp/movers-and-shakers/"),
            canonicalize_url(f"{parsed.scheme or 'https'}://{host}/gp/most-wished-for/"),
            canonicalize_url(f"{parsed.scheme or 'https'}://{host}/gp/giftfinder/"),
        ]
        return _shuffled_unseen_urls(seeds, recent_urls or set(), limit=3, label=f"amazon:{dataset_id}:{host}", bucket=bucket)
    # arXiv: seed from recent archive listings so one-hop discovery reaches /abs/<id> pages
    if (host == "arxiv.org" or host.endswith(".arxiv.org")) and normalized_path in {"", "/"}:
        scheme = parsed.scheme or "https"
        seeds = [
            canonicalize_url(f"{scheme}://{host}/list/cs/recent"),
            canonicalize_url(f"{scheme}://{host}/list/math/recent"),
            canonicalize_url(f"{scheme}://{host}/list/physics/recent"),
            canonicalize_url(f"{scheme}://{host}/list/q-bio/recent"),
            canonicalize_url(f"{scheme}://{host}/list/q-fin/recent"),
            canonicalize_url(f"{scheme}://{host}/list/stat/recent"),
            canonicalize_url(f"{scheme}://{host}/list/eess/recent"),
            canonicalize_url(f"{scheme}://{host}/list/econ/recent"),
        ]
        return _shuffled_unseen_urls(seeds, recent_urls or set(), limit=3, label=f"arxiv-seeds:{dataset_id}:{host}", bucket=bucket)
    if (host == "www.linkedin.com" or host == "linkedin.com") and normalized_path in {"", "/"}:
        scheme = parsed.scheme or "https"
        seeds = [
            canonicalize_url(f"{scheme}://www.linkedin.com/jobs/"),
            canonicalize_url(f"{scheme}://www.linkedin.com/company/"),
            canonicalize_url(f"{scheme}://www.linkedin.com/feed/"),
            canonicalize_url(f"{scheme}://www.linkedin.com/news/"),
        ]
        return _shuffled_unseen_urls(seeds, recent_urls or set(), limit=2, label=f"linkedin:{dataset_id}", bucket=bucket)
    if (host.endswith("basescan.org") or host.endswith("base.org")) and normalized_path in {"", "/"}:
        scheme = parsed.scheme or "https"
        seeds = [
            canonicalize_url(f"{scheme}://{host}/txs"),
            canonicalize_url(f"{scheme}://{host}/accounts"),
            canonicalize_url(f"{scheme}://{host}/tokens"),
            canonicalize_url(f"{scheme}://{host}/contractsVerified"),
        ]
        return _shuffled_unseen_urls(seeds, recent_urls or set(), limit=2, label=f"base:{dataset_id}:{host}", bucket=bucket)
    return _prefer_unseen_urls([canonicalize_url(seed_url)], recent_urls or set(), limit=1)


def _prefer_unseen_urls(urls: list[str], recent_urls: set[str], *, limit: int) -> list[str]:
    unique = _dedupe_preserve_order([canonicalize_url(url) for url in urls if canonicalize_url(url)])
    unseen = [url for url in unique if url not in recent_urls]
    chosen = unseen[:limit]
    if chosen:
        return chosen
    return unique[:limit]


def _shuffled_unseen_urls(urls: list[str], recent_urls: set[str], *, limit: int, label: str, bucket: int) -> list[str]:
    ordered = _dedupe_preserve_order(urls)
    rng = random.Random(_stable_seed(label, bucket=bucket))
    rng.shuffle(ordered)
    return _prefer_unseen_urls(ordered, recent_urls, limit=limit)


def _dedupe_preserve_order(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def _stable_seed(*parts: str, bucket: int) -> int:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(f"{payload}|{bucket}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)
