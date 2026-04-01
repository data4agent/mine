from __future__ import annotations

from crawler.schema_contract import flatten_record_for_schema, get_schema_contract


def test_get_schema_contract_resolves_schema_by_platform_and_resource_type() -> None:
    contract = get_schema_contract({"platform": "linkedin", "resource_type": "profile"})

    assert contract.dataset_name == "linkedin_profiles"
    assert "linkedin_num_id" in contract.property_names
    assert "engagement_rate" in contract.property_names


def test_flatten_record_for_schema_resolves_required_and_enriched_fields() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "linkedin",
            "resource_type": "profile",
            "canonical_url": "https://www.linkedin.com/in/john-doe-ai/",
            "plain_text": "AI at Self",
            "structured": {
                "source_id": "123",
                "title": "John Doe",
                "public_identifier": "john-doe-ai",
            },
            "metadata": {
                "title": "John Doe",
            },
            "enrichment": {
                "enriched_fields": {
                    "engagement_rate": 0.42,
                    "content_creator_tier": "rising",
                    "certification_validity": "active",
                }
            },
        }
    )

    assert structured_data["linkedin_num_id"] == "123"
    assert structured_data["name"] == "John Doe"
    assert structured_data["URL"] == "https://www.linkedin.com/in/john-doe-ai/"
    assert structured_data["dedup_key"] == "123"
    assert structured_data["canonical_url"] == "https://www.linkedin.com/in/john-doe-ai/"
    assert structured_data["engagement_rate"] == 0.42
    assert structured_data["content_creator_tier"] == "rising"
    assert structured_data["certification_validity"] == "active"


def test_flatten_record_for_schema_uses_top_level_and_metadata_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "wikipedia",
            "resource_type": "article",
            "canonical_url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "plain_text": "Artificial intelligence article body",
            "metadata": {"title": "Artificial intelligence"},
            "structured": {"categories": ["Artificial intelligence"]},
            "page_id": "1164",
            "language": "en",
        }
    )

    assert structured_data["page_id"] == "1164"
    assert structured_data["title"] == "Artificial intelligence"
    assert structured_data["language"] == "en"
    assert structured_data["dedup_key"] == "1164:en"
    assert structured_data["canonical_url"] == "https://en.wikipedia.org/wiki/Artificial_intelligence"


def test_flatten_record_for_schema_maps_linkedin_job_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "linkedin",
            "resource_type": "job",
            "canonical_url": "https://www.linkedin.com/jobs/view/1234567890",
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
        }
    )

    assert structured_data["job_posting_id"] == "1234567890"
    assert structured_data["job_title"] == "Staff AI Engineer"
    assert structured_data["company_name"] == "OpenAI"
    assert structured_data["date_posted"] == "2026-03-20"
    assert structured_data["remote_policy"] == "hybrid"
    assert structured_data["days_to_fill_estimated"] == 28


def test_flatten_record_for_schema_maps_linkedin_post_url_and_plain_text_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "linkedin",
            "resource_type": "post",
            "canonical_url": "https://www.linkedin.com/feed/update/urn:li:activity:9876543210",
            "activity_urn": "urn:li:activity:9876543210",
            "plain_text": "Announcing a new reasoning model.",
            "enrichment": {
                "enriched_fields": {
                    "viral_coefficient_estimated": 1.8,
                }
            },
        }
    )

    assert structured_data["post_id"] == "9876543210"
    assert structured_data["post_text"] == "Announcing a new reasoning model."
    assert structured_data["dedup_key"] == "9876543210"
    assert structured_data["viral_coefficient_estimated"] == 1.8


def test_flatten_record_for_schema_maps_amazon_seller_aliases_and_dedup() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "amazon",
            "resource_type": "seller",
            "canonical_url": "https://www.amazon.com/sp?seller=ABC123XYZ",
            "name": "Keychron Official",
            "marketplace": "US",
            "enrichment": {
                "enriched_fields": {
                    "avg_product_rating": 4.7,
                    "brand_portfolio": ["Keychron", "Lemokey"],
                }
            },
        }
    )

    assert structured_data["seller_id"] == "ABC123XYZ"
    assert structured_data["seller_name"] == "Keychron Official"
    assert structured_data["dedup_key"] == "ABC123XYZ:US"
    assert structured_data["avg_product_rating"] == 4.7
    assert structured_data["brand_portfolio"] == ["Keychron", "Lemokey"]


def test_flatten_record_for_schema_maps_amazon_review_aliases_and_dedup() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "amazon",
            "resource_type": "review",
            "canonical_url": "https://www.amazon.com/gp/customer-reviews/R1234567890",
            "asin": "B000TEST01",
            "author": "Alice",
            "plain_text": "Great keyboard for travel.",
            "marketplace": "US",
            "enrichment": {
                "enriched_fields": {
                    "review_quality_score": 0.91,
                    "review_one_liner": "Compact keyboard with strong travel feel.",
                }
            },
        }
    )

    assert structured_data["review_id"] == "R1234567890"
    assert structured_data["author_name"] == "Alice"
    assert structured_data["review_text"] == "Great keyboard for travel."
    assert structured_data["dedup_key"] == "R1234567890:US"
    assert structured_data["review_quality_score"] == 0.91
