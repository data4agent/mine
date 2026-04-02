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


def test_flatten_record_for_schema_maps_wikipedia_content_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "wikipedia",
            "resource_type": "article",
            "canonical_url": "https://en.wikipedia.org/wiki/OpenAI",
            "plain_text": "OpenAI article body",
            "markdown": "# OpenAI",
            "metadata": {
                "title": "OpenAI",
                "description": "OpenAI is an AI research organization.",
                "pageprops": {"infobox": ""},
            },
            "structured": {
                "page_id": "48795986",
                "infobox": {"industry": "Artificial intelligence"},
            },
        }
    )

    assert structured_data["raw_text"] == "OpenAI article body"
    assert structured_data["HTML"] == "# OpenAI"
    assert structured_data["article_summary"] == "OpenAI is an AI research organization."
    assert structured_data["has_infobox"] is True
    assert structured_data["infobox_structured"] == {"industry": "Artificial intelligence"}


def test_flatten_record_for_schema_maps_wikipedia_extended_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "wikipedia",
            "resource_type": "article",
            "canonical_url": "https://en.wikipedia.org/wiki/OpenAI",
            "plain_text": "OpenAI article body with useful references",
            "structured": {
                "page_id": "48795986",
                "article_creation_date": "2015-12-11T00:00:00Z",
                "protection_level": "sysop",
                "references_count": 12,
                "external_links_count": 4,
                "references": ["https://openai.com/blog"],
                "see_also": ["Artificial general intelligence"],
                "images": ["https://en.wikipedia.org/wiki/Special:FilePath/OpenAI.png"],
                "word_count": 1200,
                "number_of_sections": 8,
                "infobox_raw": "industry=Artificial intelligence",
            },
        }
    )

    assert structured_data["article_creation_date"] == "2015-12-11T00:00:00Z"
    assert structured_data["protection_level"] == "sysop"
    assert structured_data["references_count"] == 12
    assert structured_data["external_links_count"] == 4
    assert structured_data["references"] == ["https://openai.com/blog"]
    assert structured_data["see_also"] == ["Artificial general intelligence"]
    assert structured_data["images"] == ["https://en.wikipedia.org/wiki/Special:FilePath/OpenAI.png"]
    assert structured_data["word_count"] == 1200
    assert structured_data["number_of_sections"] == 8
    assert structured_data["infobox_raw"] == "industry=Artificial intelligence"


def test_flatten_record_for_schema_maps_arxiv_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "arxiv",
            "resource_type": "paper",
            "canonical_url": "https://arxiv.org/abs/2303.08774",
            "plain_text": "Full paper text",
            "structured": {
                "doi": "10.48550/arXiv.2303.08774",
                "published": "2023-03-15",
                "updated": "2023-03-27",
                "pdf_url": "https://arxiv.org/pdf/2303.08774.pdf",
                "dataset_url": "https://example.com/dataset",
                "authors": ["OpenAI", "Josh Achiam"],
            },
        }
    )

    assert structured_data["raw_text"] == "Full paper text"
    assert structured_data["DOI"] == "10.48550/arXiv.2303.08774"
    assert structured_data["submission_date"] == "2023-03-15"
    assert structured_data["update_date"] == "2023-03-27"
    assert structured_data["PDF_url"] == "https://arxiv.org/pdf/2303.08774.pdf"
    assert structured_data["dataset_url"] == "https://example.com/dataset"
    assert structured_data["num_authors"] == 2


def test_flatten_record_for_schema_maps_arxiv_extended_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "arxiv",
            "resource_type": "paper",
            "canonical_url": "https://arxiv.org/abs/2303.08774",
            "structured": {
                "comment": "Accepted to internal review.",
                "journal_ref": "arXiv preprint",
                "license": "http://creativecommons.org/licenses/by/4.0/",
                "references": ["Attention Is All You Need"],
                "page_count": 12,
            },
        }
    )

    assert structured_data["submission_comments"] == "Accepted to internal review."
    assert structured_data["journal_ref"] == "arXiv preprint"
    assert structured_data["license"] == "http://creativecommons.org/licenses/by/4.0/"
    assert structured_data["references"] == ["Attention Is All You Need"]
    assert structured_data["page_count"] == 12


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


def test_flatten_record_for_schema_maps_linkedin_profile_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "linkedin",
            "resource_type": "profile",
            "canonical_url": "https://www.linkedin.com/in/john-doe-ai/",
            "plain_text": "Builder and researcher",
            "structured": {
                "source_id": "123",
                "headline": "Staff Research Engineer at OpenAI",
                "about_summary": "Works on evaluation systems.",
                "current_company": "OpenAI",
                "current_company_id": "openai",
            },
        }
    )

    assert structured_data["ID"] == "123"
    assert structured_data["about"] == "Works on evaluation systems."
    assert structured_data["position"] == "Staff Research Engineer at OpenAI"
    assert structured_data["current_company_name"] == "OpenAI"
    assert structured_data["current_company_id"] == "openai"


def test_flatten_record_for_schema_maps_linkedin_company_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "linkedin",
            "resource_type": "company",
            "canonical_url": "https://www.linkedin.com/company/openai/",
            "structured": {
                "source_id": "1441",
                "description": "AI research and deployment company.",
                "company_website": "https://openai.com",
                "specialties": ["Artificial Intelligence", "Research"],
            },
        }
    )

    assert structured_data["ID"] == "1441"
    assert structured_data["company_id"] == "1441"
    assert structured_data["about"] == "AI research and deployment company."
    assert structured_data["website"] == "https://openai.com"
    assert structured_data["specialties"] == "Artificial Intelligence, Research"


def test_flatten_record_for_schema_maps_linkedin_company_direct_and_derived_fields() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "linkedin",
            "resource_type": "company",
            "canonical_url": "https://www.linkedin.com/company/openai/",
            "structured": {
                "source_id": "11130470",
                "title": "OpenAI",
                "country_code": "US",
                "company_type": "private",
                "company_size_range": "1001-5000 employees",
                "top_topics": ["ai", "machinelearning", "openai"],
                "funding_stage_inferred": "secondary_market",
                "tech_stack_mentioned_in_about": ["AI", "machine learning"],
                "linkable_identifiers": {
                    "website_domain": "openai.com",
                    "crunchbase_hint": "https://www.crunchbase.com/organization/openai",
                },
                "company_stage_signals": {
                    "stage_inferred": "late_stage",
                    "confidence": 0.79,
                    "evidence_phrases": ["SECONDARY_MARKET", "11 funding rounds"],
                },
            },
        }
    )

    assert structured_data["country_code"] == "US"
    assert structured_data["company_type"] == "private"
    assert structured_data["company_size_range"] == "1001-5000 employees"
    assert structured_data["top_topics"] == ["ai", "machinelearning", "openai"]
    assert structured_data["funding_stage_inferred"] == "secondary_market"
    assert structured_data["tech_stack_mentioned_in_about"] == ["AI", "machine learning"]
    assert structured_data["linkable_identifiers"] == {
        "website_domain": "openai.com",
        "crunchbase_hint": "https://www.crunchbase.com/organization/openai",
    }
    assert structured_data["company_stage_signals"] == {
        "stage_inferred": "late_stage",
        "confidence": 0.79,
        "evidence_phrases": ["SECONDARY_MARKET", "11 funding rounds"],
    }


def test_flatten_record_for_schema_maps_linkedin_job_standardized_aliases() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "linkedin",
            "resource_type": "job",
            "canonical_url": "https://www.linkedin.com/jobs/view/1234567890",
            "plain_text": "Build eval systems for frontier models.",
            "structured": {
                "source_id": "1234567890",
                "summary": "Lead model evaluation work.",
            },
            "enrichment": {
                "enriched_fields": {
                    "standardized_job_title": "Research Engineer",
                    "remote_policy": "hybrid",
                }
            },
        }
    )

    assert structured_data["job_title_standardized"] == "Research Engineer"
    assert structured_data["job_summary"] == "Lead model evaluation work."
    assert structured_data["remote_policy_detail"] == "hybrid"


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


def test_flatten_record_for_schema_maps_linkedin_post_entities_alias() -> None:
    structured_data = flatten_record_for_schema(
        {
            "platform": "linkedin",
            "resource_type": "post",
            "canonical_url": "https://www.linkedin.com/feed/update/urn:li:activity:9876543210",
            "structured": {
                "entities": ["OpenAI", "GPT-5.4"],
            },
        }
    )

    assert structured_data["entities_mentioned"] == ["OpenAI", "GPT-5.4"]


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


def test_linkedin_posts_schema_uses_number_for_trending_topic_relevance() -> None:
    contract = get_schema_contract({"platform": "linkedin", "resource_type": "post"})

    assert contract.schema["properties"]["trending_topic_relevance"]["type"] == ["number", "null"]


def test_amazon_sellers_schema_uses_number_for_dispute_rate_estimated() -> None:
    contract = get_schema_contract({"platform": "amazon", "resource_type": "seller"})

    assert contract.schema["properties"]["dispute_rate_estimated"]["type"] == ["number", "null"]
