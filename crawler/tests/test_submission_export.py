from __future__ import annotations

import json
from pathlib import Path

import pytest

from crawler.cli import main
from crawler.submission_export import build_submission_request


def test_build_submission_request_maps_canonical_record_to_platform_payload() -> None:
    record = {
        "platform": "linkedin",
        "resource_type": "company",
        "canonical_url": "https://www.linkedin.com/company/openai/",
        "plain_text": "OpenAI company profile",
        "structured": {
            "source_id": "11130470",
            "title": "OpenAI",
            "company_slug": "openai",
            "logo_url": "https://cdn.example.com/logo.png",
        },
        "crawl_timestamp": "2026-03-29T09:00:00Z",
    }

    payload = build_submission_request([record], dataset_id="ds_linkedin")

    assert payload["dataset_id"] == "ds_linkedin"
    assert payload["entries"] == [
        {
            "url": "https://www.linkedin.com/company/openai/",
            "cleaned_data": "OpenAI company profile",
            "structured_data": {
                "company_id": "11130470",
                "name": "OpenAI",
                "URL": "https://www.linkedin.com/company/openai/",
                "dedup_key": "11130470",
                "canonical_url": "https://www.linkedin.com/company/openai/",
            },
            "crawl_timestamp": "2026-03-29T09:00:00Z",
        }
    ]


def test_build_submission_request_falls_back_to_manifest_timestamp_when_record_is_missing_it() -> None:
    record = {
        "platform": "wikipedia",
        "resource_type": "article",
        "canonical_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "plain_text": "AI article",
        "metadata": {"title": "Artificial intelligence"},
        "structured": {"categories": ["Artificial intelligence"]},
        "page_id": "1164",
        "language": "en",
    }

    payload = build_submission_request(
        [record],
        dataset_id="ds_wiki",
        generated_at="2026-03-29T10:30:00Z",
    )

    assert payload["entries"][0]["crawl_timestamp"] == "2026-03-29T10:30:00Z"
    assert payload["entries"][0]["structured_data"] == {
        "URL": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "page_id": "1164",
        "title": "Artificial intelligence",
        "language": "en",
        "dedup_key": "1164:en",
        "canonical_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "categories": ["Artificial intelligence"],
    }


def test_build_submission_request_merges_enriched_fields_for_schema_properties() -> None:
    record = {
        "platform": "linkedin",
        "resource_type": "profile",
        "canonical_url": "https://www.linkedin.com/in/john-doe-ai/",
        "plain_text": "AI at Self",
        "structured": {
            "source_id": "123",
            "title": "John Doe",
            "public_identifier": "john-doe-ai",
            "headline": "AI at Self",
        },
        "enrichment": {
            "enriched_fields": {
                "engagement_rate": 0.42,
                "content_creator_tier": "rising",
                "certification_validity": "active",
            }
        },
        "crawl_timestamp": "2026-03-29T11:00:00Z",
    }

    payload = build_submission_request([record], dataset_id="ds_people")

    assert payload["entries"][0]["structured_data"] == {
        "linkedin_num_id": "123",
        "name": "John Doe",
        "URL": "https://www.linkedin.com/in/john-doe-ai/",
        "dedup_key": "123",
        "canonical_url": "https://www.linkedin.com/in/john-doe-ai/",
        "engagement_rate": 0.42,
        "content_creator_tier": "rising",
        "certification_validity": "active",
    }


@pytest.mark.parametrize(
    ("record", "expected_fields"),
    [
        pytest.param(
            {
                "platform": "linkedin",
                "resource_type": "company",
                "canonical_url": "https://www.linkedin.com/company/openai/",
                "plain_text": "OpenAI company profile",
                "structured": {
                    "source_id": "11130470",
                    "title": "OpenAI",
                },
                "enrichment": {
                    "enriched_fields": {
                        "parent_company": "OpenAI Holdings",
                        "subsidiary_tree": ["OpenAI LP", "OpenAI Startup Fund"],
                        "attrition_signal": "low",
                        "employee_growth_trend": "accelerating",
                        "hiring_velocity": "high",
                        "department_distribution_estimated": {"engineering": 0.62, "research": 0.21},
                        "tech_stack_inferred": ["Python", "Kubernetes"],
                        "engineering_team_size_estimated": 650,
                        "revenue_range_estimated": "$1B-$10B",
                    }
                },
                "crawl_timestamp": "2026-04-01T09:00:00Z",
            },
            {
                "company_id": "11130470",
                "name": "OpenAI",
                "dedup_key": "11130470",
                "canonical_url": "https://www.linkedin.com/company/openai/",
                "parent_company": "OpenAI Holdings",
                "subsidiary_tree": ["OpenAI LP", "OpenAI Startup Fund"],
                "attrition_signal": "low",
                "employee_growth_trend": "accelerating",
                "hiring_velocity": "high",
                "department_distribution_estimated": {"engineering": 0.62, "research": 0.21},
                "tech_stack_inferred": ["Python", "Kubernetes"],
                "engineering_team_size_estimated": 650,
                "revenue_range_estimated": "$1B-$10B",
            },
            id="linkedin-company-second-batch-fields",
        ),
        pytest.param(
            {
                "platform": "linkedin",
                "resource_type": "job",
                "canonical_url": "https://www.linkedin.com/jobs/view/1234567890",
                "plain_text": "Staff AI Engineer role",
                "structured": {
                    "source_id": "1234567890",
                    "title": "Staff AI Engineer",
                    "company_name": "OpenAI",
                    "published_at": "2026-03-20",
                },
                "enrichment": {
                    "enriched_fields": {
                        "remote_policy": "hybrid",
                        "days_to_fill_estimated": 28,
                    }
                },
                "crawl_timestamp": "2026-04-01T09:05:00Z",
            },
            {
                "job_posting_id": "1234567890",
                "job_title": "Staff AI Engineer",
                "company_name": "OpenAI",
                "dedup_key": "1234567890",
                "canonical_url": "https://www.linkedin.com/jobs/view/1234567890",
                "date_posted": "2026-03-20",
                "remote_policy": "hybrid",
                "days_to_fill_estimated": 28,
            },
            id="linkedin-jobs-second-batch-fields",
        ),
        pytest.param(
            {
                "platform": "amazon",
                "resource_type": "product",
                "canonical_url": "https://www.amazon.com/dp/B000TEST01",
                "plain_text": "Keychron K3 wireless keyboard",
                "structured": {
                    "asin": "B000TEST01",
                    "title": "Keychron K3 Wireless Keyboard",
                    "marketplace": "US",
                },
                "enrichment": {
                    "enriched_fields": {
                        "estimated_monthly_sales": 12000,
                        "fake_review_risk_score": 0.14,
                        "historical_price_trend": "stable",
                        "price_vs_category_avg": -0.08,
                        "rating_trend": "up",
                        "review_velocity": "high",
                        "verified_purchase_ratio": 0.87,
                    }
                },
                "crawl_timestamp": "2026-04-01T09:10:00Z",
            },
            {
                "asin": "B000TEST01",
                "title": "Keychron K3 Wireless Keyboard",
                "dedup_key": "B000TEST01:US",
                "canonical_url": "https://www.amazon.com/dp/B000TEST01",
                "estimated_monthly_sales": 12000,
                "fake_review_risk_score": 0.14,
                "historical_price_trend": "stable",
                "price_vs_category_avg": -0.08,
                "rating_trend": "up",
                "review_velocity": "high",
                "verified_purchase_ratio": 0.87,
            },
            id="amazon-products-second-batch-fields",
        ),
        pytest.param(
            {
                "platform": "arxiv",
                "resource_type": "paper",
                "canonical_url": "https://arxiv.org/abs/2401.12345",
                "plain_text": "A paper about transformers",
                "structured": {
                    "arxiv_id": "2401.12345",
                    "title": "Transformers at Scale",
                },
                "enrichment": {
                    "enriched_fields": {
                        "influential_citation_count": 91,
                        "total_citation_count": 314,
                        "venue_published": "NeurIPS 2025",
                        "venue_tier": "A*",
                    }
                },
                "crawl_timestamp": "2026-04-01T09:15:00Z",
            },
            {
                "arxiv_id": "2401.12345",
                "title": "Transformers at Scale",
                "dedup_key": "2401.12345",
                "canonical_url": "https://arxiv.org/abs/2401.12345",
                "influential_citation_count": 91,
                "total_citation_count": 314,
                "venue_published": "NeurIPS 2025",
                "venue_tier": "A*",
            },
            id="arxiv-second-batch-fields",
        ),
        pytest.param(
            {
                "platform": "wikipedia",
                "resource_type": "article",
                "canonical_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
                "plain_text": "Artificial intelligence article",
                "metadata": {"title": "Artificial intelligence"},
                "structured": {
                    "categories": ["Artificial intelligence"],
                },
                "page_id": "1164",
                "language": "en",
                "enrichment": {
                    "enriched_fields": {
                        "article_quality_class": "GA",
                        "citation_density": 3.4,
                        "edit_controversy_score": 0.18,
                        "last_major_edit": "2026-03-30T10:15:00Z",
                        "neutrality_score": 0.93,
                    }
                },
                "crawl_timestamp": "2026-04-01T09:20:00Z",
            },
            {
                "page_id": "1164",
                "title": "Artificial intelligence",
                "language": "en",
                "dedup_key": "1164:en",
                "canonical_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
                "article_quality_class": "GA",
                "citation_density": 3.4,
                "edit_controversy_score": 0.18,
                "last_major_edit": "2026-03-30T10:15:00Z",
                "neutrality_score": 0.93,
            },
            id="wikipedia-second-batch-fields",
        ),
        pytest.param(
            {
                "platform": "linkedin",
                "resource_type": "post",
                "canonical_url": "https://www.linkedin.com/feed/update/urn:li:activity:9876543210",
                "plain_text": "Announcing a new reasoning model.",
                "structured": {
                    "post_id": "9876543210",
                    "post_text": "Announcing a new reasoning model.",
                    "date_posted": "2026-04-01",
                },
                "enrichment": {
                    "enriched_fields": {
                        "viral_coefficient_estimated": 1.8,
                    }
                },
                "crawl_timestamp": "2026-04-01T09:25:00Z",
            },
            {
                "post_id": "9876543210",
                "post_text": "Announcing a new reasoning model.",
                "dedup_key": "9876543210",
                "canonical_url": "https://www.linkedin.com/feed/update/urn:li:activity:9876543210",
                "viral_coefficient_estimated": 1.8,
            },
            id="linkedin-posts-remaining-field",
        ),
        pytest.param(
            {
                "platform": "amazon",
                "resource_type": "seller",
                "canonical_url": "https://www.amazon.com/sp?seller=ABC123XYZ",
                "plain_text": "Keychron Official seller page",
                "structured": {
                    "seller_id": "ABC123XYZ",
                    "seller_name": "Keychron Official",
                    "marketplace": "US",
                },
                "enrichment": {
                    "enriched_fields": {
                        "avg_product_rating": 4.7,
                        "brand_portfolio": ["Keychron", "Lemokey"],
                        "growth_trajectory": "growing",
                        "product_count": 124,
                    }
                },
                "crawl_timestamp": "2026-04-01T09:30:00Z",
            },
            {
                "seller_id": "ABC123XYZ",
                "seller_name": "Keychron Official",
                "dedup_key": "ABC123XYZ:US",
                "canonical_url": "https://www.amazon.com/sp?seller=ABC123XYZ",
                "avg_product_rating": 4.7,
                "brand_portfolio": ["Keychron", "Lemokey"],
                "growth_trajectory": "growing",
                "product_count": 124,
            },
            id="amazon-sellers-remaining-fields",
        ),
        pytest.param(
            {
                "platform": "amazon",
                "resource_type": "review",
                "canonical_url": "https://www.amazon.com/gp/customer-reviews/R1234567890",
                "plain_text": "Great keyboard for travel.",
                "structured": {
                    "review_id": "R1234567890",
                    "asin": "B000TEST01",
                    "author_name": "Alice",
                    "review_text": "Great keyboard for travel.",
                    "marketplace": "US",
                },
                "enrichment": {
                    "enriched_fields": {
                        "review_quality_score": 0.91,
                        "review_one_liner": "Compact keyboard with strong travel feel.",
                    }
                },
                "crawl_timestamp": "2026-04-01T09:35:00Z",
            },
            {
                "review_id": "R1234567890",
                "asin": "B000TEST01",
                "author_name": "Alice",
                "review_text": "Great keyboard for travel.",
                "dedup_key": "R1234567890:US",
                "canonical_url": "https://www.amazon.com/gp/customer-reviews/R1234567890",
                "review_quality_score": 0.91,
                "review_one_liner": "Compact keyboard with strong travel feel.",
            },
            id="amazon-reviews-dedup-and-export-verification",
        ),
    ],
)
def test_build_submission_request_aligns_second_batch_schema_fields(
    record: dict[str, object],
    expected_fields: dict[str, object],
) -> None:
    payload = build_submission_request([record], dataset_id="ds_alignment")

    structured_data = payload["entries"][0]["structured_data"]
    for field_name, expected_value in expected_fields.items():
        assert structured_data[field_name] == expected_value


def test_export_submissions_command_writes_payload_json(workspace_tmp_path: Path) -> None:
    records_path = workspace_tmp_path / "records.jsonl"
    output_path = workspace_tmp_path / "submissions.json"
    records_path.write_text(
        json.dumps(
            {
                "platform": "linkedin",
                "resource_type": "profile",
                "canonical_url": "https://www.linkedin.com/in/john-doe-ai/",
                "plain_text": "AI at Self",
                "structured": {"source_id": "123", "public_identifier": "john-doe-ai", "title": "John Doe"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "export-submissions",
            "--input",
            str(records_path),
            "--dataset-id",
            "ds_people",
            "--generated-at",
            "2026-03-29T11:00:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["dataset_id"] == "ds_people"
    assert payload["entries"][0]["url"] == "https://www.linkedin.com/in/john-doe-ai/"
    assert payload["entries"][0]["cleaned_data"] == "AI at Self"
    assert payload["entries"][0]["crawl_timestamp"] == "2026-03-29T11:00:00Z"
    assert payload["entries"][0]["structured_data"]["linkedin_num_id"] == "123"
