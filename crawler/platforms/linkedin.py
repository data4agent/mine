from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from uuid import uuid4

from bs4 import BeautifulSoup, Tag
import httpx

from crawler.fetch.api_backend import fetch_api_get

from .base import (
    PlatformAdapter,
    PlatformDiscoveryPlan,
    PlatformEnrichmentPlan,
    PlatformErrorPlan,
    PlatformExtractPlan,
    PlatformFetchPlan,
    PlatformNormalizePlan,
    default_fetch_executor,
    strategy_extractor,
)

FETCH_PLAN = PlatformFetchPlan(default_backend="api", fallback_backends=("playwright", "camoufox"), requires_auth=True)
EXTRACT_PLAN = PlatformExtractPlan(strategy="document")
NORMALIZE_PLAN = PlatformNormalizePlan(hook_name="linkedin")
ENRICH_PLAN = PlatformEnrichmentPlan(
    route="social_graph",
    field_groups=(
        "linkedin_profiles_identity",
        "linkedin_profiles_summary",
        "linkedin_profiles_career",
    ),
)

PROFILE_FIELD_GROUPS = (
    "linkedin_profiles_identity",
    "linkedin_profiles_summary",
    "linkedin_profiles_career",
)

COMPANY_FIELD_GROUPS = (
    "linkedin_company_basic",
    "linkedin_company_org_intel",
    "linkedin_company_talent_signals",
)

JOB_FIELD_GROUPS = (
    "linkedin_jobs_basic",
    "linkedin_jobs_requirements",
    "linkedin_jobs_candidate_view",
)

POST_FIELD_GROUPS = (
    "linkedin_posts_basic",
    "linkedin_posts_entities",
    "linkedin_posts_summary",
)

QUERY_IDS = {
    "profile_by_vanity": "voyagerIdentityDashProfiles.34ead06db82a2cc9a778fac97f69ad6a",
    "job_posting": "voyagerJobsDashJobPostings.891aed7916d7453a37e4bbf5f1f60de4",
}

SEARCH_TYPE_PATHS = {
    "company": "companies",
    "companies": "companies",
    "profile": "people",
    "people": "people",
    "job": "jobs",
    "jobs": "jobs",
    "post": "content",
    "content": "content",
}

DECORATION_IDS = {
    "company_main": "com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-12",
}


def _load_cookie_map(storage_state_path: str | None) -> dict[str, str]:
    if storage_state_path is None:
        return {}
    payload = json.loads(open(storage_state_path, "r", encoding="utf-8").read())
    cookies = payload.get("cookies", []) if isinstance(payload, dict) else []
    return {item.get("name"): item.get("value") for item in cookies if isinstance(item, dict)}


def _storage_state_headers(
    storage_state_path: str | None,
    record: dict[str, Any] | None = None,
    discovered: dict[str, Any] | None = None,
    *,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    cookie_map = _load_cookie_map(storage_state_path)
    jsessionid = (cookie_map.get("JSESSIONID") or "").strip('"')
    if jsessionid.startswith("ajax:"):
        csrf_token = jsessionid
    elif jsessionid:
        csrf_token = f"ajax:{jsessionid}"
    else:
        csrf_token = ""
    lang = (cookie_map.get("lang") or "").lower()
    x_li_lang = "zh_CN" if "zh-cn" in lang else "en_US"
    headers = {
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "x-restli-protocol-version": "2.0.0",
        "x-li-lang": x_li_lang,
        "referer": (discovered or {}).get("canonical_url") or "https://www.linkedin.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "x-li-track": json.dumps(
            {
                "clientVersion": "1.13.*",
                "osName": "web",
                "timezoneOffset": 8,
                "deviceFormFactor": "DESKTOP",
                "mpName": "voyager-web",
                "displayDensity": 1,
                "displayWidth": 1920,
                "displayHeight": 1080,
            },
            separators=(",", ":"),
        ),
        "x-li-page-instance": f"urn:li:page:d_flagship3_profile_view_base;{uuid4()}",
    }
    if cookie_map:
        headers["Cookie"] = "; ".join(f"{key}={value}" for key, value in cookie_map.items())
    if csrf_token:
        headers["csrf-token"] = csrf_token
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _fetch_linkedin_json(
    *,
    canonical_url: str,
    endpoint: str,
    storage_state_path: str | None,
    discovered: dict[str, Any],
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    return fetch_api_get(
        canonical_url=canonical_url,
        api_endpoint=endpoint,
        headers=_storage_state_headers(storage_state_path, None, discovered, extra_headers=extra_headers),
    )


def _fetch_linkedin_html(
    *,
    canonical_url: str,
    storage_state_path: str | None,
    discovered: dict[str, Any],
) -> dict[str, Any]:
    return fetch_api_get(
        canonical_url=canonical_url,
        api_endpoint=canonical_url,
        headers=_storage_state_headers(
            storage_state_path,
            None,
            discovered,
            extra_headers={"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        ),
    )


def _build_profile_lookup_endpoint(public_identifier: str) -> str:
    return (
        "https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true"
        f"&variables=(vanityName:{quote(public_identifier)})"
        f"&queryId={QUERY_IDS['profile_by_vanity']}"
    )


def _build_company_lookup_endpoint(company_slug: str) -> str:
    return (
        "https://www.linkedin.com/voyager/api/organization/companies"
        f"?decorationId={quote(DECORATION_IDS['company_main'])}"
        "&q=universalName"
        f"&universalName={quote(company_slug)}"
    )


def _build_linkedin_endpoint(record: dict) -> str:
    if record["resource_type"] == "search":
        search_path = SEARCH_TYPE_PATHS.get(str(record.get("search_type", "company")).lower(), "companies")
        return f"https://www.linkedin.com/search/results/{search_path}/?keywords={quote(str(record.get('query', '')))}"
    if record["resource_type"] == "job":
        urn = quote(f"urn:li:fsd_jobPosting:{record['job_id']}")
        return (
            "https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true"
            f"&variables=(jobPostingUrn:{urn})"
            f"&queryId={QUERY_IDS['job_posting']}"
        )
    raise ValueError(f"linkedin api fetch not supported for {record['resource_type']}")


def _enrich_linkedin_record_from_url(record: dict[str, Any], canonical_url: str) -> dict[str, Any]:
    enriched = dict(record)
    patterns = (
        (r"^https://www\.linkedin\.com/in/([^/]+)/?$", "profile", "public_identifier"),
        (r"^https://www\.linkedin\.com/company/([^/]+)/?$", "company", "company_slug"),
        (r"^https://www\.linkedin\.com/jobs/view/(\d+)/?$", "job", "job_id"),
        (r"^https://www\.linkedin\.com/feed/update/([^/]+)/?$", "post", "activity_urn"),
    )
    for pattern, resource_type, key in patterns:
        if enriched.get("resource_type") != resource_type:
            continue
        if enriched.get(key):
            return enriched
        match = re.match(pattern, canonical_url)
        if match:
            enriched[key] = match.group(1)
            return enriched
    return enriched


def _fetch_linkedin_api(record: dict, discovered: dict, storage_state_path: str | None) -> dict:
    canonical_url = discovered["canonical_url"]
    record = _enrich_linkedin_record_from_url(record, canonical_url)
    resource_type = record["resource_type"]
    if resource_type == "search":
        return fetch_api_get(
            canonical_url=canonical_url,
            api_endpoint=canonical_url,
            headers=_storage_state_headers(
                storage_state_path,
                record,
                discovered,
                extra_headers={"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            ),
        )
    if resource_type == "post":
        return _fetch_linkedin_html(
            canonical_url=canonical_url,
            storage_state_path=storage_state_path,
            discovered=discovered,
        )
    if resource_type == "profile":
        try:
            return _fetch_linkedin_json(
                canonical_url=canonical_url,
                endpoint=_build_profile_lookup_endpoint(record["public_identifier"]),
                storage_state_path=storage_state_path,
                discovered=discovered,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 451:
                raise
            html_response = _fetch_linkedin_html(
                canonical_url=canonical_url,
                storage_state_path=storage_state_path,
                discovered=discovered,
            )
            html_response["html_fallback_text"] = html_response.get("text")
            html_response["html_fallback_content_type"] = html_response.get("content_type")
            return html_response
    if resource_type == "company":
        try:
            return _fetch_linkedin_json(
                canonical_url=canonical_url,
                endpoint=_build_company_lookup_endpoint(record["company_slug"]),
                storage_state_path=storage_state_path,
                discovered=discovered,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 451:
                raise
            html_response = _fetch_linkedin_html(
                canonical_url=canonical_url,
                storage_state_path=storage_state_path,
                discovered=discovered,
            )
            html_response["html_fallback_text"] = html_response.get("text")
            html_response["html_fallback_content_type"] = html_response.get("content_type")
            return html_response
    response = _fetch_linkedin_json(
        canonical_url=canonical_url,
        endpoint=_build_linkedin_endpoint(record),
        storage_state_path=storage_state_path,
        discovered=discovered,
    )
    if resource_type == "job" and _linkedin_job_payload_missing(response.get("json_data") or {}):
        html_response = _fetch_linkedin_html(
            canonical_url=canonical_url,
            storage_state_path=storage_state_path,
            discovered=discovered,
        )
        response["html_fallback_text"] = html_response.get("text")
        response["html_fallback_content_type"] = html_response.get("content_type")
    return response


def _resolve_linkedin_backend(record: dict, override_backend: str | None = None, retry_count: int = 0) -> str:
    if override_backend:
        return override_backend
    if record["resource_type"] == "search":
        if retry_count > 0 and FETCH_PLAN.fallback_backends:
            return FETCH_PLAN.fallback_backends[min(retry_count - 1, len(FETCH_PLAN.fallback_backends) - 1)]
        return "api"
    if record["resource_type"] == "post":
        if retry_count > 0 and FETCH_PLAN.fallback_backends:
            return FETCH_PLAN.fallback_backends[min(retry_count - 1, len(FETCH_PLAN.fallback_backends) - 1)]
        return "api"
    if retry_count > 0 and FETCH_PLAN.fallback_backends:
        return FETCH_PLAN.fallback_backends[min(retry_count - 1, len(FETCH_PLAN.fallback_backends) - 1)]
    return FETCH_PLAN.default_backend


def _extract_linkedin(record: dict, fetched: dict) -> dict:
    if record["resource_type"] == "search":
        return _extract_linkedin_search(record, fetched)
    if record["resource_type"] == "post":
        return _extract_linkedin_post(record, fetched)
    data = fetched.get("json_data") or {}
    html_fallback_text = str(fetched.get("html_fallback_text") or "")
    if record["resource_type"] == "job" and _linkedin_job_payload_missing(data):
        extracted = _extract_linkedin_job_from_html(record, html_fallback_text) if html_fallback_text else _extract_linkedin_structured(record, data)
    elif record["resource_type"] == "company" and html_fallback_text:
        extracted = _extract_linkedin_company_from_html(record, html_fallback_text)
    elif record["resource_type"] == "profile" and html_fallback_text:
        extracted = _extract_linkedin_profile_from_html(record, html_fallback_text)
    else:
        extracted = _extract_linkedin_structured(record, data)
    metadata = {
        "title": extracted.get("title") or record.get("public_identifier") or record.get("company_slug") or record.get("job_id"),
        "content_type": fetched.get("content_type"),
        "source_url": fetched["url"],
    }
    metadata.update({k: v for k, v in extracted.get("metadata_extra", {}).items() if v not in (None, "", [], {})})

    plain_text = extracted.get("plain_text") or json.dumps(data, ensure_ascii=False, default=str)
    markdown = extracted.get("markdown") or f"# {metadata['title']}\n\n{plain_text}".strip()
    structured = {
        "voyager": data,
        "linkedin": extracted.get("structured", {}),
    }
    return {
        "metadata": metadata,
        "plain_text": plain_text,
        "markdown": markdown,
        "document_blocks": [],
        "structured": structured,
        "extractor": "linkedin_api",
    }


def _extract_linkedin_structured(record: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    if record["resource_type"] == "company":
        return _extract_linkedin_company(data)
    if record["resource_type"] == "profile":
        return _extract_linkedin_profile(data)
    if record["resource_type"] == "job":
        return _extract_linkedin_job(data)
    plain_text = json.dumps(data, ensure_ascii=False, default=str)
    return {"title": record.get("activity_urn"), "plain_text": plain_text, "markdown": f"```json\n{plain_text}\n```", "structured": {}}


def _extract_linkedin_post(record: dict[str, Any], fetched: dict[str, Any]) -> dict[str, Any]:
    html = fetched.get("text") or fetched.get("html") or fetched.get("content_bytes", b"").decode("utf-8", "ignore")
    html_context = _extract_post_update_context(html)
    actor_block = _extract_post_actor_block(html)
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one('[data-sdui-screen="com.linkedin.sdui.flagshipnav.feed.UpdateDetail"]') or soup.body or soup
    text = container.get_text("\n", strip=True)
    lines = _clean_linkedin_lines(text.splitlines())
    author_name = _extract_post_author_name_from_html(actor_block) or _extract_post_author_name_from_html(html_context) or _extract_post_author_name_from_html(html) or _extract_post_author_name(lines)
    author_headline = _extract_post_author_headline_from_html(actor_block, author_name) or _extract_post_author_headline_from_html(html_context, author_name) or _extract_post_author_headline_from_html(html, author_name) or _extract_post_author_headline(lines, author_name)
    body = _extract_post_body(lines, author_name, author_headline)
    rsc_body = _extract_post_body_from_rsc_html(html)
    if rsc_body and len(rsc_body) > len(body):
        body = rsc_body
    author_profile_url = _extract_post_author_profile_url_from_html(actor_block, author_name) or _extract_post_author_profile_url_from_html(html_context, author_name) or _extract_post_author_profile_url_from_html(html, author_name) or _extract_post_author_profile_url(container)
    image_urls = _extract_post_media_urls(container, media_kind="image")
    video_urls = _extract_post_media_urls(container, media_kind="video")
    structured = {
        "activity_urn": record.get("activity_urn"),
        "author_name": author_name,
        "author_headline": author_headline,
        "author_profile_url": author_profile_url,
        "author_id": _linkedin_identifier_from_url(author_profile_url),
        "body": body,
        "hashtags": _extract_post_hashtags(body),
        "image_urls": image_urls,
        "video_urls": video_urls,
        "date_posted": _extract_post_date(container),
        "reaction_count": _extract_post_state_count(html, "reactionCount", record.get("activity_urn")) or _extract_post_reaction_total(html, record.get("activity_urn")) or _extract_post_count(text, r"([\d,]+)\s*(?:次回应|reactions?)"),
        "comment_count": _extract_post_state_count(html, "commentCount", record.get("activity_urn")) or _extract_post_count(text, r"([\d,]+)\s*(?:条评论|comments?)"),
        "repost_count": _extract_post_state_count(html, "repostCount", record.get("activity_urn")) or _extract_post_count(text, r"([\d,]+)\s*(?:次转发|reposts?)"),
    }
    title = author_name or record.get("activity_urn")
    plain_text = body or "\n".join(lines[:20]).strip()
    markdown_parts = [f"# {title}"]
    if author_headline:
        markdown_parts.append(author_headline)
    if body:
        markdown_parts.append(body)
    markdown = "\n\n".join(part for part in markdown_parts if part).strip()
    return {
        "metadata": {
            "title": title,
            "content_type": fetched.get("content_type"),
            "source_url": fetched.get("url"),
            "entity_type": "post",
        },
        "plain_text": plain_text,
        "markdown": markdown,
        "document_blocks": [],
        "structured": {
            "linkedin": {key: value for key, value in structured.items() if value not in (None, "", [], {})},
        },
        "extractor": "linkedin_post_html",
    }


def _extract_linkedin_search(record: dict[str, Any], fetched: dict[str, Any]) -> dict[str, Any]:
    html = fetched.get("text") or fetched.get("html") or fetched.get("content_bytes", b"").decode("utf-8", "ignore")
    soup = BeautifulSoup(html, "html.parser")
    search_type = str(record.get("search_type", "company")).lower()
    results = _extract_linkedin_search_results(soup, search_type)
    display_type = SEARCH_TYPE_PATHS.get(search_type, search_type)
    title = f"LinkedIn search: {record.get('query', '')} ({display_type})".strip()

    if results:
        plain_lines = [
            f"{item['title']} | {item['entity_type']} | {item.get('subtitle', '')}".rstrip(" |")
            for item in results
        ]
        markdown_lines = [
            f"- [{item['title']}]({item['canonical_url']}) - {item['entity_type']}"
            + (f" - {item['subtitle']}" if item.get("subtitle") else "")
            for item in results
        ]
    else:
        plain_lines = [f"No LinkedIn search results for {record.get('query', '')}"]
        markdown_lines = [plain_lines[0]]

    return {
        "metadata": {
            "title": title,
            "content_type": fetched.get("content_type"),
            "source_url": fetched.get("url"),
            "entity_type": "search",
            "query": record.get("query"),
            "search_type": display_type,
            "result_count": len(results),
        },
        "plain_text": "\n".join(plain_lines),
        "markdown": "# " + title + "\n\n" + "\n".join(markdown_lines),
        "document_blocks": [],
        "structured": {
            "linkedin": {
                "query": record.get("query"),
                "search_type": display_type,
                "results": results,
                "result_count": len(results),
            }
        },
        "extractor": "linkedin_search_html",
    }


def _extract_linkedin_search_results(soup: BeautifulSoup, search_type: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        candidate = _search_candidate_from_anchor(anchor, search_type)
        if candidate is None:
            continue
        canonical_url = candidate["canonical_url"]
        if canonical_url in seen:
            continue
        seen.add(canonical_url)
        results.append(candidate)
        if len(results) >= 10:
            break

    return results


def _search_candidate_from_anchor(anchor: Tag, search_type: str) -> dict[str, Any] | None:
    href = str(anchor.get("href", "")).strip()
    if not href:
        return None

    normalized_href = _normalize_linkedin_href(href)
    if normalized_href is None:
        return None

    candidate = _candidate_from_href(normalized_href, search_type)
    if candidate is None:
        return None

    title = " ".join(anchor.stripped_strings).strip()
    if not title:
        return None

    subtitle = _candidate_subtitle(anchor, title)
    candidate["title"] = title
    candidate["subtitle"] = subtitle
    candidate["search_type"] = SEARCH_TYPE_PATHS.get(search_type, search_type)
    candidate["discovery_input"] = {
        "platform": "linkedin",
        "resource_type": candidate["resource_type"],
        candidate["identifier_field"]: candidate["identifier"],
    }
    return candidate


def _normalize_linkedin_href(href: str) -> str | None:
    if href.startswith("/"):
        href = urljoin("https://www.linkedin.com", href)
    if not href.startswith("https://www.linkedin.com/"):
        return None
    parts = urlsplit(href)
    normalized_path = parts.path.rstrip("/")
    if normalized_path:
        normalized_path += "/"
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, "", ""))


def _candidate_from_href(href: str, search_type: str) -> dict[str, Any] | None:
    patterns = {
        "company": (r"https://www\.linkedin\.com/company/([^/]+)/?$", "company", "company", "company_slug"),
        "profile": (r"https://www\.linkedin\.com/in/([^/]+)/?$", "person", "profile", "public_identifier"),
        "job": (r"https://www\.linkedin\.com/jobs/view/(\d+)/?$", "job", "job", "job_id"),
        "post": (r"https://www\.linkedin\.com/feed/update/([^/]+)/?$", "post", "post", "activity_urn"),
    }
    requested = search_type.lower()
    accepted_types = [requested] if requested in patterns else ["company", "profile", "job", "post"]
    for candidate_type in accepted_types:
        pattern, entity_type, resource_type, identifier_field = patterns[candidate_type]
        match = re.match(pattern, href)
        if not match:
            continue
        return {
            "entity_type": entity_type,
            "resource_type": resource_type,
            "canonical_url": href,
            "identifier": match.group(1),
            "identifier_field": identifier_field,
        }
    return None


def _candidate_subtitle(anchor: Tag, title: str) -> str:
    container = anchor
    for _ in range(4):
        if container.parent is None or not isinstance(container.parent, Tag):
            break
        container = container.parent
    text = container.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line != title:
            return line
    return ""


def _linkedin_identifier_from_url(url: str | None) -> str | None:
    normalized = _normalize_linkedin_href(str(url or "").strip())
    if not normalized:
        return None
    if "/in/" in normalized or "/company/" in normalized:
        return normalized.rstrip("/").split("/")[-1]
    if "/feed/update/" in normalized or "/jobs/view/" in normalized:
        return _linkedin_id(normalized.rstrip("/").split("/")[-1])
    return None


def _clean_linkedin_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen_recent: set[str] = set()
    for raw in lines:
        line = " ".join(raw.split()).strip()
        if not line:
            continue
        if line in seen_recent:
            continue
        cleaned.append(line)
        seen_recent = set(cleaned[-8:])
    return cleaned


def _extract_post_author_name(lines: list[str]) -> str | None:
    skip_exact = {
        "信息流动态",
        "Feed post number",
        "关注",
        "Follow",
        "显示译文",
        "See translation",
        "赞",
        "Like",
        "评论",
        "Comment",
        "转发",
        "Repost",
        "发送",
        "Send",
    }
    for line in lines:
        if line in skip_exact:
            continue
        if re.search(r"(?:次回应|条评论|次转发|reactions?|comments?|reposts?)", line, re.IGNORECASE):
            continue
        if re.search(r"^\d+\s*(?:年|mo|h|d|w)\b", line, re.IGNORECASE):
            continue
        if re.search(r"\b\d+\s*度\+?$", line):
            continue
        if line.startswith("reactionState-"):
            continue
        return line
    return None


def _extract_post_author_headline(lines: list[str], author_name: str | None) -> str | None:
    if not author_name:
        return None
    try:
        start = lines.index(author_name) + 1
    except ValueError:
        return None
    for line in lines[start:]:
        if re.search(r"^\d+\s*(?:年|mo|h|d|w)\b", line, re.IGNORECASE):
            return None
        if line in {"关注", "Follow"}:
            return None
        if len(line) >= 6:
            return line
    return None


def _extract_post_body(lines: list[str], author_name: str | None, author_headline: str | None) -> str:
    ignore = {value for value in (author_name, author_headline) if value}
    body_lines: list[str] = []
    in_body = False
    for line in lines:
        if line in ignore:
            continue
        if not in_body:
            if re.search(r"^\d+\s*(?:年|mo|h|d|w)\b", line, re.IGNORECASE):
                in_body = True
            continue
        if line in {"关注", "Follow", "显示译文", "See translation", "赞", "Like", "评论", "Comment", "转发", "Repost", "发送", "Send"}:
            continue
        if re.search(r"(?:次回应|条评论|次转发|reactions?|comments?|reposts?)", line, re.IGNORECASE):
            break
        if line.startswith("reactionState-"):
            break
        body_lines.append(line)
    return "\n".join(body_lines).strip()


def _extract_post_body_from_rsc_html(html: str) -> str | None:
    normalized = html.replace('\\"', '"')
    candidates: list[str] = []
    start = 0
    while True:
        idx = normalized.find("translation_translatable-commentary-", start)
        if idx < 0:
            break
        window = normalized[max(0, idx - 5000): idx + 5000]
        if "contentUrnCommentUrn=null" not in window:
            start = idx + 1
            continue
        for match in re.finditer(r'children":\["((?:[^"\\]|\\.){20,5000}?)"\]', window, re.DOTALL):
            candidate = unescape(match.group(1)).replace("\\n", "\n").strip()
            if not candidate:
                continue
            if candidate in {"抱歉，出现错误。", "出了点问题。请重试。"}:
                continue
            candidates.append(candidate)
        start = idx + 1
    if not candidates:
        return None
    candidates.sort(key=len, reverse=True)
    return candidates[0]


def _extract_post_count(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _extract_post_author_profile_url(container: Tag) -> str | None:
    for anchor in container.find_all("a", href=True):
        normalized = _normalize_linkedin_href(str(anchor.get("href", "")).strip())
        if normalized and ("/in/" in normalized or "/company/" in normalized):
            return normalized
    return None


def _extract_post_update_context(html: str) -> str:
    marker = 'commentaryViewType\\":\\"Update\\"'
    idx = html.find(marker)
    if idx < 0:
        return html
    start = max(0, idx - 2200)
    end = min(len(html), idx + 2400)
    return html[start:end]


def _extract_post_actor_block(html: str) -> str:
    markers = (
        'legacyControlName\\":\\"actor_picture\\"',
        'legacyControlName":"actor_picture"',
    )
    idx = -1
    for marker in markers:
        idx = max(idx, html.rfind(marker))
    if idx < 0:
        return html
    end = min(len(html), idx + 12000)
    return html[idx:end]


def _extract_post_author_profile_url_from_html(html: str, author_name: str | None = None) -> str | None:
    candidates: list[str] = []
    if author_name:
        anchor = html.find(author_name)
        if anchor >= 0:
            html = html[max(0, anchor - 2600): min(len(html), anchor + 5200)]
    for prefix in ("https://www.linkedin.com/in/", "https://www.linkedin.com/company/"):
        start = 0
        while True:
            start = html.find(prefix, start)
            if start < 0:
                break
            end = start + len(prefix)
            while end < len(html) and html[end] not in {'"', '\\'}:
                end += 1
            candidate = html[start:end]
            if not candidate.endswith("/"):
                candidate += "/"
            normalized = _normalize_linkedin_href(candidate)
            if normalized and "/company/setup/new/" not in normalized:
                candidates.append(normalized)
            start = end
    if candidates:
        for candidate in candidates:
            if "/in/" in candidate:
                return candidate
        return candidates[0]
    return None


def _extract_post_author_name_from_html(html: str) -> str | None:
    matches = re.findall(r'aria-label(?:=(?:\\")?|\\":\\"|":")([^"\\]+?)\s+(?:旗舰帐号|职业档案)', html)
    if matches:
        return matches[0].strip()
    return None


def _extract_post_author_headline_from_html(html: str, author_name: str | None) -> str | None:
    if not author_name:
        return None
    idx = html.find(author_name)
    if idx < 0:
        return None
    window = html[idx: idx + 5200].replace('\\"', '"')
    for match in re.finditer(r'children":\["([^"\n]{1,200})"\]', window):
        candidate = match.group(1).strip()
        if candidate == author_name:
            continue
        if re.search(r"(?:职业档案|旗舰帐号|度\\+|年\\s*•)", candidate):
            continue
        if len(candidate) < 3:
            continue
        return candidate
    return None


def _extract_post_hashtags(body: str) -> list[str]:
    seen: set[str] = set()
    tags: list[str] = []
    for match in re.finditer(r"#([A-Za-z0-9_][A-Za-z0-9_-]*)", body or ""):
        tag = match.group(1)
        lowered = tag.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tags.append(tag)
    return tags


def _extract_post_media_urls(container: Tag, *, media_kind: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    if media_kind == "image":
        candidates = container.find_all(["img"])
    else:
        candidates = container.find_all(["video", "source"])

    for node in candidates:
        raw_url = ""
        if media_kind == "image":
            raw_url = str(
                node.get("src")
                or node.get("data-delayed-url")
                or node.get("data-ghost-url")
                or ""
            ).strip()
        else:
            raw_url = str(node.get("src") or "").strip()
        if not raw_url.startswith("http"):
            continue
        lowered = raw_url.lower()
        if media_kind == "image" and any(token in lowered for token in ("profile-displayphoto", "company-logo", "ghost")):
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        urls.append(raw_url)
    return urls


def _extract_post_date(container: Tag) -> str | None:
    time_node = container.find("time")
    if time_node is None:
        return None
    for attr in ("datetime", "title"):
        raw_value = str(time_node.get(attr, "")).strip()
        normalized = _normalize_date_value(raw_value)
        if normalized:
            return normalized
    return None


def _extract_post_state_count(html: str, counter_name: str, activity_urn: str | None) -> int | None:
    if not activity_urn:
        return None
    marker = f"{counter_name}-{activity_urn}"
    start = 0
    while True:
        idx = html.find(marker, start)
        if idx < 0:
            return None
        window = html[idx: idx + 280].replace('\\"', '"')
        match = re.search(r'"?intValue"?\s*:\s*(\d+)', window)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        start = idx + len(marker)


def _extract_post_reaction_total(html: str, activity_urn: str | None) -> int | None:
    if not activity_urn:
        return None
    pattern = rf'ReactionType_[A-Z_]+_{re.escape(activity_urn)}'
    total = 0
    matched = False
    for match in re.finditer(pattern, html):
        window = html[match.start(): match.start() + 220].replace('\\"', '"')
        value_match = re.search(r'"?intValue"?\s*:\s*(\d+)', window)
        if not value_match:
            continue
        matched = True
        total += int(value_match.group(1))
    return total if matched else None


def _linkedin_job_payload_missing(data: dict[str, Any]) -> bool:
    payload_data = data.get("data") if isinstance(data.get("data"), dict) else {}
    return not isinstance(payload_data.get("jobsDashJobPostingsById"), dict)


def _extract_linkedin_bpr_payloads_from_html(html_text: str, request_keywords: tuple[str, ...]) -> list[dict[str, Any]]:
    text = unescape(html_text or "")
    bodies = {
        match.group(1): match.group(2).strip()
        for match in re.finditer(r'<code style="display: none" id="(bpr-guid-[^"]+)">\s*(.*?)\s*</code>', text, re.DOTALL)
    }
    payloads: list[dict[str, Any]] = []
    for match in re.finditer(r'<code style="display: none" id="(datalet-bpr-guid-[^"]+)">\s*(.*?)\s*</code>', text, re.DOTALL):
        try:
            datalet = json.loads(match.group(2).strip())
        except json.JSONDecodeError:
            continue
        request = str(datalet.get("request") or "")
        if request_keywords and not any(keyword in request for keyword in request_keywords):
            continue
        body = bodies.get(str(datalet.get("body") or ""))
        if not body:
            continue
        try:
            payloads.append(json.loads(body))
        except json.JSONDecodeError:
            continue
    return payloads


def _extract_linkedin_company_from_html(record: dict[str, Any], html_text: str) -> dict[str, Any]:
    payloads = _extract_linkedin_bpr_payloads_from_html(
        html_text,
        (
            "voyagerOrganizationDashCompanies",
            "voyagerJobsDashOrganizationWorkplacePolicies",
        ),
    )
    if payloads:
        merged = _merge_linkedin_payloads(*payloads)
        extracted = _extract_linkedin_company(merged)
        structured = extracted.get("structured") if isinstance(extracted.get("structured"), dict) else {}
        if structured.get("title") or structured.get("source_id"):
            return extracted
    title_match = re.search(r"<title>([^<]+)</title>", html_text or "", re.IGNORECASE)
    raw_title = unescape(title_match.group(1)).strip() if title_match else ""
    title = raw_title.replace("| LinkedIn", "").strip() or str(record.get("company_slug") or "")
    return {
        "title": title,
        "plain_text": "",
        "markdown": f"# {title}".strip() if title else "",
        "structured": {
            "source_id": None,
            "title": title,
            "company_slug": record.get("company_slug"),
            "company_url": f"https://www.linkedin.com/company/{record.get('company_slug')}/" if record.get("company_slug") else None,
        },
        "metadata_extra": {
            "entity_type": "organization",
            "source_id": None,
        },
    }


def _extract_profile_headline_from_html(soup: BeautifulSoup, canonical_url: str, title: str | None) -> str | None:
    canonical_url = canonical_url.rstrip("/")
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").rstrip("/")
        if canonical_url and href != canonical_url:
            continue
        text = " ".join(anchor.stripped_strings).strip()
        if not text:
            continue
        if title and text.startswith(title):
            headline = text[len(title):].strip(" -")
            if headline:
                return headline
    return None


def _extract_profile_location_from_html(html_text: str) -> str | None:
    match = re.search(
        r">([^<>]{2,120})</p>\s*<p[^>]*>·</p>\s*<p[^>]*><a[^>]+/overlay/contact-info/",
        html_text,
        re.IGNORECASE,
    )
    if match:
        return unescape(match.group(1)).strip()
    return None


def _extract_linkedin_profile_from_html(record: dict[str, Any], html_text: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    canonical_url = str(record.get("canonical_url") or f"https://www.linkedin.com/in/{record.get('public_identifier', '')}/").strip()
    title_match = re.search(r"<title>([^<]+)</title>", html_text or "", re.IGNORECASE)
    raw_title = unescape(title_match.group(1)).strip() if title_match else ""
    title = raw_title.replace("| LinkedIn", "").strip() or str(record.get("public_identifier") or "")
    headline = _extract_profile_headline_from_html(soup, canonical_url, title)
    about_match = re.search(r"个人简介\s*(.+?)(?:\s*(?:精选动态|活动|经验|教育|技能|兴趣|推荐内容)|\Z)", soup.get_text("\n", strip=True), re.DOTALL)
    about = about_match.group(1).strip() if about_match else None
    follower_match = re.search(r"([\d,]+)\s*位关注者", soup.get_text("\n", strip=True))
    avatar_match = re.search(r"(https://media\.licdn\.com/[^\s\"']*profile-displayphoto-[^\s\"']+)", html_text)
    banner_match = re.search(r"(https://media\.licdn\.com/[^\s\"']*profile-displaybackgroundimage-[^\s\"']+)", html_text)
    structured = {
        "source_id": str(record.get("public_identifier") or "").strip() or None,
        "title": title,
        "headline": headline,
        "public_identifier": record.get("public_identifier"),
        "about": about,
        "city": _extract_profile_location_from_html(html_text),
        "country_code": None,
        "profile_url": canonical_url or None,
        "avatar": avatar_match.group(1) if avatar_match else None,
        "banner_image": banner_match.group(1) if banner_match else None,
        "follower_count": int(follower_match.group(1).replace(",", "")) if follower_match else None,
    }
    plain_text = "\n\n".join(part for part in (headline, about) if part)
    markdown = "\n\n".join(part for part in (f"# {title}" if title else "", headline, about) if part)
    return {
        "title": title,
        "plain_text": plain_text,
        "markdown": markdown,
        "structured": {key: value for key, value in structured.items() if value not in (None, "", [], {})},
        "metadata_extra": {
            "entity_type": "person",
            "source_id": structured.get("source_id"),
        },
    }


def _first_selector_text(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if not isinstance(node, Tag):
            continue
        text = " ".join(node.stripped_strings).strip()
        if text:
            return text
    return None


def _parse_json_ld_objects(html_text: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    objects: list[dict[str, Any]] = []
    for script in soup.select("script[type='application/ld+json']"):
        raw = script.string or script.get_text("\n", strip=True)
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            objects.append(parsed)
        elif isinstance(parsed, list):
            objects.extend(item for item in parsed if isinstance(item, dict))
    return objects


def _extract_job_posting_ld_json(html_text: str) -> dict[str, Any]:
    for item in _parse_json_ld_objects(html_text):
        item_type = item.get("@type")
        if item_type == "JobPosting" or (isinstance(item_type, list) and "JobPosting" in item_type):
            return item
    return {}


def _job_location_from_ld_json(job_posting: dict[str, Any]) -> str | None:
    location = job_posting.get("jobLocation")
    locations = location if isinstance(location, list) else [location]
    for item in locations:
        if not isinstance(item, dict):
            continue
        address = item.get("address") if isinstance(item.get("address"), dict) else {}
        parts = [
            str(address.get("addressLocality") or "").strip(),
            str(address.get("addressRegion") or "").strip(),
            str(address.get("addressCountry") or "").strip(),
        ]
        text = ", ".join(part for part in parts if part)
        if text:
            return text
    return None


def _clean_html_fragment_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = BeautifulSoup(unescape(value), "html.parser").get_text("\n", strip=True)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text or None


def _extract_linkedin_job_from_html(record: dict[str, Any], html_text: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text or "", "html.parser")
    job_posting = _extract_job_posting_ld_json(html_text)
    title_match = re.search(r"<title>([^<]+)</title>", html_text or "", re.IGNORECASE)
    raw_title = unescape(title_match.group(1)).strip() if title_match else ""
    parts = [part.strip() for part in raw_title.split("|") if part.strip()]
    title = (
        _clean_html_fragment_text(job_posting.get("title"))
        or _first_selector_text(
            soup,
            (
                "h1.top-card-layout__title",
                "h1.topcard__title",
                ".job-details-jobs-unified-top-card__job-title h1",
                "h1",
            ),
        )
        or (parts[0] if parts else str(record.get("job_id") or ""))
    )
    company_name = (
        _clean_html_fragment_text((job_posting.get("hiringOrganization") or {}).get("name") if isinstance(job_posting.get("hiringOrganization"), dict) else None)
        or _first_selector_text(
            soup,
            (
                "a.topcard__org-name-link",
                ".job-details-jobs-unified-top-card__company-name a",
                ".topcard__flavor-row a",
            ),
        )
        or (parts[1] if len(parts) >= 2 and parts[1].lower() != "linkedin" else None)
    )
    location = (
        _first_selector_text(
            soup,
            (
                ".topcard__flavor--bullet",
                ".job-details-jobs-unified-top-card__primary-description-container span",
                ".topcard__flavor-row .topcard__flavor--bullet",
            ),
        )
        or _job_location_from_ld_json(job_posting)
    )
    description = (
        _clean_html_fragment_text(job_posting.get("description"))
        or _first_selector_text(
            soup,
            (
                ".show-more-less-html__markup",
                ".jobs-description__content .jobs-box__html-content",
                ".description__text",
                "[class*='jobs-description']",
            ),
        )
    )
    employment_type = _clean_html_fragment_text(job_posting.get("employmentType"))
    generic_titles = {"linkedin", "职位", "job"}
    if str(title or "").strip().lower() in generic_titles and not any((company_name, location, description)):
        title = str(record.get("job_id") or "").strip() or title
    structured = {
        "source_id": str(record.get("job_id") or "").strip() or None,
        "title": title,
        "company_name": company_name,
        "location": location,
        "description": description,
        "employment_type": employment_type,
    }
    plain_text = description or (title if title and title != str(record.get("job_id") or "") else "")
    return {
        "title": title,
        "plain_text": plain_text,
        "markdown": f"# {title}\n\n{plain_text}".strip() if title else "",
        "structured": {key: value for key, value in structured.items() if value not in (None, "", [], {})},
        "metadata_extra": {
            "entity_type": "job",
            "source_id": structured.get("source_id"),
        },
    }


def _build_linkedin_enrichment_request(record: dict[str, Any], requested_groups: tuple[str, ...] = ()) -> dict[str, Any]:
    if requested_groups:
        field_groups = requested_groups
    else:
        resource_type = str(record.get("resource_type") or "")
        field_groups = {
            "profile": PROFILE_FIELD_GROUPS,
            "company": COMPANY_FIELD_GROUPS,
            "job": JOB_FIELD_GROUPS,
            "post": POST_FIELD_GROUPS,
        }.get(resource_type, ENRICH_PLAN.field_groups)
    return {
        "route": ENRICH_PLAN.route,
        "field_groups": tuple(field_groups),
    }


def _normalize_linkedin_record(
    record: dict[str, Any],
    discovered: dict[str, Any],
    extracted: dict[str, Any],
    supplemental: dict[str, Any],
) -> dict[str, Any]:
    del supplemental
    metadata = extracted.get("metadata", {}) if isinstance(extracted.get("metadata"), dict) else {}
    extracted_structured = extracted.get("structured", {}) if isinstance(extracted.get("structured"), dict) else {}
    linkedin_data = extracted_structured.get("linkedin", {}) if isinstance(extracted_structured.get("linkedin"), dict) else {}
    result = dict(extracted_structured)
    result.update(linkedin_data)

    canonical_url = str((discovered or {}).get("canonical_url") or record.get("canonical_url") or "").strip()
    resource_type = str(record.get("resource_type") or "")
    title = metadata.get("title") or result.get("title")
    description = metadata.get("description") or result.get("description")

    if resource_type == "profile":
        result.setdefault("linkedin_num_id", result.get("source_id"))
        result.setdefault("name", title)
        result.setdefault("URL", canonical_url)
        result.setdefault("profile_url", canonical_url)
        result.setdefault("position", result.get("headline"))
        result.setdefault("avatar_url", result.get("avatar"))
        result.setdefault("followers", result.get("follower_count"))
    elif resource_type == "company":
        specialties = result.get("specialties")
        if isinstance(specialties, list):
            specialties = ", ".join(str(item).strip() for item in specialties if str(item).strip()) or None
            if specialties:
                result["specialties"] = specialties
        result.setdefault("company_id", result.get("source_id"))
        result.setdefault("name", title)
        result.setdefault("company_name", title)
        result.setdefault("URL", canonical_url)
        result.setdefault("company_url", canonical_url)
        result.setdefault("about", description)
        result.setdefault("headquarters_location", result.get("headquarters"))
        result.setdefault("website", result.get("website_url"))
        result.setdefault("followers", result.get("follower_count"))
        result.setdefault("employee_count", result.get("staff_count"))
        result.setdefault("employees_in_linkedin", result.get("staff_count"))
    elif resource_type == "job":
        result.setdefault("job_posting_id", result.get("source_id") or record.get("job_id"))
        result.setdefault("job_title", result.get("title") or title)
        result.setdefault("job_summary", _job_summary_from_description(result.get("description")))
        result.setdefault("job_description", result.get("description") or description)
        result.setdefault("job_location", result.get("location"))
        result.setdefault("location", result.get("location"))
        result.setdefault("date_posted", _normalize_date_value(result.get("published_at")))
        result.setdefault("posted_date", result.get("date_posted"))
        result.setdefault("job_function", _join_linkedin_values(result.get("job_functions")))
        result.setdefault("job_seniority_level", result.get("seniority_level"))
        workplace_type = result.get("workplace_type")
        if workplace_type not in (None, ""):
            result.setdefault("workplace_type", workplace_type)
            result.setdefault("remote_policy", workplace_type)
        result.setdefault("application_method", _linkedin_application_method(result))
    elif resource_type == "post":
        post_id = _linkedin_id(result.get("activity_urn") or record.get("activity_urn"))
        result.setdefault("post_id", post_id)
        result.setdefault("post_text", result.get("body"))
        result.setdefault("title", result.get("author_name") or title)
        result.setdefault("headline", result.get("author_headline"))
        result.setdefault("user_id", result.get("author_id"))
        result.setdefault("user_url", result.get("author_profile_url"))
        result.setdefault("date_posted", _normalize_date_value(result.get("date_posted")))
        result.setdefault("posted_date", result.get("date_posted"))
        result.setdefault("images", list(result.get("image_urls") or []))
        result.setdefault("videos", list(result.get("video_urls") or []))
        result.setdefault("num_likes", result.get("reaction_count"))
        result.setdefault("num_comments", result.get("comment_count"))
        result.setdefault("num_shares", result.get("repost_count"))
        result.setdefault("like_count", result.get("num_likes"))
        result.setdefault("comment_count", result.get("num_comments"))
        result.setdefault("share_count", result.get("num_shares"))
        result.setdefault("author_profile_url", result.get("author_profile_url"))
        result.setdefault("post_media_urls", _merge_media_urls(result.get("images"), result.get("videos")))

    if title:
        result.setdefault("title", title)
    if canonical_url:
        result.setdefault("canonical_url", canonical_url)

    return {key: value for key, value in result.items() if value not in (None, "", [], {})}


def _job_summary_from_description(description: Any) -> str | None:
    text = str(description or "").strip()
    if not text:
        return None
    first_block = re.split(r"\n\s*\n", text, maxsplit=1)[0].strip()
    return first_block[:400] or None


def _join_linkedin_values(value: Any) -> str | None:
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(parts) or None
    text = str(value or "").strip()
    return text or None


def _linkedin_application_method(values: dict[str, Any]) -> str | None:
    if values.get("company_apply_url"):
        return "external_link"
    raw = str(values.get("application_type") or "").strip().lower()
    if "easy" in raw:
        return "Easy Apply"
    if "email" in raw:
        return "email"
    return None


def _linkedin_workplace_type(job: dict[str, Any], included: list[dict[str, Any]]) -> str | None:
    direct = job.get("formattedWorkplaceType") or job.get("workplaceType") or job.get("workplaceTypes")
    if isinstance(direct, list):
        for value in direct:
            text = str(value or "").strip()
            if text:
                return text
        return None
    text = str(direct or "").strip()
    if text:
        return text
    for key in ("*formattedWorkplaceType", "*workplaceType"):
        resolved = _lookup_entity_text(included, job.get(key))
        if resolved not in (None, ""):
            return resolved
    return None


def _normalize_date_value(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    try:
        normalized = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return normalized.date().isoformat()


def _merge_media_urls(*groups: Any) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        if not isinstance(group, list):
            continue
        for value in group:
            text = str(value or "").strip()
            lowered = text.lower()
            if not text or lowered in seen:
                continue
            seen.add(lowered)
            merged.append(text)
    return merged


def _extract_linkedin_company(data: dict[str, Any]) -> dict[str, Any]:
    payload_items = _linkedin_items(data)
    company = _select_company_item(payload_items)
    title = company.get("name")
    text = company.get("description") or _multi_locale_text(company.get("multiLocaleDescriptions")) or company.get("tagline") or ""
    headquarters = _headquarters_label(company)
    follower_count = _follower_count(payload_items, company)
    logo_url = _logo_url(company)
    structured = {
        "source_id": _linkedin_id(company.get("dashEntityUrn") or company.get("entityUrn")),
        "title": title,
        "description": text,
        "company_slug": company.get("universalName"),
        "industry": _industry_label(company),
        "staff_count": company.get("staffCount"),
        "staff_count_range_start": (company.get("staffCountRange") or {}).get("start"),
        "headquarters": headquarters,
        "country_code": company.get("countryISOCode") or ((company.get("headquarter") or {}).get("country") if isinstance(company.get("headquarter"), dict) else None),
        "locations": _location_labels(company),
        "follower_count": follower_count,
        "logo_url": logo_url,
        "website_url": company.get("companyPageUrl"),
        "company_url": company.get("url"),
        "founded_year": company.get("foundedOn", {}).get("year") if isinstance(company.get("foundedOn"), dict) else company.get("foundedYear"),
        "specialties": company.get("specialities") or [],
        "company_size_range": _company_size_range_label(company),
        "company_type": _company_type_value(company),
        "top_topics": _company_top_topics(company),
        "funding_stage_inferred": _company_funding_stage(company),
        "linkable_identifiers": _company_linkable_identifiers(company),
        "company_stage_signals": _company_stage_signals(company),
        "tech_stack_mentioned_in_about": _company_tech_stack_mentions(text, company.get("specialities") or []),
    }
    return {
        "title": title,
        "plain_text": text,
        "markdown": f"# {title}\n\n{text}".strip() if title or text else "",
        "structured": structured,
        "metadata_extra": {
            "entity_type": "organization",
            "source_id": structured["source_id"],
        },
    }


def _extract_linkedin_profile(data: dict[str, Any]) -> dict[str, Any]:
    payload_items = _linkedin_items(data)
    profile = _select_richest_item(payload_items, "Profile")
    first = profile.get("firstName") or ""
    last = profile.get("lastName") or ""
    title = " ".join(part for part in (first, last) if part).strip() or None
    headline = profile.get("headline") or ""
    profile_url = profile.get("publicProfileUrl")
    structured = {
        "source_id": _linkedin_id(profile.get("entityUrn")),
        "title": title,
        "headline": headline,
        "public_identifier": profile.get("publicIdentifier"),
        "about": profile.get("summary"),
        "city": profile.get("geoLocationName") or profile.get("locationName"),
        "country_code": profile.get("locationCountryCode"),
        "profile_url": profile_url,
        "avatar": _image_url(profile.get("profilePicture") or profile.get("picture")),
        "banner_image": _image_url(profile.get("backgroundImage")),
    }
    return {
        "title": title,
        "plain_text": "\n\n".join(part for part in (headline, structured.get("about")) if part),
        "markdown": "\n\n".join(part for part in (f"# {title}" if title else "", headline, structured.get("about")) if part),
        "structured": structured,
        "metadata_extra": {
            "entity_type": "person",
            "source_id": structured["source_id"],
        },
    }


def _extract_linkedin_job(data: dict[str, Any]) -> dict[str, Any]:
    included = _linkedin_items(data)
    payload_data = data.get("data") if isinstance(data.get("data"), dict) else {}
    job = payload_data.get("jobsDashJobPostingsById") if isinstance(payload_data, dict) and isinstance(payload_data.get("jobsDashJobPostingsById"), dict) else None
    if not isinstance(job, dict):
        job = _select_richest_item(included, "JobPosting")
    company = _select_richest_item(included, "Company", "Organization")
    description = ((job.get("description") or {}).get("text") if isinstance(job.get("description"), dict) else job.get("description")) or ""
    location = _lookup_entity_text(included, job.get("*location"))
    structured = {
        "source_id": _linkedin_id(job.get("entityUrn")),
        "title": job.get("title"),
        "description": description,
        "company_name": company.get("name") or ((job.get("companyDetails") or {}).get("name")),
        "company_id": _linkedin_id(company.get("entityUrn") or (((job.get("companyDetails") or {}).get("jobCompany") or {}).get("*company"))),
        "location": location,
        "published_at": _normalize_epoch(job.get("listedAt") or job.get("originalListedAt")),
        "employment_type": _lookup_entity_text(included, job.get("*employmentStatus")),
        "workplace_type": _linkedin_workplace_type(job, included),
        "job_functions": job.get("jobFunctions") or [],
        "company_apply_url": job.get("companyApplyUrl"),
    }
    return {
        "title": structured["title"],
        "plain_text": description,
        "markdown": f"# {structured['title']}\n\n{description}".strip() if structured["title"] or description else "",
        "structured": structured,
        "metadata_extra": {
            "entity_type": "job",
            "source_id": structured["source_id"],
            "published_at": structured["published_at"],
        },
    }


def _select_richest_item(included: list[dict[str, Any]], *type_keywords: str) -> dict[str, Any]:
    candidates: list[tuple[int, dict[str, Any]]] = []
    for item in included:
        item_type = item.get("$type") or item.get("_type") or item.get("$recipeType") or item.get("_recipeType") or ""
        if any(keyword in item_type for keyword in type_keywords):
            score = sum(1 for value in item.values() if value not in (None, "", [], {}))
            candidates.append((score, item))
    if not candidates:
        return {}
    candidates.sort(key=lambda value: value[0], reverse=True)
    return candidates[0][1]


def _linkedin_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[int] = set()

    def append_item(item: Any) -> None:
        if not isinstance(item, dict):
            return
        item_id = id(item)
        if item_id in seen:
            return
        seen.add(item_id)
        items.append(item)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            included = node.get("included")
            if isinstance(included, list):
                for item in included:
                    append_item(item)
            elements = node.get("elements")
            if isinstance(elements, list):
                for item in elements:
                    append_item(item)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return items


def _merge_linkedin_payloads(*payloads: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    included: list[dict[str, Any]] = []
    elements: list[dict[str, Any]] = []
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            if key not in {"included", "data"}:
                merged[key] = value
        payload_included = payload.get("included")
        if isinstance(payload_included, list):
            included.extend(item for item in payload_included if isinstance(item, dict))
        payload_data = payload.get("data")
        if isinstance(payload_data, dict):
            payload_elements = payload_data.get("elements")
            if isinstance(payload_elements, list):
                elements.extend(item for item in payload_elements if isinstance(item, dict))
            for key, value in payload_data.items():
                if key != "elements":
                    merged.setdefault("data", {})[key] = value
    if included:
        merged["included"] = included
    if elements:
        merged.setdefault("data", {})["elements"] = elements
    return merged


def _profile_urn_from_payload(data: dict[str, Any]) -> str | None:
    for item in _linkedin_items(data):
        entity_urn = item.get("entityUrn")
        if isinstance(entity_urn, str) and entity_urn.startswith("urn:li:fsd_profile:"):
            return entity_urn
    profile = _select_richest_item(_linkedin_items(data), "Profile")
    entity_urn = profile.get("entityUrn")
    return entity_urn if isinstance(entity_urn, str) else None


def _company_id_from_payload(data: dict[str, Any]) -> str | None:
    for item in _linkedin_items(data):
        entity_urn = item.get("entityUrn")
        if isinstance(entity_urn, str) and entity_urn.startswith("urn:li:fsd_company:"):
            return _linkedin_id(entity_urn)
    company = _select_company_item(_linkedin_items(data))
    entity_urn = company.get("entityUrn") or company.get("dashEntityUrn")
    company_id = _linkedin_id(entity_urn)
    if company_id:
        return company_id
    for item in _linkedin_items(data):
        nested = item.get("*entityResult") or item.get("*organizationalTarget")
        candidate = _linkedin_id(nested)
        if candidate:
            return candidate
    return None


def _select_company_item(included: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[tuple[int, dict[str, Any]]] = []
    for item in included:
        item_type = item.get("$type") or item.get("_type") or item.get("$recipeType") or item.get("_recipeType") or ""
        is_company_like = any(keyword in item_type for keyword in ("Company", "Organization"))
        has_company_shape = bool(item.get("name")) and (
            bool(item.get("universalName"))
            or str(item.get("entityUrn", "")).startswith("urn:li:fs_normalized_company:")
            or str(item.get("entityUrn", "")).startswith("urn:li:fsd_company:")
        )
        if is_company_like or has_company_shape:
            score = sum(1 for value in item.values() if value not in (None, "", [], {}))
            candidates.append((score, item))
    if not candidates:
        return {}
    candidates.sort(key=lambda value: value[0], reverse=True)
    return candidates[0][1]


def _linkedin_id(entity_urn: Any) -> str | None:
    if not isinstance(entity_urn, str) or ":" not in entity_urn:
        return None
    return entity_urn.split(":")[-1]


def _normalize_epoch(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    timestamp = value / 1000 if value > 1e12 else value
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _lookup_entity_text(included: list[dict[str, Any]], entity_urn: Any) -> str | None:
    if not isinstance(entity_urn, str):
        return None
    for item in included:
        if item.get("entityUrn") == entity_urn:
            return item.get("defaultLocalizedName") or item.get("localizedName") or item.get("abbreviatedLocalizedName")
    return None


def _multi_locale_text(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    localized = payload.get("localized")
    if not isinstance(localized, dict) or not localized:
        return None
    preferred = payload.get("preferredLocale") or {}
    if isinstance(preferred, dict):
        key = f"{preferred.get('language')}_{preferred.get('country')}"
        if key in localized:
            return localized[key]
    return next(iter(localized.values()), None)


def _headquarters_label(company: dict[str, Any]) -> str | None:
    grouped = company.get("groupedLocationsByCountry") or company.get("groupedLocations")
    if isinstance(grouped, list) and grouped:
        first = grouped[0]
        if isinstance(first, dict):
            return first.get("localizedName")
    headquarter = company.get("headquarter")
    if isinstance(headquarter, dict):
        return headquarter.get("city")
    return None


def _follower_count(included: list[dict[str, Any]], company: dict[str, Any]) -> int | None:
    following_info = company.get("followingInfo")
    if isinstance(following_info, dict) and isinstance(following_info.get("followerCount"), int):
        return following_info.get("followerCount")
    following_urn = company.get("*followingInfo") or company.get("*followingState") or company.get("dashFollowingStateUrn")
    if isinstance(following_urn, str):
        for item in included:
            if item.get("entityUrn") == following_urn:
                return item.get("followerCount")
    return None


def _logo_url(company: dict[str, Any]) -> str | None:
    image = None
    if isinstance(company.get("logo"), dict):
        image = company["logo"].get("image")
    if not isinstance(image, dict) and isinstance(company.get("logos"), dict):
        image = company["logos"].get("logo")
    if isinstance(image, dict) and "com.linkedin.common.VectorImage" in image:
        image = image.get("com.linkedin.common.VectorImage")
    if not isinstance(image, dict):
        return None
    root_url = image.get("rootUrl")
    artifacts = image.get("artifacts")
    if not root_url or not isinstance(artifacts, list) or not artifacts:
        return None
    best = max((artifact for artifact in artifacts if isinstance(artifact, dict)), key=lambda artifact: artifact.get("width", 0), default=None)
    if not best:
        return None
    return f"{root_url}{best.get('fileIdentifyingUrlPathSegment', '')}"


def _image_url(image_like: Any) -> str | None:
    image = image_like
    if isinstance(image, dict) and "image" in image and isinstance(image.get("image"), dict):
        image = image.get("image")
    if isinstance(image, dict) and "com.linkedin.common.VectorImage" in image:
        image = image.get("com.linkedin.common.VectorImage")
    if not isinstance(image, dict):
        return None
    root_url = image.get("rootUrl")
    artifacts = image.get("artifacts")
    if not root_url or not isinstance(artifacts, list) or not artifacts:
        return None
    best = max((artifact for artifact in artifacts if isinstance(artifact, dict)), key=lambda artifact: artifact.get("width", 0), default=None)
    if not best:
        return None
    return f"{root_url}{best.get('fileIdentifyingUrlPathSegment', '')}"


def _location_labels(company: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    grouped = company.get("groupedLocations")
    candidates: list[dict[str, Any]] = []
    if isinstance(company.get("headquarter"), dict):
        candidates.append(company["headquarter"])
    if isinstance(grouped, list):
        candidates.extend(item for item in grouped if isinstance(item, dict))
    for item in candidates:
        parts = [
            str(item.get("city") or "").strip(),
            str(item.get("geographicArea") or item.get("state") or "").strip(),
            str(item.get("country") or item.get("countryCode") or "").strip(),
        ]
        label = ", ".join(part for part in parts if part)
        lowered = label.lower()
        if not label or lowered in seen:
            continue
        seen.add(lowered)
        labels.append(label)
    return labels


def _industry_label(company: dict[str, Any]) -> str | None:
    industries = company.get("industries")
    if isinstance(industries, list) and industries:
        first = industries[0]
        if isinstance(first, dict):
            return first.get("localizedName") or first.get("name")
        if isinstance(first, str):
            return first

    company_industries = company.get("companyIndustries")
    if isinstance(company_industries, list) and company_industries:
        first = company_industries[0]
        if isinstance(first, dict):
            return first.get("localizedName") or first.get("name")
        if isinstance(first, str):
            return first

    return None


def _company_size_range_label(company: dict[str, Any]) -> str | None:
    staff_count_range = company.get("staffCountRange")
    if not isinstance(staff_count_range, dict):
        return None
    start = staff_count_range.get("start")
    end = staff_count_range.get("end")
    if isinstance(start, int) and isinstance(end, int):
        return f"{start}-{end} employees"
    if isinstance(start, int):
        return f"{start}+ employees"
    return None


def _company_type_value(company: dict[str, Any]) -> str | None:
    company_type = company.get("companyType")
    if isinstance(company_type, dict):
        company_type = company_type.get("localizedName") or company_type.get("name")
    value = str(company_type or "").strip().lower()
    if not value:
        return None
    mapping = {
        "public company": "public",
        "public": "public",
        "privately held": "private",
        "private": "private",
        "joint venture": "private",
        "合营企业": "private",
        "nonprofit": "nonprofit",
        "非营利组织": "nonprofit",
        "educational": "educational",
        "政府机构": "government",
        "government agency": "government",
        "government": "government",
    }
    return mapping.get(value)


def _company_top_topics(company: dict[str, Any]) -> list[str]:
    cards = company.get("contentTopicCards")
    if not isinstance(cards, list):
        return []
    topics: list[str] = []
    seen: set[str] = set()
    for card in cards:
        if not isinstance(card, dict):
            continue
        raw = card.get("name")
        if not raw and isinstance(card.get("entityUrn"), str) and ":hashtag:" in card["entityUrn"]:
            raw = card["entityUrn"].rsplit(":hashtag:", 1)[-1]
        topic = str(raw or "").strip().lower()
        if not topic or topic in seen:
            continue
        seen.add(topic)
        topics.append(topic)
    return topics


def _company_funding_stage(company: dict[str, Any]) -> str | None:
    funding = company.get("fundingData")
    if not isinstance(funding, dict):
        return None
    last_round = funding.get("lastFundingRound")
    if not isinstance(last_round, dict):
        return None
    funding_type = str(last_round.get("fundingType") or "").strip().lower()
    return funding_type or None


def _company_linkable_identifiers(company: dict[str, Any]) -> dict[str, Any] | None:
    identifiers: dict[str, Any] = {}
    website = str(company.get("companyPageUrl") or "").strip()
    if website:
        identifiers["website_domain"] = urlsplit(website).hostname or None
    funding = company.get("fundingData")
    if isinstance(funding, dict):
        crunchbase = str(funding.get("companyCrunchbaseUrl") or "").strip()
        if crunchbase:
            identifiers["crunchbase_hint"] = crunchbase
    return identifiers or None


def _company_stage_signals(company: dict[str, Any]) -> dict[str, Any] | None:
    funding = company.get("fundingData")
    if not isinstance(funding, dict):
        return None
    funding_stage = _company_funding_stage(company)
    num_rounds = funding.get("numFundingRounds")
    evidence: list[str] = []
    if funding_stage:
        evidence.append(funding_stage.upper())
    if isinstance(num_rounds, int) and num_rounds > 0:
        evidence.append(f"{num_rounds} funding rounds")
    if not evidence:
        return None
    return {
        "stage_inferred": funding_stage,
        "confidence": 0.8 if funding_stage else 0.5,
        "evidence_phrases": evidence,
    }


def _company_tech_stack_mentions(description: Any, specialties: Any) -> list[str]:
    parts: list[str] = []
    if isinstance(description, str) and description.strip():
        parts.append(description)
    if isinstance(specialties, str) and specialties.strip():
        parts.append(specialties)
    elif isinstance(specialties, list):
        parts.extend(str(item) for item in specialties if str(item).strip())
    haystack = "\n".join(parts).lower()
    if not haystack:
        return []
    matches: list[str] = []
    for label, needles in (
        ("AI", ("artificial intelligence", " ai ")),
        ("machine learning", ("machine learning",)),
        ("Python", ("python",)),
        ("Kubernetes", ("kubernetes",)),
    ):
        if any(needle in haystack for needle in needles):
            matches.append(label)
    return matches


ADAPTER = PlatformAdapter(
    platform="linkedin",
    discovery=PlatformDiscoveryPlan(
        resource_types=("search", "profile", "company", "post", "job"),
        canonicalizer="linkedin",
    ),
    fetch=FETCH_PLAN,
    extract=EXTRACT_PLAN,
    normalize=NORMALIZE_PLAN,
    enrich=ENRICH_PLAN,
    error=PlatformErrorPlan(normalized_code="LINKEDIN_FETCH_FAILED"),
    resolve_backend_fn=_resolve_linkedin_backend,
    fetch_fn=default_fetch_executor(_fetch_linkedin_api),
    extract_fn=_extract_linkedin,
    normalize_fn=_normalize_linkedin_record,
    enrichment_fn=_build_linkedin_enrichment_request,
)
