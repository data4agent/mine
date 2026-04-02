from __future__ import annotations

import json
from pathlib import Path

import httpx

from crawler.platforms import arxiv, linkedin, wikipedia
from crawler.platforms.base import hook_normalizer
from crawler.platforms.registry import get_platform_adapter
from crawler.platforms.registry import list_platform_adapters


def test_wikipedia_adapter_declares_article_support() -> None:
    adapter = get_platform_adapter("wikipedia")
    assert adapter.platform == "wikipedia"
    assert "article" in adapter.supported_resource_types
    assert adapter.default_backend == "api"


def test_wikipedia_extract_includes_page_id_in_metadata() -> None:
    extracted = wikipedia._extract_wikipedia(
        {"platform": "wikipedia", "resource_type": "article", "title": "Artificial intelligence"},
        {
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "content_type": "application/json",
            "json_data": {
                "query": {
                    "pages": {
                        "1164": {
                            "pageid": 1164,
                            "title": "Artificial intelligence",
                            "extract": "Artificial intelligence is the capability of computational systems.",
                            "categories": [{"title": "Category:Artificial intelligence"}],
                            "pageprops": {"wikibase-shortdesc": "Intelligence of machines"},
                        }
                    }
                }
            },
        },
    )

    assert extracted["metadata"]["page_id"] == "1164"


def test_wikipedia_extract_includes_extended_article_metadata() -> None:
    extracted = wikipedia._extract_wikipedia(
        {"platform": "wikipedia", "resource_type": "article", "title": "Artificial intelligence"},
        {
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "content_type": "application/json",
            "parse_json_data": {
                "parse": {
                    "text": {
                        "*": """
                            <div class="mw-parser-output">
                              <table class="wikitable">
                                <caption>Milestones</caption>
                                <tr><th>Year</th><th>Event</th></tr>
                                <tr><td>1956</td><td>Dartmouth workshop</td></tr>
                              </table>
                            </div>
                        """
                    }
                }
            },
            "html_fallback_text": """
                <html><body>
                  <table class="infobox"><tr><th>Industry</th><td>Artificial intelligence</td></tr></table>
                </body></html>
            """,
            "json_data": {
                "query": {
                    "pages": {
                        "1164": {
                            "pageid": 1164,
                            "title": "Artificial intelligence",
                            "fullurl": "https://en.wikipedia.org/wiki/Artificial_intelligence",
                            "touched": "2026-04-02T08:00:00Z",
                            "extract": "Lead section.\n\n== History ==\n\nMore details here.",
                            "categories": [
                                {"title": "Category:Artificial intelligence"},
                                {"title": "Category:Good articles"},
                                {"title": "Category:All articles with unsourced statements"},
                            ],
                            "pageprops": {
                                "wikibase-shortdesc": "Intelligence of machines",
                                "wikibase_item": "Q11660",
                            },
                            "protection": [{"type": "edit", "level": "sysop"}],
                            "images": [{"title": "File:AI.png"}],
                            "extlinks": [
                                {"*": "https://openai.com/research"},
                                {"*": "https://www.nytimes.com/2024/01/01/technology/ai.html"},
                                {"*": "https://arxiv.org/abs/1706.03762"},
                                {"*": "https://www.nasa.gov/ai/"},
                            ],
                            "links": [{"title": "History of AI"}, {"title": "See also"}],
                            "langlinks": [
                                {"lang": "zh", "*": "人工智能", "url": "https://zh.wikipedia.org/wiki/%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD"},
                                {"lang": "fr", "*": "Intelligence artificielle", "url": "https://fr.wikipedia.org/wiki/Intelligence_artificielle"},
                            ],
                            "revisions": [
                                {
                                    "timestamp": "2001-01-15T00:00:00Z",
                                    "slots": {
                                        "main": {
                                            "*": """{{Infobox technology
| name = Artificial intelligence
| field = Computer science
}}
Lead section.
<ref>Primary source</ref>

== See also ==
* [[Machine learning]]
* [[Neural network]]
"""
                                        }
                                    },
                                }
                            ],
                        }
                    }
                }
            },
        },
    )

    assert extracted["structured"]["article_creation_date"] == "2001-01-15T00:00:00Z"
    assert extracted["structured"]["protection_level"] == "fully-protected"
    assert extracted["structured"]["references"] == [
        "https://openai.com/research",
        "https://www.nytimes.com/2024/01/01/technology/ai.html",
        "https://arxiv.org/abs/1706.03762",
        "https://www.nasa.gov/ai/",
    ]
    assert extracted["structured"]["references_count"] == 1
    assert extracted["structured"]["external_links_count"] == 4
    assert extracted["structured"]["images"] == ["https://en.wikipedia.org/wiki/Special:FilePath/AI.png"]
    assert extracted["structured"]["number_of_sections"] == 2
    assert extracted["structured"]["word_count"] >= 4
    assert extracted["structured"]["title_disambiguated"] is None
    assert extracted["structured"]["canonical_entity_name"] == "Artificial intelligence"
    assert extracted["structured"]["wikidata_id"] == "Q11660"
    assert extracted["structured"]["article_summary"] == "Lead section."
    assert extracted["structured"]["categories_cleaned"] == ["Artificial intelligence"]
    assert extracted["structured"]["citation_density"] == 0.1667
    assert extracted["structured"]["last_major_edit"] == "2026-04-02T08:00:00Z"
    assert extracted["structured"]["article_quality_class"] == "good_article"
    assert extracted["structured"]["domain"] == "artificial_intelligence"
    assert extracted["structured"]["topic_hierarchy"] == ["artificial_intelligence", "technology"]
    assert extracted["structured"]["subject_tags"] == ["Artificial intelligence"]
    assert extracted["structured"]["external_links_classified"] == [
        {"url": "https://openai.com/research", "source_type": "other", "reliability_tier": "medium"},
        {"url": "https://www.nytimes.com/2024/01/01/technology/ai.html", "source_type": "news", "reliability_tier": "medium"},
        {"url": "https://arxiv.org/abs/1706.03762", "source_type": "academic", "reliability_tier": "high"},
        {"url": "https://www.nasa.gov/ai/", "source_type": "government", "reliability_tier": "high"},
    ]
    assert extracted["structured"]["table_of_contents"] == ["History"]
    assert extracted["structured"]["sections_structured"] == [
        {
            "heading": "History",
            "content": "More details here.",
            "section_type": "history",
        }
    ]
    assert extracted["structured"]["tables_structured"] == [
        {
            "table_title": "Milestones",
            "headers": ["Year", "Event"],
            "rows": [["1956", "Dartmouth workshop"]],
            "table_topic": "Milestones",
            "data_type": "table",
        }
    ]
    assert extracted["structured"]["cross_language_links"] == {
        "zh": "https://zh.wikipedia.org/wiki/%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD",
        "fr": "https://fr.wikipedia.org/wiki/Intelligence_artificielle",
    }
    assert extracted["structured"]["entity_name_translations"] == {
        "zh": "人工智能",
        "fr": "Intelligence artificielle",
    }
    assert extracted["structured"]["infobox_raw"].startswith("{{Infobox technology")
    assert extracted["structured"]["infobox_structured"] == {
        "name": "Artificial intelligence",
        "field": "Computer science",
    }
    assert extracted["structured"]["see_also"] == ["Machine learning", "Neural network"]
    assert "Artificial intelligence" in extracted["structured"]["infobox_raw"]


def test_wikipedia_extract_defaults_unprotected_level_when_page_has_no_restrictions() -> None:
    extracted = wikipedia._extract_wikipedia(
        {"platform": "wikipedia", "resource_type": "article", "title": "OpenAI"},
        {
            "url": "https://en.wikipedia.org/wiki/OpenAI",
            "content_type": "application/json",
            "json_data": {
                "query": {
                    "pages": {
                        "1": {
                            "pageid": 1,
                            "title": "OpenAI",
                            "extract": "OpenAI is an AI research organization.",
                            "categories": [],
                            "pageprops": {},
                            "protection": [],
                        }
                    }
                }
            },
        },
    )

    assert extracted["structured"]["protection_level"] == "unprotected"


def test_wikipedia_extract_parses_disambiguated_titles() -> None:
    extracted = wikipedia._extract_wikipedia(
        {"platform": "wikipedia", "resource_type": "article", "title": "Mercury (element)"},
        {
            "url": "https://en.wikipedia.org/wiki/Mercury_(element)",
            "content_type": "application/json",
            "json_data": {
                "query": {
                    "pages": {
                        "1": {
                            "pageid": 1,
                            "title": "Mercury (element)",
                            "extract": "Mercury is a chemical element.",
                            "categories": [],
                            "pageprops": {},
                        }
                    }
                }
            },
        },
    )

    assert extracted["structured"]["title_disambiguated"] == "Mercury (element)"
    assert extracted["structured"]["canonical_entity_name"] == "Mercury"


def test_arxiv_extract_parses_extended_metadata() -> None:
    extracted = arxiv._extract_arxiv(
        {"platform": "arxiv", "resource_type": "paper", "arxiv_id": "2303.08774"},
        {
            "url": "https://arxiv.org/abs/2303.08774",
            "content_type": "application/atom+xml",
            "html_fallback_text": """
                <html><body>
                  <div class=\"submission-history\">
                    <a href=\"/abs/2303.08774v1\">v1</a>
                    <a href=\"/abs/2303.08774v2\">v2</a>
                  </div>
                  <td class=\"comments\">15 pages, 5 figures</td>
                  <a href=\"https://doi.org/10.48550/arXiv.2303.08774\">doi</a>
                  <a href=\"https://arxiv.org/pdf/2303.08774.pdf\">pdf</a>
                  <a href=\"http://arxiv.org/licenses/nonexclusive-distrib/1.0/\">license</a>
                </body></html>
            """,
            "text": """
                <feed xmlns=\"http://www.w3.org/2005/Atom\"
                      xmlns:arxiv=\"http://arxiv.org/schemas/atom\">
                  <title>ArXiv Query: id_list=2303.08774</title>
                  <entry>
                    <id>http://arxiv.org/abs/2303.08774v2</id>
                    <updated>2023-03-27T17:37:50Z</updated>
                    <published>2023-03-15T22:56:50Z</published>
                    <title> GPT-4 Technical Report </title>
                    <summary> We report the development of GPT-4. </summary>
                    <author><name>OpenAI</name></author>
                    <author><name>Josh Achiam</name></author>
                    <arxiv:doi>10.48550/arXiv.2303.08774</arxiv:doi>
                    <arxiv:comment>Accepted to internal review.</arxiv:comment>
                    <arxiv:journal_ref>arXiv preprint</arxiv:journal_ref>
                    <arxiv:primary_category term=\"cs.CL\" />
                    <category term=\"cs.CL\" />
                    <category term=\"cs.AI\" />
                    <link rel=\"alternate\" href=\"https://arxiv.org/abs/2303.08774v2\" />
                    <link title=\"pdf\" href=\"https://arxiv.org/pdf/2303.08774.pdf\" />
                    <rights>http://creativecommons.org/licenses/by/4.0/</rights>
                  </entry>
                </feed>
            """,
        },
    )

    assert extracted["structured"]["arxiv_id"] == "2303.08774"
    assert extracted["structured"]["doi"] == "10.48550/arXiv.2303.08774"
    assert extracted["structured"]["published"] == "2023-03-15"
    assert extracted["structured"]["updated"] == "2023-03-27"
    assert extracted["structured"]["comment"] == "Accepted to internal review."
    assert extracted["structured"]["journal_ref"] == "arXiv preprint"
    assert extracted["structured"]["primary_category"] == "cs.CL"
    assert extracted["structured"]["categories"] == ["cs.CL", "cs.AI"]
    assert extracted["structured"]["pdf_url"] == "https://arxiv.org/pdf/2303.08774.pdf"
    assert extracted["structured"]["license"] == "http://creativecommons.org/licenses/by/4.0/"
    assert extracted["structured"]["versions"] == ["v1", "v2"]
    assert extracted["structured"]["versions"] == ["v1", "v2"]
    assert extracted["structured"]["num_figures"] == 5


def test_wikipedia_normalizer_maps_page_id_for_submission_schema() -> None:
    normalizer = hook_normalizer("wikipedia")

    normalized = normalizer(
        {"platform": "wikipedia", "resource_type": "article", "title": "Artificial intelligence"},
        {"fields": {"title": "Artificial_intelligence"}},
        {
            "metadata": {
                "title": "Artificial intelligence",
                "page_id": "1164",
            },
            "plain_text": "Artificial intelligence is the capability of computational systems.",
        },
        {},
    )

    assert normalized["title"] == "Artificial intelligence"
    assert normalized["page_id"] == "1164"


def test_wikipedia_normalizer_preserves_extended_article_fields() -> None:
    normalizer = hook_normalizer("wikipedia")

    normalized = normalizer(
        {"platform": "wikipedia", "resource_type": "article", "title": "Artificial intelligence"},
        {"canonical_url": "https://en.wikipedia.org/wiki/Artificial_intelligence", "fields": {"title": "Artificial_intelligence"}},
        {
            "metadata": {
                "title": "Artificial intelligence",
                "page_id": "1164",
            },
            "plain_text": "Lead section.\n\n== History ==\n\nMore details here.",
            "markdown": "# Artificial intelligence",
            "structured": {
                "categories": ["Artificial intelligence"],
                "article_creation_date": "2001-01-15T00:00:00Z",
                "protection_level": "fully-protected",
                "references": ["https://openai.com/research"],
                "references_count": 1,
                "external_links_count": 1,
                "images": ["https://en.wikipedia.org/wiki/Special:FilePath/AI.png"],
                "word_count": 6,
                "number_of_sections": 2,
                "has_infobox": True,
                "infobox_raw": "industry=AI",
                "wikidata_id": "Q11660",
                "article_summary": "Lead section.",
                "categories_cleaned": ["Artificial intelligence"],
                "citation_density": 0.1667,
                "last_major_edit": "2026-04-02T08:00:00Z",
                "article_quality_class": "good_article",
                "domain": "artificial_intelligence",
                "topic_hierarchy": ["artificial_intelligence", "technology"],
                "subject_tags": ["Artificial intelligence"],
                "external_links_classified": [
                    {"url": "https://openai.com/research", "source_type": "other", "reliability_tier": "medium"},
                ],
                "table_of_contents": ["History"],
                "sections_structured": [{"heading": "History", "content": "More details here.", "section_type": "history"}],
                "tables_structured": [{"table_title": "Milestones", "headers": ["Year"], "rows": [["1956"]], "table_topic": "Milestones", "data_type": "table"}],
                "canonical_entity_name": "Artificial intelligence",
                "cross_language_links": {"zh": "https://zh.wikipedia.org/wiki/%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD"},
                "entity_name_translations": {"zh": "人工智能"},
            },
        },
        {},
    )

    assert normalized["article_creation_date"] == "2001-01-15T00:00:00Z"
    assert normalized["protection_level"] == "fully-protected"
    assert normalized["references_count"] == 1
    assert normalized["word_count"] == 6
    assert normalized["has_infobox"] is True
    assert normalized["infobox_raw"] == "industry=AI"
    assert normalized["infobox_structured"] == {"industry": "AI"}
    assert normalized["wikidata_id"] == "Q11660"
    assert normalized["article_summary"] == "Lead section."
    assert normalized["categories_cleaned"] == ["Artificial intelligence"]
    assert normalized["citation_density"] == 0.1667
    assert normalized["last_major_edit"] == "2026-04-02T08:00:00Z"
    assert normalized["article_quality_class"] == "good_article"
    assert normalized["domain"] == "artificial_intelligence"
    assert normalized["topic_hierarchy"] == ["artificial_intelligence", "technology"]
    assert normalized["subject_tags"] == ["Artificial intelligence"]
    assert normalized["external_links_classified"] == [
        {"url": "https://openai.com/research", "source_type": "other", "reliability_tier": "medium"},
    ]
    assert normalized["table_of_contents"] == ["History"]
    assert normalized["sections_structured"] == [{"heading": "History", "content": "More details here.", "section_type": "history"}]
    assert normalized["tables_structured"] == [{"table_title": "Milestones", "headers": ["Year"], "rows": [["1956"]], "table_topic": "Milestones", "data_type": "table"}]
    assert normalized["canonical_entity_name"] == "Artificial intelligence"
    assert normalized["cross_language_links"] == {"zh": "https://zh.wikipedia.org/wiki/%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD"}
    assert normalized["entity_name_translations"] == {"zh": "人工智能"}


def test_arxiv_normalizer_preserves_extended_metadata_fields() -> None:
    normalizer = hook_normalizer("arxiv")

    normalized = normalizer(
        {"platform": "arxiv", "resource_type": "paper", "title": "GPT-4 Technical Report"},
        {"fields": {"arxiv_id": "2303.08774"}},
        {
            "metadata": {
                "title": "GPT-4 Technical Report",
                "authors": ["OpenAI", "Josh Achiam"],
            },
            "plain_text": "We report the development of GPT-4.",
            "structured": {
                "doi": "10.48550/arXiv.2303.08774",
                "published": "2023-03-15",
                "updated": "2023-03-27",
                "comment": "Accepted to internal review.",
                "journal_ref": "arXiv preprint",
                "license": "http://creativecommons.org/licenses/by/4.0/",
                "pdf_url": "https://arxiv.org/pdf/2303.08774.pdf",
                "primary_category": "cs.CL",
                "categories": ["cs.CL", "cs.AI"],
                "references": ["Attention Is All You Need"],
                "page_count": 12,
            },
        },
        {},
    )

    assert normalized["DOI"] == "10.48550/arXiv.2303.08774"
    assert normalized["submission_date"] == "2023-03-15"
    assert normalized["update_date"] == "2023-03-27"
    assert normalized["submission_comments"] == "Accepted to internal review."
    assert normalized["journal_ref"] == "arXiv preprint"
    assert normalized["license"] == "http://creativecommons.org/licenses/by/4.0/"
    assert normalized["PDF_url"] == "https://arxiv.org/pdf/2303.08774.pdf"
    assert normalized["num_authors"] == 2


def test_linkedin_adapter_requires_auth_and_browser() -> None:
    adapter = get_platform_adapter("linkedin")
    assert adapter.requires_auth is True
    assert adapter.default_backend == "api"
    assert "profile" in adapter.supported_resource_types
    assert "search" in adapter.supported_resource_types


def test_registry_lists_all_known_adapters() -> None:
    platforms = {adapter.platform for adapter in list_platform_adapters()}

    assert platforms == {"wikipedia", "arxiv", "amazon", "base", "linkedin", "generic"}


def test_generic_adapter_declares_page_support_with_http_default() -> None:
    adapter = get_platform_adapter("generic")

    assert adapter.platform == "generic"
    assert adapter.supported_resource_types == ("page",)
    assert adapter.requires_auth is False
    assert adapter.default_backend == "http"

    assert adapter.resolve_backend(
        {"platform": "generic", "resource_type": "page", "url": "https://example.com"},
        None,
        retry_count=0,
    ) == "http"
    assert adapter.resolve_backend(
        {"platform": "generic", "resource_type": "page", "url": "https://example.com"},
        None,
        retry_count=1,
    ) == "playwright"
    assert adapter.resolve_backend(
        {"platform": "generic", "resource_type": "page", "url": "https://example.com"},
        None,
        retry_count=2,
    ) == "camoufox"


def test_linkedin_headers_preserve_ajax_prefixed_jsessionid(workspace_tmp_path: Path) -> None:
    storage_state_path = workspace_tmp_path / "linkedin.json"
    storage_state_path.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "li_at", "value": "secret-token", "domain": ".linkedin.com", "path": "/"},
                    {"name": "JSESSIONID", "value": '"ajax:123"', "domain": ".linkedin.com", "path": "/"},
                    {"name": "lang", "value": "v=2&lang=zh-cn", "domain": ".linkedin.com", "path": "/"},
                ],
                "origins": [],
            }
        ),
        encoding="utf-8",
    )

    headers = linkedin._storage_state_headers(str(storage_state_path), None, {"canonical_url": "https://www.linkedin.com/"})

    assert headers["csrf-token"] == "ajax:123"
    assert headers["x-li-lang"] == "zh_CN"
    assert "li_at=secret-token" in headers["Cookie"]


def test_linkedin_company_fetch_uses_browser_verified_detail_query(monkeypatch, workspace_tmp_path: Path) -> None:
    storage_state_path = workspace_tmp_path / "linkedin.json"
    storage_state_path.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "li_at", "value": "secret-token", "domain": ".linkedin.com", "path": "/"},
                    {"name": "JSESSIONID", "value": '"ajax:123"', "domain": ".linkedin.com", "path": "/"},
                ],
                "origins": [],
            }
        ),
        encoding="utf-8",
    )
    calls: list[dict] = []

    def fake_fetch(*, canonical_url: str, api_endpoint: str, headers: dict[str, str] | None = None, timeout: float = 30.0) -> dict:
        calls.append({"canonical_url": canonical_url, "api_endpoint": api_endpoint, "headers": headers or {}})
        return {
            "url": canonical_url,
            "api_endpoint": api_endpoint,
            "content_type": "application/json",
            "json_data": {"included": [{"$type": "com.linkedin.voyager.organization.Company", "name": "OpenAI"}]},
        }

    monkeypatch.setattr("crawler.platforms.linkedin.fetch_api_get", fake_fetch)

    linkedin._fetch_linkedin_api(
        {"platform": "linkedin", "resource_type": "company", "company_slug": "openai"},
        {"canonical_url": "https://www.linkedin.com/company/openai/"},
        str(storage_state_path),
    )

    assert len(calls) == 1
    assert calls[0]["api_endpoint"].startswith("https://www.linkedin.com/voyager/api/organization/companies")
    assert "q=universalName" in calls[0]["api_endpoint"]
    assert "universalName=openai" in calls[0]["api_endpoint"]
    assert "decorationId=com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-12" in calls[0]["api_endpoint"]


def test_linkedin_profile_fetch_uses_browser_verified_profile_query(monkeypatch, workspace_tmp_path: Path) -> None:
    storage_state_path = workspace_tmp_path / "linkedin.json"
    storage_state_path.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "li_at", "value": "secret-token", "domain": ".linkedin.com", "path": "/"},
                    {"name": "JSESSIONID", "value": '"ajax:123"', "domain": ".linkedin.com", "path": "/"},
                ],
                "origins": [],
            }
        ),
        encoding="utf-8",
    )
    calls: list[dict] = []

    def fake_fetch(*, canonical_url: str, api_endpoint: str, headers: dict[str, str] | None = None, timeout: float = 30.0) -> dict:
        calls.append({"canonical_url": canonical_url, "api_endpoint": api_endpoint, "headers": headers or {}})
        return {
            "url": canonical_url,
            "api_endpoint": api_endpoint,
            "content_type": "application/json",
            "json_data": {"data": {"entityUrn": "urn:li:fsd_profile:ACoAAA"}},
        }

    monkeypatch.setattr("crawler.platforms.linkedin.fetch_api_get", fake_fetch)

    linkedin._fetch_linkedin_api(
        {"platform": "linkedin", "resource_type": "profile", "public_identifier": "satyanadella"},
        {"canonical_url": "https://www.linkedin.com/in/satyanadella/"},
        str(storage_state_path),
    )

    assert len(calls) == 1
    assert "variables=(vanityName:satyanadella)" in calls[0]["api_endpoint"]
    assert "queryId=voyagerIdentityDashProfiles.34ead06db82a2cc9a778fac97f69ad6a" in calls[0]["api_endpoint"]


def test_linkedin_extracts_profile_from_graphql_collection_shape() -> None:
    extracted = linkedin._extract_linkedin_profile(
        {
            "data": {
                "identityDashProfilesByMemberIdentity": {
                    "elements": [
                        {
                            "_type": "com.linkedin.voyager.dash.identity.profile.Profile",
                            "entityUrn": "urn:li:fsd_profile:123",
                            "publicIdentifier": "john-doe-ai",
                            "firstName": "John",
                            "lastName": "Doe",
                            "headline": "AI at Self",
                        }
                    ]
                }
            }
        }
    )

    assert extracted["title"] == "John Doe"
    assert extracted["structured"]["source_id"] == "123"
    assert extracted["structured"]["public_identifier"] == "john-doe-ai"
    assert extracted["structured"]["headline"] == "AI at Self"


def test_linkedin_fetch_profile_falls_back_to_html_on_451(monkeypatch) -> None:
    request = httpx.Request("GET", "https://www.linkedin.com/voyager/api/graphql?profile")
    response = httpx.Response(451, request=request)

    def fake_json_fetch(**kwargs):
        raise httpx.HTTPStatusError("451", request=request, response=response)

    def fake_html_fetch(**kwargs):
        return {"url": kwargs["canonical_url"], "content_type": "text/html", "text": "<html><title>Satya Nadella | LinkedIn</title></html>"}

    monkeypatch.setattr(linkedin, "_fetch_linkedin_json", fake_json_fetch)
    monkeypatch.setattr(linkedin, "_fetch_linkedin_html", fake_html_fetch)

    fetched = linkedin._fetch_linkedin_api(
        {"platform": "linkedin", "resource_type": "profile", "public_identifier": "satyanadella"},
        {"canonical_url": "https://www.linkedin.com/in/satyanadella/"},
        "dummy.json",
    )

    assert fetched["html_fallback_text"] == "<html><title>Satya Nadella | LinkedIn</title></html>"


def test_linkedin_fetch_company_falls_back_to_html_on_451(monkeypatch) -> None:
    request = httpx.Request("GET", "https://www.linkedin.com/voyager/api/company")
    response = httpx.Response(451, request=request)

    def fake_json_fetch(**kwargs):
        raise httpx.HTTPStatusError("451", request=request, response=response)

    def fake_html_fetch(**kwargs):
        return {"url": kwargs["canonical_url"], "content_type": "text/html", "text": "<html><title>OpenAI | LinkedIn</title></html>"}

    monkeypatch.setattr(linkedin, "_fetch_linkedin_json", fake_json_fetch)
    monkeypatch.setattr(linkedin, "_fetch_linkedin_html", fake_html_fetch)

    fetched = linkedin._fetch_linkedin_api(
        {"platform": "linkedin", "resource_type": "company", "company_slug": "openai"},
        {"canonical_url": "https://www.linkedin.com/company/openai/"},
        "dummy.json",
    )

    assert fetched["html_fallback_text"] == "<html><title>OpenAI | LinkedIn</title></html>"


def test_linkedin_extracts_company_from_top_level_elements_shape() -> None:
    extracted = linkedin._extract_linkedin_company(
        {
            "elements": [
                {
                    "entityUrn": "urn:li:fs_normalized_company:11130470",
                    "name": "OpenAI",
                    "universalName": "openai",
                    "description": "AI research company",
                    "companyIndustries": [{"localizedName": "Research Services"}],
                    "headquarter": {"city": "San Francisco", "country": "US"},
                    "staffCountRange": {"start": 1001, "end": 5000},
                    "companyType": {"localizedName": "Privately Held"},
                    "contentTopicCards": [
                        {"name": "AI"},
                        {"entityUrn": "urn:li:fs_contentTopicData:urn:li:hashtag:machinelearning"},
                    ],
                    "fundingData": {
                        "companyCrunchbaseUrl": "https://www.crunchbase.com/organization/openai",
                        "lastFundingRound": {"fundingType": "SECONDARY_MARKET"},
                        "numFundingRounds": 11,
                    },
                    "companyPageUrl": "https://openai.com",
                    "followingInfo": {"followerCount": 123456},
                    "logo": {
                        "image": {
                            "rootUrl": "https://cdn.example.com/",
                            "artifacts": [
                                {"width": 100, "fileIdentifyingUrlPathSegment": "logo-small.png"},
                                {"width": 200, "fileIdentifyingUrlPathSegment": "logo-large.png"},
                            ],
                        }
                    },
                }
            ]
        }
    )

    assert extracted["title"] == "OpenAI"
    assert extracted["structured"]["source_id"] == "11130470"
    assert extracted["structured"]["company_slug"] == "openai"
    assert extracted["structured"]["industry"] == "Research Services"
    assert extracted["structured"]["follower_count"] == 123456
    assert extracted["structured"]["logo_url"] == "https://cdn.example.com/logo-large.png"
    assert extracted["structured"]["country_code"] == "US"
    assert extracted["structured"]["company_size_range"] == "1001-5000 employees"
    assert extracted["structured"]["company_type"] == "private"
    assert extracted["structured"]["top_topics"] == ["ai", "machinelearning"]
    assert extracted["structured"]["funding_stage_inferred"] == "secondary_market"
    assert extracted["structured"]["linkable_identifiers"] == {
        "website_domain": "openai.com",
        "crunchbase_hint": "https://www.crunchbase.com/organization/openai",
    }
    assert extracted["structured"]["company_stage_signals"] == {
        "stage_inferred": "secondary_market",
        "confidence": 0.8,
        "evidence_phrases": ["SECONDARY_MARKET", "11 funding rounds"],
    }


def test_linkedin_extracts_company_logo_from_vector_image_wrapper() -> None:
    extracted = linkedin._extract_linkedin_company(
        {
            "elements": [
                {
                    "entityUrn": "urn:li:fs_normalized_company:11130470",
                    "name": "OpenAI",
                    "universalName": "openai",
                    "logo": {
                        "image": {
                            "com.linkedin.common.VectorImage": {
                                "rootUrl": "https://media.licdn.com/dms/image/v2/D560BAQHpzXbqSyR74A/company-logo_",
                                "artifacts": [
                                    {
                                        "width": 100,
                                        "fileIdentifyingUrlPathSegment": "100_100/logo-small.png",
                                    },
                                    {
                                        "width": 400,
                                        "fileIdentifyingUrlPathSegment": "400_400/logo-large.png",
                                    },
                                ],
                            }
                        }
                    },
                }
            ]
        }
    )

    assert (
        extracted["structured"]["logo_url"]
        == "https://media.licdn.com/dms/image/v2/D560BAQHpzXbqSyR74A/company-logo_400_400/logo-large.png"
    )


def test_linkedin_extracts_company_from_html_bpr_fallback() -> None:
    extracted = linkedin._extract_linkedin_company_from_html(
        {"platform": "linkedin", "resource_type": "company", "company_slug": "openai"},
        """
        <html><head><title>OpenAI | LinkedIn</title></head><body>
        <code style="display: none" id="bpr-guid-1">
        {"data":{"data":{"organizationDashCompaniesByUniversalName":{"*elements":["urn:li:fsd_company:11130470"],"$type":"com.linkedin.restli.common.CollectionResponse"}}},"included":[{"entityUrn":"urn:li:fsd_company:11130470","name":"OpenAI","description":"AI research and deployment company.","universalName":"openai","companyPageUrl":"https://openai.com/","url":"https://www.linkedin.com/company/openai/","followingInfo":{"followerCount":10514911},"headquarter":{"city":"San Francisco"},"specialities":["artificial intelligence","machine learning"],"$type":"com.linkedin.voyager.dash.organization.Company"}]}
        </code>
        <code style="display: none" id="datalet-bpr-guid-1">
        {"request":"/voyager/api/graphql?includeWebMetadata=true&variables=(universalName:openai)&queryId=voyagerOrganizationDashCompanies.bd2de7b53b2079072f92b55ac1bae2f3","status":200,"body":"bpr-guid-1","method":"GET"}
        </code>
        </body></html>
        """,
    )

    assert extracted["title"] == "OpenAI"
    assert extracted["structured"]["source_id"] == "11130470"
    assert extracted["structured"]["company_slug"] == "openai"
    assert extracted["structured"]["description"] == "AI research and deployment company."
    assert extracted["structured"]["follower_count"] == 10514911
    assert extracted["structured"]["headquarters"] == "San Francisco"


def test_linkedin_normalizer_preserves_company_direct_and_derived_schema_fields() -> None:
    normalizer = hook_normalizer("linkedin")

    normalized = normalizer(
        {"platform": "linkedin", "resource_type": "company", "url": "https://www.linkedin.com/company/openai/"},
        {"canonical_url": "https://www.linkedin.com/company/openai/", "fields": {"company_slug": "openai"}},
        {
            "metadata": {"title": "OpenAI", "description": "AI research company"},
            "structured": {
                "source_id": "11130470",
                "title": "OpenAI",
                "description": "AI research company",
                "country_code": "US",
                "company_size_range": "1001-5000 employees",
                "company_type": "private",
                "top_topics": ["ai", "machinelearning"],
                "funding_stage_inferred": "secondary_market",
                "tech_stack_mentioned_in_about": ["AI", "machine learning"],
                "linkable_identifiers": {
                    "website_domain": "openai.com",
                    "crunchbase_hint": "https://www.crunchbase.com/organization/openai",
                },
                "company_stage_signals": {
                    "stage_inferred": "secondary_market",
                    "confidence": 0.8,
                    "evidence_phrases": ["SECONDARY_MARKET", "11 funding rounds"],
                },
            },
        },
        {},
    )

    assert normalized["country_code"] == "US"
    assert normalized["company_size_range"] == "1001-5000 employees"
    assert normalized["company_type"] == "private"
    assert normalized["top_topics"] == ["ai", "machinelearning"]
    assert normalized["funding_stage_inferred"] == "secondary_market"
    assert normalized["tech_stack_mentioned_in_about"] == ["AI", "machine learning"]
    assert normalized["linkable_identifiers"] == {
        "website_domain": "openai.com",
        "crunchbase_hint": "https://www.crunchbase.com/organization/openai",
    }
    assert normalized["company_stage_signals"] == {
        "stage_inferred": "secondary_market",
        "confidence": 0.8,
        "evidence_phrases": ["SECONDARY_MARKET", "11 funding rounds"],
    }


def test_linkedin_extracts_profile_from_html_fallback() -> None:
    extracted = linkedin._extract_linkedin_profile_from_html(
        {"platform": "linkedin", "resource_type": "profile", "public_identifier": "satyanadella"},
        """
        <html>
          <head><title>Satya Nadella | LinkedIn</title></head>
          <body>
            <a href="https://www.linkedin.com/in/satyanadella/">Satya Nadella Chairman and CEO at Microsoft</a>
            <p>Microsoft</p>
            <p>美国 华盛顿州 雷德蒙德</p>
            <p>·</p>
            <p><a href="https://www.linkedin.com/in/satyanadella/overlay/contact-info/">联系方式</a></p>
            <p>11,928,051 位关注者</p>
            <h2>个人简介</h2>
            <p>Leading Microsoft through the AI platform shift.</p>
            <img src="https://media.licdn.com/dms/image/v2/D4E03AQHsmDqgICL5jQ/profile-displayphoto-shrink_400_400/example.jpg"/>
            <img src="https://media.licdn.com/dms/image/v2/D5616AQFuhBYf-ocZug/profile-displaybackgroundimage-shrink_350_1400/example.jpg"/>
          </body>
        </html>
        """,
    )

    assert extracted["title"] == "Satya Nadella"
    assert extracted["structured"]["source_id"] == "satyanadella"
    assert extracted["structured"]["headline"] == "Chairman and CEO at Microsoft"
    assert extracted["structured"]["city"] == "美国 华盛顿州 雷德蒙德"
    assert extracted["structured"]["follower_count"] == 11928051
    assert extracted["structured"]["about"] == "Leading Microsoft through the AI platform shift."
    assert "profile-displayphoto" in extracted["structured"]["avatar"]
    assert "profile-displaybackgroundimage" in extracted["structured"]["banner_image"]


def test_linkedin_normalizer_preserves_extracted_structured_fields() -> None:
    normalized = linkedin.ADAPTER.normalize_record(
        {"platform": "linkedin", "resource_type": "company", "company_slug": "openai"},
        {"fields": {"company_slug": "openai"}},
        {
            "metadata": {"title": "OpenAI"},
            "structured": {
                "linkedin": {
                    "source_id": "11130470",
                    "title": "OpenAI",
                    "company_slug": "openai",
                    "follower_count": 123456,
                }
            },
        },
        {},
    )

    assert normalized["source_id"] == "11130470"
    assert normalized["company_slug"] == "openai"
    assert normalized["follower_count"] == 123456
    assert normalized["title"] == "OpenAI"


# =============================================================================
# Fallback backend escalation tests
# =============================================================================


def test_non_auth_platform_fallback_escalates_on_retry() -> None:
    """Non-auth platforms (Amazon, Base, Wikipedia) should also escalate to fallback backends on retry."""
    from crawler.platforms.amazon import ADAPTER as amazon_adapter

    # First attempt: default backend (http for Amazon)
    backend_0 = amazon_adapter.resolve_backend({"platform": "amazon", "resource_type": "product"}, None, retry_count=0)
    assert backend_0 == "http"

    # Retry 1: first fallback (playwright)
    backend_1 = amazon_adapter.resolve_backend({"platform": "amazon", "resource_type": "product"}, None, retry_count=1)
    assert backend_1 == "playwright"

    # Retry 2: second fallback (camoufox)
    backend_2 = amazon_adapter.resolve_backend({"platform": "amazon", "resource_type": "product"}, None, retry_count=2)
    assert backend_2 == "camoufox"


def test_amazon_adapter_uses_resource_specific_default_field_groups() -> None:
    from crawler.platforms.amazon import ADAPTER as amazon_adapter

    product_request = amazon_adapter.build_enrichment_request({"platform": "amazon", "resource_type": "product"})
    seller_request = amazon_adapter.build_enrichment_request({"platform": "amazon", "resource_type": "seller"})
    review_request = amazon_adapter.build_enrichment_request({"platform": "amazon", "resource_type": "review"})

    assert product_request["field_groups"] == (
        "amazon_products_identity",
        "amazon_products_pricing",
        "amazon_products_description",
        "amazon_products_category",
        "amazon_products_visual",
        "amazon_products_availability",
        "amazon_products_competition",
        "amazon_products_reviews_summary",
        "amazon_products_variants",
        "amazon_products_compliance",
        "amazon_products_multimodal_images",
        "amazon_products_multi_level_summary",
        "amazon_products_market_positioning",
        "amazon_products_listing_quality",
        "amazon_products_linkable_ids",
    )
    assert seller_request["field_groups"] == (
        "amazon_sellers_identity",
        "amazon_sellers_performance",
        "amazon_sellers_portfolio",
        "amazon_sellers_business_intel",
        "amazon_sellers_multi_level_summary",
        "amazon_sellers_linkable_ids",
    )
    assert review_request["field_groups"] == (
        "amazon_reviews_identity",
        "amazon_reviews_content",
        "amazon_reviews_analysis",
        "amazon_reviews_quality",
        "amazon_reviews_structured",
        "amazon_reviews_media",
        "amazon_reviews_multimodal_images",
        "amazon_reviews_multi_level_summary",
        "amazon_reviews_review_depth",
    )


def test_base_platform_fallback_escalates_on_retry() -> None:
    """Base chain platform should escalate to fallback backends on retry."""
    from crawler.platforms.base_chain import ADAPTER as base_adapter

    # First attempt: default backend (api for base)
    backend_0 = base_adapter.resolve_backend({"platform": "base", "resource_type": "address"}, None, retry_count=0)
    assert backend_0 == "api"

    # Retry 1: first fallback (http)
    backend_1 = base_adapter.resolve_backend({"platform": "base", "resource_type": "address"}, None, retry_count=1)
    assert backend_1 == "http"

    # Retry 2: second fallback (playwright)
    backend_2 = base_adapter.resolve_backend({"platform": "base", "resource_type": "address"}, None, retry_count=2)
    assert backend_2 == "playwright"


def test_base_token_prefers_http_html_flow() -> None:
    from crawler.platforms.base_chain import ADAPTER as base_adapter

    backend_0 = base_adapter.resolve_backend({"platform": "base", "resource_type": "token"}, None, retry_count=0)
    backend_1 = base_adapter.resolve_backend({"platform": "base", "resource_type": "token"}, None, retry_count=1)

    assert backend_0 == "http"
    assert backend_1 == "playwright"


def test_base_contract_prefers_http_html_flow() -> None:
    from crawler.platforms.base_chain import ADAPTER as base_adapter

    backend_0 = base_adapter.resolve_backend({"platform": "base", "resource_type": "contract"}, None, retry_count=0)
    backend_1 = base_adapter.resolve_backend({"platform": "base", "resource_type": "contract"}, None, retry_count=1)

    assert backend_0 == "http"
    assert backend_1 == "playwright"


def test_linkedin_post_escalates_to_camoufox_on_retry() -> None:
    """LinkedIn post should start with api and escalate to camoufox on retry."""
    from crawler.platforms.linkedin import _resolve_linkedin_backend, FETCH_PLAN

    # First attempt: api for post detail HTML
    backend_0 = _resolve_linkedin_backend({"resource_type": "post"}, None, retry_count=0)
    assert backend_0 == "api"

    # Retry 1: should escalate to first fallback (playwright in FETCH_PLAN.fallback_backends)
    backend_1 = _resolve_linkedin_backend({"resource_type": "post"}, None, retry_count=1)
    assert backend_1 == FETCH_PLAN.fallback_backends[0]  # playwright

    # Retry 2: should escalate to second fallback (camoufox)
    backend_2 = _resolve_linkedin_backend({"resource_type": "post"}, None, retry_count=2)
    assert backend_2 == "camoufox"


def test_linkedin_profile_escalates_to_camoufox_on_retry() -> None:
    """LinkedIn profile should start with api and escalate through fallback chain on retry."""
    from crawler.platforms.linkedin import _resolve_linkedin_backend

    # First attempt: api for profile
    backend_0 = _resolve_linkedin_backend({"resource_type": "profile"}, None, retry_count=0)
    assert backend_0 == "api"

    # Retry 1: first fallback (playwright)
    backend_1 = _resolve_linkedin_backend({"resource_type": "profile"}, None, retry_count=1)
    assert backend_1 == "playwright"

    # Retry 2: second fallback (camoufox)
    backend_2 = _resolve_linkedin_backend({"resource_type": "profile"}, None, retry_count=2)
    assert backend_2 == "camoufox"


def test_linkedin_search_starts_with_api_and_falls_back() -> None:
    backend_0 = linkedin._resolve_linkedin_backend({"resource_type": "search", "search_type": "company"}, None, retry_count=0)
    backend_1 = linkedin._resolve_linkedin_backend({"resource_type": "search", "search_type": "company"}, None, retry_count=1)
    backend_2 = linkedin._resolve_linkedin_backend({"resource_type": "search", "search_type": "company"}, None, retry_count=2)

    assert backend_0 == "api"
    assert backend_1 == "playwright"
    assert backend_2 == "camoufox"
