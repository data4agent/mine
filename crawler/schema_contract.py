from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse


Record = dict[str, Any]
Resolver = Callable[[Record], Any]

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema(1)"

SCHEMA_NAME_BY_PLATFORM_RESOURCE: dict[tuple[str, str], str] = {
    ("amazon", "product"): "amazon_products",
    ("amazon", "review"): "amazon_reviews",
    ("amazon", "seller"): "amazon_sellers",
    ("arxiv", "paper"): "arxiv",
    ("arxiv", "article"): "arxiv",
    ("linkedin", "company"): "linkedin_company",
    ("linkedin", "job"): "linkedin_jobs",
    ("linkedin", "post"): "linkedin_posts",
    ("linkedin", "profile"): "linkedin_profiles",
    ("wikipedia", "article"): "wikipedia",
}


@dataclass(frozen=True, slots=True)
class SchemaContract:
    dataset_name: str
    schema_path: Path
    schema: dict[str, Any]
    property_names: tuple[str, ...]
    required_fields: tuple[str, ...]


def get_schema_contract(record: Record) -> SchemaContract:
    platform = str(record.get("platform") or "").strip().lower()
    resource_type = str(record.get("resource_type") or "").strip().lower()
    if not platform or not resource_type:
        inferred_platform, inferred_resource_type = _infer_record_kind(record)
        platform = platform or inferred_platform
        resource_type = resource_type or inferred_resource_type
    dataset_name = SCHEMA_NAME_BY_PLATFORM_RESOURCE.get((platform, resource_type))
    if dataset_name is None:
        raise ValueError(f"unsupported schema contract for platform={platform!r} resource_type={resource_type!r}")
    return _load_schema_contract(dataset_name)


@lru_cache(maxsize=None)
def _load_schema_contract(dataset_name: str) -> SchemaContract:
    schema_path = SCHEMA_DIR / f"{dataset_name}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    return SchemaContract(
        dataset_name=dataset_name,
        schema_path=schema_path,
        schema=schema,
        property_names=tuple(properties.keys()) if isinstance(properties, dict) else (),
        required_fields=tuple(required) if isinstance(required, list) else (),
    )


def flatten_record_for_schema(record: Record) -> dict[str, Any]:
    contract = get_schema_contract(record)
    flattened: dict[str, Any] = {}
    for field_name in contract.property_names:
        value = _resolve_schema_field(record, field_name)
        normalizer = FIELD_NORMALIZERS.get(field_name)
        if normalizer is not None:
            value = normalizer(value)
        if value in (None, ""):
            continue
        flattened[field_name] = value
    return flattened


def _resolve_schema_field(record: Record, field_name: str) -> Any:
    for value in _direct_values(record, field_name):
        if value not in (None, ""):
            return value

    resolver = FIELD_RESOLVERS.get(field_name)
    if resolver is None:
        return None
    return resolver(record)


def _direct_values(record: Record, field_name: str) -> list[Any]:
    values: list[Any] = []
    structured = record.get("structured")
    if isinstance(structured, dict):
        values.append(structured.get(field_name))
    enrichment = record.get("enrichment")
    if isinstance(enrichment, dict):
        enriched_fields = enrichment.get("enriched_fields")
        if isinstance(enriched_fields, dict):
            values.append(enriched_fields.get(field_name))
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        values.append(metadata.get(field_name))
    values.append(record.get(field_name))
    return values


def _canonical_url(record: Record) -> str | None:
    value = record.get("canonical_url") or record.get("url")
    return str(value).strip() if value not in (None, "") else None


def _infer_record_kind(record: Record) -> tuple[str, str]:
    canonical_url = _canonical_url(record) or ""
    parsed = urlparse(canonical_url)
    hostname = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    if "wikipedia.org" in hostname:
        return "wikipedia", "article"
    if "linkedin.com" in hostname:
        if "/in/" in path:
            return "linkedin", "profile"
        if "/company/" in path:
            return "linkedin", "company"
        if "/jobs/view/" in path:
            return "linkedin", "job"
        if "/feed/update/" in path:
            return "linkedin", "post"
    if "amazon." in hostname:
        if "/dp/" in path or "/gp/product/" in path:
            return "amazon", "product"
        if "seller=" in parsed.query:
            return "amazon", "seller"
        if "/review/" in path or "/gp/customer-reviews/" in path:
            return "amazon", "review"
    if "arxiv.org" in hostname:
        return "arxiv", "paper"
    return "", ""


def _structured(record: Record) -> dict[str, Any]:
    value = record.get("structured")
    return value if isinstance(value, dict) else {}


def _metadata(record: Record) -> dict[str, Any]:
    value = record.get("metadata")
    return value if isinstance(value, dict) else {}


def _first(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _join_strings(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (list, tuple)):
        parts = [str(item).strip() for item in value if str(item).strip()]
        if parts:
            return ", ".join(parts)
    return None


def _count_items(value: Any) -> int | None:
    if isinstance(value, (list, tuple, set)):
        return len(value)
    return None


def _wikipedia_has_infobox(record: Record) -> bool | None:
    structured = _structured(record)
    metadata = _metadata(record)

    infobox = _first(structured.get("infobox_structured"), structured.get("infobox"))
    if isinstance(infobox, dict):
        return bool(infobox)

    pageprops = metadata.get("pageprops")
    if isinstance(pageprops, dict):
        for key in ("infobox", "wikibase_item", "wikibase-shortdesc"):
            if key in pageprops:
                return True
    return None


def _wikipedia_language(record: Record) -> str | None:
    explicit = _first(record.get("language"), _structured(record).get("language"), _metadata(record).get("language"))
    if explicit not in (None, ""):
        return explicit
    canonical_url = _canonical_url(record)
    if not canonical_url:
        return None
    hostname = urlparse(canonical_url).hostname or ""
    parts = hostname.split(".")
    return parts[0] if len(parts) >= 3 else None


def _amazon_seller_id(record: Record) -> str | None:
    candidate = _first(record.get("seller_id"), _structured(record).get("seller_id"))
    if candidate not in (None, ""):
        return candidate
    canonical_url = _canonical_url(record)
    if not canonical_url:
        return None
    return parse_qs(urlparse(canonical_url).query).get("seller", [None])[0]


def _amazon_review_id(record: Record) -> str | None:
    candidate = _first(record.get("review_id"), _structured(record).get("review_id"))
    if candidate not in (None, ""):
        return candidate
    canonical_url = _canonical_url(record)
    if not canonical_url:
        return None
    path_parts = [segment for segment in urlparse(canonical_url).path.split("/") if segment]
    if "customer-reviews" in path_parts:
        index = path_parts.index("customer-reviews")
        if index + 1 < len(path_parts):
            return path_parts[index + 1]
    return None


def _linkedin_post_id(record: Record) -> str | None:
    candidate = _first(
        record.get("post_id"),
        _structured(record).get("post_id"),
        _structured(record).get("source_id"),
        record.get("source_id"),
        record.get("activity_urn"),
        _structured(record).get("activity_urn"),
    )
    if isinstance(candidate, str):
        text = candidate.strip()
        if text.isdigit():
            return text
        if "activity:" in text:
            tail = text.rsplit("activity:", 1)[-1]
            if tail.isdigit():
                return tail
    canonical_url = _canonical_url(record)
    if not canonical_url:
        return None
    path = urlparse(canonical_url).path
    marker = "activity:"
    if marker in path:
        tail = path.rsplit(marker, 1)[-1].strip("/")
        if tail.isdigit():
            return tail
    return None


def _amazon_marketplace(record: Record) -> str | None:
    return _first(record.get("marketplace"), _structured(record).get("marketplace"))


def _amazon_product_dedup_key(record: Record) -> str | None:
    asin = _first(record.get("asin"), _structured(record).get("asin"))
    if asin in (None, ""):
        return None
    marketplace = _amazon_marketplace(record)
    return f"{asin}:{marketplace}" if marketplace not in (None, "") else str(asin)


def _amazon_seller_dedup_key(record: Record) -> str | None:
    seller_id = _amazon_seller_id(record)
    if seller_id in (None, ""):
        return None
    marketplace = _amazon_marketplace(record)
    return f"{seller_id}:{marketplace}" if marketplace not in (None, "") else str(seller_id)


def _amazon_review_dedup_key(record: Record) -> str | None:
    review_id = _amazon_review_id(record)
    if review_id in (None, ""):
        return None
    marketplace = _amazon_marketplace(record)
    return f"{review_id}:{marketplace}" if marketplace not in (None, "") else str(review_id)


def _amazon_dedup_key(record: Record) -> str | None:
    platform = str(record.get("platform") or "").strip().lower()
    resource_type = str(record.get("resource_type") or "").strip().lower()
    if not platform or not resource_type:
        platform, resource_type = _infer_record_kind(record)
    if platform != "amazon":
        return None
    if resource_type == "seller":
        return _amazon_seller_dedup_key(record)
    if resource_type == "review":
        return _amazon_review_dedup_key(record)
    return _amazon_product_dedup_key(record)


FIELD_RESOLVERS: dict[str, Resolver] = {
    "ID": lambda record: _first(
        record.get("ID"),
        _structured(record).get("ID"),
        record.get("linkedin_num_id"),
        _structured(record).get("linkedin_num_id"),
        record.get("company_id"),
        _structured(record).get("company_id"),
        _structured(record).get("source_id"),
        record.get("source_id"),
    ),
    "URL": _canonical_url,
    "canonical_url": _canonical_url,
    "title": lambda record: _first(_structured(record).get("title"), _metadata(record).get("title"), record.get("title")),
    "name": lambda record: _first(_structured(record).get("name"), _structured(record).get("title"), _metadata(record).get("title"), record.get("name"), record.get("title")),
    "about": lambda record: _first(
        record.get("about"),
        _structured(record).get("about"),
        _structured(record).get("about_summary"),
        _structured(record).get("description"),
        _metadata(record).get("description"),
        record.get("summary"),
    ),
    "seller_name": lambda record: _first(
        record.get("seller_name"),
        _structured(record).get("seller_name"),
        record.get("name"),
        _structured(record).get("name"),
        record.get("seller"),
        _structured(record).get("seller"),
        _metadata(record).get("title"),
        record.get("title"),
    ),
    "job_title": lambda record: _first(
        _structured(record).get("job_title"),
        _structured(record).get("title"),
        _metadata(record).get("job_title"),
        _metadata(record).get("title"),
        record.get("job_title"),
        record.get("title"),
    ),
    "post_text": lambda record: _first(
        record.get("post_text"),
        _structured(record).get("post_text"),
        record.get("plain_text"),
        record.get("cleaned_data"),
        record.get("markdown"),
    ),
    "review_text": lambda record: _first(
        record.get("review_text"),
        _structured(record).get("review_text"),
        record.get("review_body"),
        _structured(record).get("review_body"),
        record.get("plain_text"),
        record.get("cleaned_data"),
    ),
    "author_name": lambda record: _first(
        record.get("author_name"),
        _structured(record).get("author_name"),
        record.get("author"),
        _structured(record).get("author"),
        record.get("reviewer_name"),
        _structured(record).get("reviewer_name"),
        record.get("reviewer"),
        _structured(record).get("reviewer"),
        record.get("user_name"),
        _structured(record).get("user_name"),
    ),
    "content": lambda record: _first(record.get("plain_text"), record.get("cleaned_data"), record.get("markdown")),
    "raw_text": lambda record: _first(
        record.get("raw_text"),
        _structured(record).get("raw_text"),
        record.get("plain_text"),
        record.get("cleaned_data"),
        record.get("markdown"),
    ),
    "HTML": lambda record: _first(record.get("HTML"), _structured(record).get("HTML"), record.get("html"), _structured(record).get("html"), record.get("markdown")),
    "article_summary": lambda record: _first(
        record.get("article_summary"),
        _structured(record).get("article_summary"),
        record.get("summary"),
        _structured(record).get("summary"),
        _metadata(record).get("description"),
    ),
    "has_infobox": _wikipedia_has_infobox,
    "infobox_structured": lambda record: _first(
        record.get("infobox_structured"),
        _structured(record).get("infobox_structured"),
        _structured(record).get("infobox"),
    ),
    "linkedin_num_id": lambda record: _first(record.get("linkedin_num_id"), _structured(record).get("linkedin_num_id"), _structured(record).get("source_id"), record.get("source_id")),
    "company_id": lambda record: _first(record.get("company_id"), _structured(record).get("company_id"), _structured(record).get("source_id"), record.get("source_id")),
    "current_company_name": lambda record: _first(
        record.get("current_company_name"),
        _structured(record).get("current_company_name"),
        record.get("current_company"),
        _structured(record).get("current_company"),
    ),
    "current_company_id": lambda record: _first(
        record.get("current_company_id"),
        _structured(record).get("current_company_id"),
    ),
    "position": lambda record: _first(
        record.get("position"),
        _structured(record).get("position"),
        _structured(record).get("headline"),
        _structured(record).get("title"),
        _metadata(record).get("headline"),
    ),
    "website": lambda record: _first(
        record.get("website"),
        _structured(record).get("website"),
        record.get("company_website"),
        _structured(record).get("company_website"),
    ),
    "specialties": lambda record: _first(
        _join_strings(_structured(record).get("specialties")),
        _join_strings(record.get("specialties")),
        record.get("specialties"),
        _structured(record).get("specialties"),
    ),
    "job_posting_id": lambda record: _first(record.get("job_posting_id"), _structured(record).get("job_posting_id"), _structured(record).get("source_id"), record.get("job_id"), record.get("source_id")),
    "job_title_standardized": lambda record: _first(
        record.get("job_title_standardized"),
        _structured(record).get("job_title_standardized"),
        ((record.get("enrichment") or {}).get("enriched_fields") or {}).get("job_title_standardized"),
        ((record.get("enrichment") or {}).get("enriched_fields") or {}).get("standardized_job_title"),
        record.get("standardized_job_title"),
    ),
    "job_summary": lambda record: _first(
        record.get("job_summary"),
        _structured(record).get("job_summary"),
        record.get("summary"),
        _structured(record).get("summary"),
        record.get("plain_text"),
    ),
    "remote_policy_detail": lambda record: _first(
        record.get("remote_policy_detail"),
        _structured(record).get("remote_policy_detail"),
        ((record.get("enrichment") or {}).get("enriched_fields") or {}).get("remote_policy_detail"),
        ((record.get("enrichment") or {}).get("enriched_fields") or {}).get("remote_policy"),
        record.get("remote_policy"),
    ),
    "post_id": _linkedin_post_id,
    "entities_mentioned": lambda record: _first(
        record.get("entities_mentioned"),
        _structured(record).get("entities_mentioned"),
        record.get("entities"),
        _structured(record).get("entities"),
        record.get("mentions"),
        _structured(record).get("mentions"),
    ),
    "page_id": lambda record: _first(record.get("page_id"), _structured(record).get("page_id"), _metadata(record).get("page_id")),
    "language": _wikipedia_language,
    "date_posted": lambda record: _first(
        record.get("date_posted"),
        _structured(record).get("date_posted"),
        record.get("review_date"),
        _structured(record).get("review_date"),
        record.get("date"),
        _structured(record).get("date"),
        record.get("posted_date"),
        _structured(record).get("posted_date"),
        _structured(record).get("published_at"),
        _metadata(record).get("date_posted"),
        _metadata(record).get("posted_date"),
        _metadata(record).get("published_at"),
        record.get("published_at"),
    ),
    "asin": lambda record: _first(record.get("asin"), _structured(record).get("asin")),
    "seller_id": _amazon_seller_id,
    "review_id": _amazon_review_id,
    "feedbacks": lambda record: _first(
        record.get("feedbacks"),
        _structured(record).get("feedbacks"),
        record.get("feedback_count"),
        _structured(record).get("feedback_count"),
    ),
    "stars": lambda record: _first(
        record.get("stars"),
        _structured(record).get("stars"),
        record.get("seller_rating"),
        _structured(record).get("seller_rating"),
    ),
    "arxiv_id": lambda record: _first(record.get("arxiv_id"), _structured(record).get("arxiv_id")),
    "DOI": lambda record: _first(record.get("DOI"), _structured(record).get("DOI"), record.get("doi"), _structured(record).get("doi")),
    "submission_comments": lambda record: _first(
        record.get("submission_comments"),
        _structured(record).get("submission_comments"),
        record.get("comment"),
        _structured(record).get("comment"),
    ),
    "submission_date": lambda record: _first(
        record.get("submission_date"),
        _structured(record).get("submission_date"),
        record.get("published"),
        _structured(record).get("published"),
    ),
    "update_date": lambda record: _first(
        record.get("update_date"),
        _structured(record).get("update_date"),
        record.get("updated"),
        _structured(record).get("updated"),
    ),
    "PDF_url": lambda record: _first(record.get("PDF_url"), _structured(record).get("PDF_url"), record.get("pdf_url"), _structured(record).get("pdf_url")),
    "num_authors": lambda record: _count_items(
        _first(record.get("authors"), _structured(record).get("authors"), _structured(record).get("authors_structured"))
    ),
    "dedup_key": lambda record: _first(
        record.get("dedup_key"),
        _structured(record).get("dedup_key"),
        _first(record.get("linkedin_num_id"), _structured(record).get("linkedin_num_id"), _structured(record).get("source_id"), record.get("source_id")),
        _first(record.get("company_id"), _structured(record).get("company_id"), _structured(record).get("source_id"), record.get("source_id")),
        _first(record.get("job_posting_id"), _structured(record).get("job_posting_id"), _structured(record).get("source_id"), record.get("job_id"), record.get("source_id")),
        _linkedin_post_id(record),
        _amazon_dedup_key(record),
        _wikipedia_dedup_key(record),
        _first(record.get("arxiv_id"), _structured(record).get("arxiv_id")),
    ),
}


FIELD_NORMALIZERS: dict[str, Callable[[Any], Any]] = {
    "specialties": _join_strings,
}


def _wikipedia_dedup_key(record: Record) -> str | None:
    wikidata_id = _first(record.get("wikidata_id"), _structured(record).get("wikidata_id"))
    if wikidata_id not in (None, ""):
        return wikidata_id
    page_id = _first(record.get("page_id"), _structured(record).get("page_id"), _metadata(record).get("page_id"))
    language = _wikipedia_language(record)
    if page_id in (None, "") or language in (None, ""):
        return None
    return f"{page_id}:{language}"
