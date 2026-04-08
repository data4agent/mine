# Dataset Product Catalog

> AI-Enhanced Structured Data · LLM-Powered Deep Extraction · Beyond Raw Scraping

---

## 1. LinkedIn Dataset

### Overview

Access the world's largest professional network dataset with **LLM-enhanced semantic extraction**. Unlike traditional scraping that captures raw field values, our AI engine deeply parses unstructured text fields — extracting skills from free-text descriptions, standardizing job titles across languages, detecting profile inconsistencies and experience gaps, inferring career motivations, analyzing profile images, generating multi-audience summaries with personalized outreach hooks, and producing cross-dataset linkable identifiers for downstream entity resolution.

**Total Records:** 880M+ profiles · 60M+ companies · 35M+ posts · 25M+ job listings

**Pricing:** Starting at $275 / 100K records · Subscription discounts available

### Sub-Datasets

#### 1.1 LinkedIn Profiles Dataset

**668M+ records**


| Category | Standard Fields | 🔥 LLM-Enhanced Fields (Exclusive) |
|----------|----------------|-------------------------------------|
| **Identity** | ID, name, city, country_code, avatar, banner_image, URL, linkedin_num_id, `profile_url_custom` (bool) | `name_gender_inference`, `name_ethnicity_estimation`, `profile_language_detected` |
| **Current Role** | position, current_company, current_company_id, current_company_name | `standardized_job_title` (mapped to O*NET/ISCO taxonomy), `seniority_level` (C-suite/VP/Director/Manager/IC), `job_function_category` (Engineering/Sales/Marketing/...) |
| **About** | about (raw text) | `about_summary` (3-sentence distillation), `about_topics` (extracted topic tags), `about_sentiment`, `career_narrative_type` (builder/leader/specialist/entrepreneur) |
| **Open Status** | `open_to_work` (bool), `open_to_work_details` (if visible: desired titles, locations, work types) | `job_change_signal_strength` (0-1 composite score from: open_to_work flag, tenure pattern, recent certification activity, profile update recency) |
| **Experience** | experience (array of raw entries) | `experience_structured[]`: each entry parsed into {company, title, start_date, end_date, duration_months, `responsibilities_extracted[]`, `technologies_mentioned[]`, `achievements_quantified[]`, `industry_standardized`} |
| **Education** | education, educations_details | `education_structured[]`: {institution, degree_type (PhD/Master/Bachelor/...), field_of_study_standardized, graduation_year, `institution_recognition_level` (world-class/well-known/regional/unknown — LLM knowledge-based assessment)} |
| **Skills** | (not directly extracted) | `skills_extracted[]` (from about + experience text), `skill_categories` (Technical/Soft/Domain), `skill_proficiency_inferred` (based on experience duration + context) |
| **Social** | followers, connections, posts (count), recommendations_count | `influence_score` (composite from followers + connections + recommendations), `content_activity_level` (active/moderate/passive/lurker — based on posts count + recency) |
| **Network** | people_also_viewed | `professional_cluster` (inferred peer group), `career_trajectory_vector` (embedding for similarity search) |
| **Certifications** | certifications, languages, courses | `certification_expiry_mentioned` (extracted from cert name/description, e.g., "AWS SAA 2024"), `language_proficiency_level` (mapped to CEFR scale) |
| **Publications** | `publications_listed[]` {title, publisher, date, url, description} | `publication_type` (journal_paper/conference_paper/book_chapter/blog/patent), `publication_topics[]` |
| **Honors** | `honors_and_awards[]` {title, issuer, date, description} | `award_significance_level` (international/national/institutional/team) |
| **Projects** | `projects_listed[]` {title, url, date_range, description, team_members} | `project_domain`, `technologies_used[]`, `project_scale_hint` |
| **Patents** | `patents_listed[]` {title, patent_number, date, status, url} | `patent_domain`, `patent_innovation_type` (utility/design/process) |
| **Volunteer** | `volunteer_experience[]` {role, organization, date_range, description, cause} | `cause_categories[]` (education/environment/health/social_justice/...) |
| **Featured** | `featured_content[]` {type (post/article/link/media), title, url} | `featured_content_themes[]`, `personal_brand_focus` |
| **Metadata** | timestamp, input_url | `profile_completeness_score`, `last_active_estimate`, `profile_freshness_grade` |
| **Dedup & Normalization** | `dedup_key` (`linkedin_num_id`), `canonical_url` (normalized profile URL) | `url_normalize_regex`: `^https?://(?:www\.)?linkedin\.com/in/([^/?#]+).*$` → `https://www.linkedin.com/in/$1` |
| **🔥 Multimodal** | avatar (image URL), banner_image (image URL) | `avatar_quality_assessment` {is_professional_headshot, face_detected, lighting_quality, background_type (studio/office/outdoor/casual)}, `banner_content_analysis` {depicts (company_logo/product/event/abstract/city_skyline/...), brand_alignment_score, text_extracted_from_banner} |
| **🔥 Multi-level Summary** | (derived from all text fields) | `one_line_summary` (≤15 words), `recruiter_brief` (3-sentence profile optimized for hiring evaluation: strengths, experience depth, potential fit), `investor_brief` (for VC scouts: technical depth, leadership signal, entrepreneurial indicators), `full_profile_narrative` (2-paragraph natural language biography synthesized from all structured fields) |
| **🔥 Behavioral Signals** | (derived from about + experience + posts) | `writing_style_profile` {formality_level, vocabulary_richness, jargon_density, persuasion_style (data-driven/storytelling/authoritative/collaborative)}, `culture_fit_indicators` {work_style_inferred (remote-first/in-office/hybrid), values_expressed[] (innovation/stability/growth/impact/...), communication_style (concise/verbose/technical/accessible)} |
| **🔥 Cross-dataset Linkable IDs** | (extracted from profile text) | `linkable_identifiers`: {`github_urls[]` (from about/experience text), `personal_website_url`, `twitter_handle`, `orcid_id`, `google_scholar_url`, `arxiv_author_query_hint` (full_name + affiliation formatted for arXiv search), `company_domains_mentioned[]`, `patent_numbers_mentioned[]`, `publication_titles_mentioned[]` (paper titles found in about/experience for arXiv matching)} |
| **🆕 Consistency Check** | (derived from all fields) | `internal_consistency_flags[]` {inconsistency (e.g., "About claims 10 years Python but earliest Python role is 3 years ago"), field_a, field_b, severity (minor/moderate/critical)}, `experience_gap_analysis[]` {gap_start, gap_end, duration_months, context_hint (career_pivot/education/entrepreneurship/unknown)} |
| **🆕 Career Intelligence** | (derived from experience sequence) | `career_transition_detected[]` {from_role, to_role, transition_type (upward/lateral/career_pivot/industry_switch), transition_risk_level}, `motivation_signals` {primary_motivation (impact/money/learning/status/autonomy/creativity), evidence_phrases[]}, `side_project_signals[]` {project_name, nature (open_source/consulting/startup/content_creation), commitment_level} |
| **🆕 Credibility & Outreach** | (derived from all text) | `credibility_assessment` {overall_score (0-1), red_flags[] (inflated_titles/unverifiable_claims/inconsistent_dates/buzzword_heavy), green_flags[] (specific_metrics/named_projects/verifiable_companies)}, `cold_outreach_hooks[]` (3 personalized conversation starters based on profile content), `interview_questions_suggested[]` (verification questions targeting specific achievement claims) |
| **🆕 Training Data** | (derived from all fields) | `qa_pairs_generated[]` {question, answer, source_field} (5-10 Q&A pairs derived from the profile, for RAG/instruction tuning datasets) |

**Sample Record (JSON):**
```json
{
  "linkedin_id": "john-doe-ai-researcher",
  "name": "John Doe",
  "profile_url_custom": true,
  "open_to_work": false,
  "standardized_job_title": "Machine Learning Engineer",
  "seniority_level": "Senior IC",
  "job_function_category": "Engineering - AI/ML",
  "one_line_summary": "Senior ML engineer at Google specializing in NLP and recommendation systems",
  "recruiter_brief": "8-year ML specialist with deep FAANG experience. Core strengths in production recommendation systems and distributed training infrastructure. Strong IC track record with emerging leadership signals (led team of 5).",
  "investor_brief": "Deep technical builder in high-demand ML/NLP space. Google tenure suggests top-tier engineering bar. No entrepreneurial signals yet but domain expertise is highly commercializable.",
  "writing_style_profile": {
    "formality_level": "professional",
    "vocabulary_richness": 0.72,
    "persuasion_style": "data-driven"
  },
  "job_change_signal_strength": 0.35,
  "culture_fit_indicators": {
    "work_style_inferred": "hybrid",
    "values_expressed": ["innovation", "technical excellence"],
    "communication_style": "technical"
  },
  "avatar_quality_assessment": {
    "is_professional_headshot": true,
    "face_detected": true,
    "lighting_quality": "good",
    "background_type": "studio"
  },
  "publications_listed": [
    {"title": "Scaling Laws for Neural Language Models", "publisher": "arXiv", "date": "2020-01"}
  ],
  "patents_listed": [],
  "honors_and_awards": [
    {"title": "Best Paper Award", "issuer": "NeurIPS Workshop", "date": "2022"}
  ],
  "linkable_identifiers": {
    "github_urls": ["https://github.com/johndoe-ml"],
    "google_scholar_url": "https://scholar.google.com/citations?user=XXXX",
    "arxiv_author_query_hint": "John Doe, Google Research",
    "publication_titles_mentioned": ["Scaling Laws for Neural Language Models"],
    "company_domains_mentioned": ["google.com"]
  },
  "experience_structured": [
    {
      "company": "Google",
      "title": "Senior ML Engineer",
      "duration_months": 36,
      "responsibilities_extracted": ["Led team of 5 building real-time recommendation models", "Designed A/B testing framework"],
      "technologies_mentioned": ["TensorFlow", "Kubernetes", "BigQuery", "Flume"],
      "achievements_quantified": ["+15% CTR improvement", "3x inference throughput"],
      "industry_standardized": "Technology - Internet Services"
    }
  ],
  "skills_extracted": ["PyTorch", "TensorFlow", "Distributed Systems", "A/B Testing", "Leadership"],
  "career_trajectory_vector": [0.12, -0.34, 0.56, ...],
  "internal_consistency_flags": [],
  "experience_gap_analysis": [],
  "career_transition_detected": [
    {"from_role": "Software Engineer (backend)", "to_role": "ML Engineer", "transition_type": "career_pivot", "transition_risk_level": "moderate"}
  ],
  "motivation_signals": {"primary_motivation": "learning", "evidence_phrases": ["passionate about pushing boundaries", "constantly exploring new architectures"]},
  "credibility_assessment": {"overall_score": 0.89, "red_flags": [], "green_flags": ["specific_metrics (+15% CTR)", "named_projects", "verifiable_company (Google)"]},
  "cold_outreach_hooks": [
    "Your work on real-time recommendation models at Google caught my eye — we're tackling a similar challenge at [company] for healthcare.",
    "The +15% CTR improvement you mentioned is impressive — I'd love to hear how you handled the cold-start problem.",
    "Noticed you've published on scaling laws — we're building on that research and could use your perspective."
  ],
  "qa_pairs_generated": [
    {"question": "What is John Doe's current role?", "answer": "Senior ML Engineer at Google, specializing in NLP and recommendation systems", "source_field": "current_role + about"},
    {"question": "What technologies does John Doe work with?", "answer": "TensorFlow, Kubernetes, BigQuery, Flume, PyTorch", "source_field": "experience_structured.technologies_mentioned + skills_extracted"}
  ]
}
```

#### 1.2 LinkedIn Company Dataset

**56M+ records**


| Category | Standard Fields | 🔥 LLM-Enhanced Fields |
|----------|----------------|------------------------|
| **Basic** | ID, name, URL, country_code, locations, website, `headquarters_location`, `founded_year`, `company_type` (public/private/nonprofit/educational/government), `company_size_range` (e.g., "51-200 employees") | `company_legal_name_inferred`, `parent_company_mentioned`, `subsidiary_mentioned[]` |
| **Profile** | about, specialties, industry | `about_summary`, `core_business_extracted`, `value_proposition`, `target_market_inferred`, `industry_standardized` (NAICS/SIC mapped), `tech_stack_mentioned_in_about[]` |
| **Scale** | followers, employees_in_linkedin | `funding_stage_inferred` (from about text clues: "Series B", "bootstrapped", "publicly traded"), `business_model_type` (SaaS/Marketplace/Enterprise/...), `revenue_hints_in_text` (e.g., "$10M ARR" if mentioned, null otherwise) |
| **Content** | posts (recent) | `content_strategy_analysis`, `posting_frequency`, `top_topics[]`, `brand_voice_profile` |
| **🔥 Multi-level Summary** | (derived from about + specialties) | `elevator_pitch` (1 sentence), `investor_brief` (key metrics + growth signals from page), `competitor_brief` (positioning + differentiation from companies mentioned in about) |
| **🔥 Cross-dataset Linkable IDs** | (extracted from about/website) | `linkable_identifiers`: {`website_domain`, `amazon_seller_search_hint` (brand name + product keywords), `wikipedia_entity_hint` (canonical company name), `github_org_url` (if mentioned), `crunchbase_hint`} |
| **🆕 Intent & Stage Signals** | (derived from about text) | `company_stage_signals` {stage_inferred (pre-seed/seed/early/growth/mature/public), confidence, evidence_phrases[] (e.g., "building the future of…" → early; "trusted by Fortune 500" → mature)}, `hiring_intent_from_about` (bool + evidence: "join our growing team", "we're hiring" etc.) |
| **Dedup & Normalization** | `dedup_key` (`company_id`), `canonical_url` (normalized company URL) | `url_normalize_regex`: `^https?://(?:www\.)?linkedin\.com/company/([^/?#]+).*$` → `https://www.linkedin.com/company/$1` |

#### 1.3 LinkedIn Jobs Dataset

**25M+ records**


| Category | Standard Fields | 🔥 LLM-Enhanced Fields |
|----------|----------------|------------------------|
| **Basic** | job_posting_id, job_title, company_name, company_id, job_location, `workplace_type` (On-site/Remote/Hybrid — LinkedIn native field), `application_method` (Easy Apply / external link / email) | `job_title_standardized`, `remote_policy_detail` (fully remote / remote with travel / hybrid N days / onsite-only — inferred from description when workplace_type is vague), `location_parsed` {city, state, country} |
| **Content** | job_summary, job_description (raw HTML/text) | `responsibilities_extracted[]`, `requirements_extracted[]` {skill, required_or_preferred, years_experience}, `salary_range_inferred`, `benefits_extracted[]`, `team_size_hint`, `reporting_to_level` |
| **Classification** | job_seniority_level, job_function | `role_category_fine_grained`, `industry_vertical`, `visa_sponsorship_signal`, `equity_compensation_signal` |
| **Skills** | (not directly extracted) | `required_skills[]`, `preferred_skills[]`, `tools_and_platforms[]`, `programming_languages[]`, `frameworks[]` |
| **Market** | applicants_count, date_posted | `competition_level`, `urgency_signal`, `reposting_frequency` |
| **🔥 Multi-level Summary** | (derived from description) | `candidate_facing_summary` (plain-English role overview stripped of corporate jargon), `hiring_manager_brief` (key requirements distilled into 5 bullet points with priority ranking) |
| **🔥 Domain-specific** | (derived from description) | `red_flags_detected[]` (unrealistic requirements, salary-experience mismatch, excessive on-call, vague role scope), `culture_signals_extracted` {management_style_hints, growth_opportunity_signals, work_life_balance_indicators}, `tech_stack_full_picture` {must_have[], nice_to_have[], infrastructure[], methodology[] (agile/waterfall/kanban)} |
| **🆕 JD Quality & Integrity** | (derived from description) | `jd_internal_contradictions[]` {contradiction (e.g., "Title says Junior but requires 8+ years"), field_a, field_b, severity}, `role_clarity_score` (0-1: how well-defined is the role scope; vague JDs with "wear many hats" / "other duties" score low), `ideal_candidate_persona` {years_experience_sweet_spot, background_path (e.g., "CS degree → 3yr SaaS startup → team lead"), must_have_vs_nice_to_have_ratio, deal_breaker_skills[]} |
| **Dedup & Normalization** | `dedup_key` (`job_posting_id`), `canonical_url` (normalized job URL) | `url_normalize_regex`: `^https?://(?:www\.)?linkedin\.com/jobs/view/(\d+).*$` → `https://www.linkedin.com/jobs/view/$1` |

#### 1.4 LinkedIn Posts Dataset

**34M+ records**


| Category | Standard Fields | 🔥 LLM-Enhanced Fields |
|----------|----------------|------------------------|
| **Content** | post_text, title, headline, hashtags, images, videos | `post_topic_tags[]`, `post_type` (thought_leadership/job_announcement/company_news/personal_story/engagement_bait), `key_claims_extracted[]`, `entities_mentioned[]` {name, type, sentiment} |
| **Engagement** | num_likes, num_comments, top_visible_comments | `engagement_quality_score` (based on comment depth and sentiment), `comment_sentiment_distribution`, `controversial_flag` |
| **Author** | user_id, user_url, user_followers | `author_authority_score`, `author_industry`, `is_corporate_voice` |
| **Temporal** | date_posted | `trending_topic_relevance`, `news_event_linkage` |
| **🔥 Multimodal** | images[], videos[] | `post_image_analysis[]` {image_type (infographic/screenshot/photo/meme/chart/slide), `text_extracted_from_image`, `chart_data_described`, `visual_sentiment`}, `shared_link_content_summary` (if post contains URL, summarize the linked article title/topic extracted from post context) |
| **🔥 Multi-level Summary** | (derived from post_text) | `post_one_liner` (1-sentence distillation of the post's main point), `post_takeaway` (the actionable insight or claim, if any) |
| **🔥 Behavioral** | (derived from post_text + comments) | `thought_leadership_depth` (surface_commentary/practical_insight/original_research/contrarian_take), `self_promotion_score` (0-1, how much the post promotes the author vs. provides value), `argument_structure` (claim_only/claim+evidence/narrative/question_posing) |
| **🆕 Intent & Verifiability** | (derived from post_text) | `posting_intent` {primary_intent (build_authority/recruit/sell/network/celebrate/educate/provoke_discussion), secondary_intent, confidence}, `audience_targeting` {target_audience (recruiters/peers/leadership/clients/general_public), evidence}, `factual_claims_checkable[]` {claim, verifiability (easily_verifiable/hard_to_verify/opinion/anecdotal)} |
| **Dedup & Normalization** | `dedup_key` (`post_id` from `urn:li:activity:{id}`), `canonical_url` (normalized post URL) | `url_normalize_regex`: `^https?://(?:www\.)?linkedin\.com/(?:feed/update/urn:li:activity:|posts/[^/]+-activity-)(\d+).*$` → `https://www.linkedin.com/feed/update/urn:li:activity:$1` |

### Use Cases

- **Talent Intelligence:** Identify and rank candidates with structured skill-experience matching, career trajectory analysis, credibility scoring, multi-audience briefs (recruiter/investor), and job-change signal scoring via open_to_work flags and behavioral signals
- **Talent Verification:** Detect profile inconsistencies (timeline gaps, inflated titles, unverifiable claims), generate targeted interview questions to verify specific achievement claims
- **Competitive Intelligence:** Track competitor brand voice, tech stack mentions, company stage signals, hiring intent, and content strategy from company pages and posts
- **Investment Signals:** Detect early growth signals through company page clues (funding stage, revenue hints), leadership patent/publication activity, and tech adoption indicators
- **Lead Generation:** Enrich CRM with standardized titles, inferred seniority, writing style profiles, motivation signals, and personalized cold outreach hooks — all derived per-profile
- **JD Quality Assurance:** Detect internal contradictions in job descriptions, assess role clarity, generate ideal candidate personas, and flag unrealistic requirements before posting
- **Cross-dataset Analytics:** Link professionals to their arXiv publications, companies to their Amazon storefronts, and projects to GitHub repos via extracted linkable identifiers
- **AI/LLM Training:** High-quality structured professional knowledge including image-text pairs (avatar + profile), multi-granularity summaries, behavioral signal labels, and per-record Q&A pairs for instruction tuning

---

## 2. arXiv Dataset

### Overview

The most comprehensive structured academic paper dataset available. Our LLM engine goes far beyond metadata extraction — it reads full-text papers and PDF figures, extracting research contributions, methodologies, datasets used, results and limitations, detecting internal consistency issues and missing baselines, assessing writing quality and experiment rigor, generating multi-audience summaries from tweet-length to full simulated peer review, and producing per-paper Q&A pairs for scientific training data.

**Total Records:** 2.5M+ papers · Updated daily with new submissions

**Pricing:** Starting at $150 / 100K records · Full archive available

### Data Fields


| Category | Standard Fields | 🔥 LLM-Enhanced Fields (Exclusive) |
|----------|----------------|-------------------------------------|
| **Identity** | arxiv_id, DOI, URL, title, abstract, `page_count`, `num_authors` | `title_normalized` (de-LaTeX'd clean text), `abstract_plain_text` (formula-free version) |
| **Authors** | authors[] {name, affiliation} | `authors_structured[]`: {full_name, first_name, last_name, `affiliation_standardized`, `affiliation_type` (university/company/lab/government), `affiliation_country`, `orcid_mentioned` (if found in paper footnotes/text, null otherwise), `career_stage_inferred` (PhD student/Postdoc/Assistant Prof/...)} |
| **Classification** | categories (arXiv codes), primary_category | `topic_hierarchy[]` (multi-level: Domain > Sub-field > Topic), `keywords_extracted[]`, `research_area_plain_english`, `interdisciplinary_score` |
| **Dates** | submission_date, update_date, versions[] | `venue_mentioned` (extracted from comments/journal-ref fields, e.g., "accepted at NeurIPS 2025"), `venue_tier_mapped` (A*/A/B/C/Workshop — mapped via external venue ranking table, null if venue not mentioned) |
| **Metadata** | `submission_comments` (arXiv "Comments" field, e.g., "12 pages, 5 figures"), `journal_ref` (arXiv "Journal reference" field), `license` (CC-BY/CC-BY-SA/arxiv-license/etc.) | `acceptance_status_inferred` (published/preprint/withdrawn — best-effort from journal_ref + comments fields) |
| **Full Text** | raw_text, PDF_url, `num_figures` | `sections_structured[]`: {heading, content_summary, section_type (introduction/related_work/methodology/experiment/results/discussion/conclusion)} |
| **Contribution** | (not available) | `main_contributions[]` (1-3 sentence claims), `novelty_type` (new_method/new_dataset/new_theory/new_application/survey), `problem_statement`, `proposed_solution_summary` |
| **Methodology** | (not available) | `methods_used[]` {method_name, method_category, is_novel}, `baselines_compared[]`, `evaluation_metrics[]`, `datasets_used[]` {name, URL, size, domain}, `experimental_setup_summary` |
| **Results** | (not available) | `key_results[]` {metric, value, baseline_comparison, improvement_percentage}, `state_of_art_claimed`, `statistical_significance_reported`, `reproducibility_indicators` |
| **Limitations** | (not available) | `limitations_stated[]`, `future_work_directions[]`, `threats_to_validity[]` |
| **References** | references[] (raw citation strings) | `references_structured[]`: {title, authors, year, venue, `citation_context` (how it's cited: background/method/comparison/extension), `citation_sentiment` (positive/negative/neutral)} |
| **Code & Data** | (not available) | `code_available` (bool), `code_url`, `code_framework` (PyTorch/TensorFlow/JAX/...), `dataset_released` (bool), `dataset_url`, `open_access_status` |
| **Embeddings** | (not available) | `title_embedding` (768-dim), `abstract_embedding` (768-dim), `full_paper_embedding` (768-dim) — for semantic search and clustering |
| **Relations** | (not available) | `builds_upon[]` (papers this extends), `contradicts[]`, `replicates[]`, `uses_dataset_from[]`, `uses_method_from[]` |
| **🔥 Multimodal (Figures)** | PDF figures (embedded in paper) | `figures_analyzed[]`: {figure_id, figure_type (architecture_diagram/bar_chart/line_chart/scatter_plot/table/flowchart/heatmap/confusion_matrix/photo/illustration), `caption_original`, `caption_enhanced` (if original is terse, LLM generates richer description), `key_findings_from_figure` (what does this figure show in 1-2 sentences), `data_points_extracted` (for charts: approximate values of key data points), `components_identified[]` (for architecture diagrams: named blocks/modules)} |
| **🔥 Multimodal (Equations)** | LaTeX equations in text | `key_equations[]`: {equation_latex, equation_id, `plain_english_explanation` (e.g., "This is the cross-entropy loss function weighted by class frequency"), `variables_defined` {symbol: meaning}, `equation_role` (objective_function/constraint/definition/derivation_step/final_result)} |
| **🔥 Multi-level Summary** | (derived from full text) | `tweet_summary` (≤280 chars, engaging hook for social sharing), `one_line_summary` (1-sentence technical summary), `executive_summary` (3-sentence non-technical version for PMs/VCs/journalists), `layman_summary` (2-paragraph explanation assuming zero domain knowledge, analogies encouraged), `technical_abstract_enhanced` (improved abstract fixing common issues: adds quantitative results if omitted, clarifies vague claims), `review_style_summary` (structured as: Strengths / Weaknesses / Questions for Authors / Overall Assessment — simulated peer review) |
| **🔥 Research Depth Analysis** | (derived from full text) | `mathematical_complexity_score` (1-5: 1=no math, 2=basic statistics, 3=linear algebra/calculus, 4=advanced optimization/proofs, 5=novel theoretical framework), `mathematical_complexity_evidence` (which sections/theorems drive the score), `novelty_delta_assessment` {novelty_claim, `actual_delta`: LLM's assessment of true incremental contribution vs. cited prior work, `closest_prior_work`: most similar existing approach from references}, `methodology_transferability[]` (other domains where this method could apply, with brief justification), `claim_verification_notes[]` {claim, `evidence_strength` (strong/moderate/weak/unsupported), `evidence_detail`, `potential_issues`} |
| **🔥 Cross-dataset Linkable IDs** | (extracted from paper text) | `linkable_identifiers`: {`author_linkedin_hints[]` {name, affiliation, query_hint}, `github_repos_mentioned[]`, `project_urls_mentioned[]`, `wikipedia_concept_hints[]` (key technical terms for entity linking), `dataset_source_urls[]`, `related_arxiv_ids_mentioned[]` (arXiv IDs explicitly cited)} |
| **🆕 Internal Consistency** | (derived from full text) | `internal_consistency_issues[]` {issue (e.g., "Abstract claims state-of-the-art but Table 3 shows method is second-best on 2 of 4 metrics"), location_a, location_b, severity (minor/moderate/critical)}, `missing_baselines_or_ablations[]` {missing_element (e.g., "No ablation on component B despite claiming B is a key contribution"), importance (critical/recommended/minor)}, `cherry_picking_indicators[]` {indicator (e.g., "Reports precision but not recall", "Evaluates on 5 datasets but only details 2"), severity} |
| **🆕 Writing & Rigor** | (derived from full text) | `writing_quality_assessment` {overall_quality (excellent/good/average/poor), clarity_score (0-1), organization_score (0-1), common_problems[] (verbose_introduction/weak_motivation/missing_limitation_discussion/notation_inconsistency/no_related_work_positioning)}, `experiment_rigor_score` {score (0-10), positive_indicators[] (multiple_datasets/statistical_significance/error_bars/ablation_study/multiple_seeds), negative_indicators[] (single_dataset/no_error_bars/no_ablation/cherry_picked)}, `readability_for_audience` {in_field (easy/moderate/hard), outside_field (easy/moderate/hard), practitioners (easy/moderate/hard), students (easy/moderate/hard)} |
| **🆕 Generative** | (derived from full text) | `follow_up_research_questions[]` (3-5 specific, executable research questions that go beyond the paper's stated future work — LLM identifies gaps and unexplored directions), `practitioner_takeaway` (1-sentence "so what" for engineers: "This research means X is now possible / cheaper / faster for Y use case"), `target_venue_inferred` {venue_guesses[] {venue, confidence, evidence (writing style, page format, citation patterns)}} |
| **🆕 Training Data** | (derived from full text) | `qa_pairs_generated[]` {question, answer, difficulty, source_section} (10-20 Q&A pairs spanning factual, conceptual, and analytical questions about the paper, for scientific QA datasets) |
| **Dedup & Normalization** | `dedup_key` (`arxiv_id`; versioned: `arxiv_id` + `version`), `canonical_url` (normalized to `https://arxiv.org/abs/{id}`) | `url_normalize_regex`: `^https?://(?:www\.)?arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?.*$` → `https://arxiv.org/abs/$1` (also handles old-style IDs: `[a-z-]+/\d{7}`) |

**Sample Record (JSON):**
```json
{
  "arxiv_id": "2401.12345",
  "title": "ZKFlow: Detecting Privacy Leakage in Circom ZK Circuits via Information Flow Analysis",
  "page_count": 14,
  "num_authors": 3,
  "num_figures": 8,
  "submission_comments": "14 pages, 8 figures, accepted at IEEE S&P 2025",
  "journal_ref": null,
  "license": "CC-BY-4.0",
  "venue_mentioned": "IEEE S&P 2025",
  "venue_tier_mapped": "A*",
  "acceptance_status_inferred": "published",
  "tweet_summary": "New tool detects privacy leaks in zero-knowledge circuits — found 23 unknown vulnerabilities across 150+ real-world Circom projects. 94% precision, outperforms taint analysis by 12%. #ZKP #Security",
  "one_line_summary": "A static analysis tool using a novel constraint-circuit information graph (CCIG) to detect witness privacy leakage in Circom ZK circuits.",
  "executive_summary": "Researchers developed an automated tool to find privacy bugs in zero-knowledge proof systems, which are widely used in blockchain and digital identity. Testing on 150+ real-world projects, they discovered 23 previously unknown vulnerabilities. The tool is significantly more accurate than existing approaches.",
  "layman_summary": "Imagine you have a magic envelope that lets you prove you're over 21 without showing your ID — that's essentially what zero-knowledge proofs do. But sometimes these 'magic envelopes' have tiny holes that accidentally leak private information. This paper builds a tool that automatically scans these envelopes for holes. Think of it like a flashlight that shines through the envelope from different angles to find any spots where light (your private data) leaks through. They tested it on over 150 real systems and found 23 previously unknown privacy holes.",
  "review_style_summary": {
    "strengths": ["Novel CCIG representation captures constraint-level information flow that existing tools miss", "Large-scale evaluation on 150+ real projects with ground truth", "23 new vulnerabilities demonstrate practical impact"],
    "weaknesses": ["Limited to Circom circuits; unclear how CCIG generalizes to other ZK frameworks", "No formal soundness proof for the leakage detection algorithm", "Scalability evaluation missing for circuits >10K constraints"],
    "questions": ["How does CCIG handle recursive circuit compositions?", "What is the false negative rate on circuits with intentional information release?"],
    "overall": "Strong systems paper with clear practical value. Main limitation is generalizability beyond Circom."
  },
  "mathematical_complexity_score": 3,
  "novelty_delta_assessment": {
    "novelty_claim": "First information-flow analysis framework specifically designed for ZK circuit privacy",
    "actual_delta": "Genuinely new — prior work applied generic taint analysis without modeling R1CS constraint semantics",
    "closest_prior_work": "Circomspect (static analysis for Circom) focuses on constraint bugs, not privacy leakage"
  },
  "claim_verification_notes": [
    {"claim": "94.2% precision", "evidence_strength": "strong", "evidence_detail": "Table 2 shows per-project breakdown with ground truth labels from manual audit", "potential_issues": "Ground truth limited to 3 auditors; inter-rater agreement not reported"}
  ],
  "methodology_transferability": ["Noir circuits (same R1CS backend)", "Cairo/STARK circuits (similar constraint structure)", "Homomorphic encryption schemes (analogous plaintext leakage problem)"],
  "figures_analyzed": [
    {"figure_id": "fig3", "figure_type": "architecture_diagram", "caption_enhanced": "The CCIG construction pipeline: Circom source → AST → constraint extraction → information flow graph with privacy-sensitive nodes highlighted", "components_identified": ["Parser", "Constraint Extractor", "CCIG Builder", "Leakage Detector"]}
  ],
  "key_equations": [
    {"equation_latex": "\\mathcal{L}(w, x) = \\{c \\in C : \\exists \\text{path}(w_i, x_j) \\text{ via } c\\}", "plain_english_explanation": "The leakage set is all constraints that create an information flow path from a private witness variable to a public input", "equation_role": "definition"}
  ],
  "linkable_identifiers": {
    "author_linkedin_hints": [{"name": "Alice Researcher", "affiliation": "UESTC", "query_hint": "Alice Researcher UESTC cryptography"}],
    "github_repos_mentioned": ["https://github.com/example/zkflow"],
    "wikipedia_concept_hints": ["Zero-knowledge proof", "R1CS", "Circom"],
    "related_arxiv_ids_mentioned": ["2301.04321", "2205.09876"]
  },
  "internal_consistency_issues": [],
  "missing_baselines_or_ablations": [
    {"missing_element": "No evaluation on Noir or Plonky3 circuits despite claiming general applicability to ZK frameworks", "importance": "recommended"}
  ],
  "writing_quality_assessment": {"overall_quality": "good", "clarity_score": 0.82, "organization_score": 0.88, "common_problems": ["notation_inconsistency between Section 3 and 4"]},
  "experiment_rigor_score": {"score": 8, "positive_indicators": ["multiple_datasets (150+ projects)", "ablation_study", "ground_truth_from_manual_audit"], "negative_indicators": ["no_error_bars", "single_run"]},
  "readability_for_audience": {"in_field": "easy", "outside_field": "moderate", "practitioners": "moderate", "students": "hard"},
  "follow_up_research_questions": [
    "Can CCIG be extended to handle recursive circuit compositions (e.g., Nova/Supernova folding schemes)?",
    "What is the false negative rate on circuits with intentional partial information disclosure (e.g., selective disclosure credentials)?",
    "How does CCIG scale to circuits beyond 100K constraints — is there a graph approximation that preserves leakage detection accuracy?"
  ],
  "practitioner_takeaway": "If you're building Circom circuits, this tool can automatically audit your code for privacy leaks before deployment — catching bugs that manual review misses.",
  "target_venue_inferred": {"venue_guesses": [{"venue": "IEEE S&P", "confidence": 0.9, "evidence": "Security-focused, systems paper with vulnerability findings, 14-page format"}]}
}
```

### Use Cases

- **Research Intelligence:** Track emerging research trends, identify breakthrough papers before they go viral, discover interdisciplinary connections, and monitor competitor institutions' research output
- **Literature Review Automation:** Structured contribution/methodology/results extraction enables automated survey generation, gap analysis, and related work discovery; review-style summaries and experiment rigor scoring accelerate peer review triage
- **Research Quality Auditing:** Internal consistency checks, missing baseline detection, cherry-picking indicators, and writing quality assessments help reviewers, editors, and program committees evaluate papers faster and more systematically
- **Academic Knowledge Graphs:** Entity-relationship extraction (author-institution-topic-method-dataset) powers research collaboration networks; linkable identifiers enable author → LinkedIn profile resolution
- **AI/LLM Training:** High-quality scientific reasoning chains, figure-caption pairs, equation explanations, structured Q&A pairs (10-20 per paper), and experiment rigor labels for training models on scientific text understanding
- **Due Diligence:** For VCs and tech scouts — executive summaries, novelty assessments, practitioner takeaways, and methodology transferability analysis reduce paper evaluation time from hours to minutes
- **Education:** Layman summaries, equation explanations, readability assessments, and generated follow-up research questions make cutting-edge research accessible to students and non-specialists

---

## 3. Wikipedia Dataset

### Overview

The world's largest open knowledge base, transformed into a deeply structured knowledge dataset. Our LLM engine goes beyond raw article text — it extracts structured facts, entities, relationships, and temporal events; detects citation gaps, internal contradictions, and content biases; assesses article completeness and source diversity; generates multi-audience summaries, alternative explanations, quiz questions, and section interdependency maps for optimal RAG chunking.

**Total Records:** 60M+ articles across 300+ languages · English: 6.8M+ articles

**Pricing:** Starting at $100 / 100K records · Full language dumps available

### Data Fields


| Category | Standard Fields | 🔥 LLM-Enhanced Fields (Exclusive) |
|----------|----------------|-------------------------------------|
| **Identity** | URL, page_id, title, language, `article_creation_date`, `protection_level` (unprotected/semi-protected/fully-protected) | `title_disambiguated`, `canonical_entity_name`, `entity_type` (person/place/organization/event/concept/thing), `wikidata_id` |
| **Content** | raw_text, HTML, `word_count`, `number_of_sections` | `sections_structured[]` {heading, content, section_type}, `table_of_contents`, `article_summary` (3-5 sentences), `reading_level` (Flesch-Kincaid) |
| **Tables** | (raw HTML tables) | `tables_structured[]`: each table parsed into {table_title, headers[], rows[][], `table_topic`, `data_type` (statistical/comparison/timeline/list)} |
| **Infobox** | `has_infobox` (bool), raw HTML/wikitext | `infobox_structured`: fully typed key-value pairs with standardized field names, e.g., {born: "1990-01-15", nationality: "American", occupation: ["Engineer", "Researcher"]} |
| **Categories** | categories[] (raw Wikipedia cats) | `categories_cleaned[]`, `topic_hierarchy[]`, `domain` (Science/History/Geography/Technology/...), `subject_tags[]` |
| **References** | `references_count`, `external_links_count`, references[] (raw) | `external_links_classified[]` {url, source_type (academic/news/official/...), `reliability_tier`} |
| **Entities** | (not extracted) | `entities_extracted[]`: {name, type (PER/ORG/LOC/DATE/EVENT), `wikidata_id`, `first_mention_context`, `relation_to_subject`} |
| **Facts** | (not extracted) | `structured_facts[]`: {subject, predicate, object, `confidence_score`, `temporal_scope`, `source_sentence`} — ready for knowledge graph ingestion |
| **Timeline** | (not extracted) | `temporal_events[]`: {date, event_description, `event_type` (birth/death/founding/election/discovery/conflict/...), `participants[]`} |
| **Relations** | see_also | `related_entities[]`: {entity, relation_type (part_of/located_in/created_by/member_of/influenced_by/...), `bidirectional`} |
| **Multi-lingual** | (not available) | `cross_language_links` {lang: url}, `translation_coverage_score`, `entity_name_translations` {lang: name} |
| **Embeddings** | (not available) | `article_embedding` (768-dim), `section_embeddings[]` — for semantic retrieval and clustering |
| **🔥 Multimodal (Images)** | images[] (URLs) | `images_annotated[]`: {url, `caption_generated` (if no caption exists, LLM generates one from article context), `depicts[]` (structured list of objects/people/places), `image_type` (photo/diagram/map/chart/logo/flag/artwork/satellite/microscopy), `spatial_description` (composition and layout in 1-2 sentences), `historical_period_depicted` (for historical images), `scientific_annotation` (for diagrams: labeled components and their relationships)} |
| **🔥 Multi-level Summary** | (derived from article text) | `one_line_summary` (≤15 words), `eli5_summary` (explain-like-I'm-5: 2-3 sentences using only common words and analogies), `standard_summary` (3-5 sentences, encyclopedic tone), `academic_summary` (formal, with key dates/figures/citations, suitable for literature reviews), `key_takeaways[]` (3-5 bullet-point facts a reader should remember) |
| **🔥 Educational** | (derived from article text) | `prerequisite_concepts[]` {concept_name, `wikipedia_title_hint`, `why_needed` (1-sentence explanation)}, `difficulty_level` (elementary/middle_school/high_school/undergraduate/graduate/expert), `quiz_questions_generated[]` {question, answer, difficulty, question_type (factual/conceptual/analytical), `distractor_answers[]` (3 plausible wrong answers for MCQ)}, `common_misconceptions[]` {misconception, correction, evidence_from_article} |
| **🔥 Bias & Neutrality** | (derived from article text) | `bias_detection[]` {section_heading, `bias_type` (geographic_bias/temporal_bias/western_centrism/gender_bias/corporate_bias/political_lean), `evidence_quote_location` (paragraph index), `severity` (minor/moderate/significant), `suggested_neutral_framing`}, `missing_perspectives[]` (viewpoints or regions underrepresented), `weasel_words_detected[]` {phrase, location, issue (e.g., "some experts say" — which experts?)} |
| **🔥 Content Freshness** | (derived from article text) | `information_freshness_score` (0-1 based on: most recent date mentioned in text, proportion of references from last 5 years, presence of "as of [year]" markers), `potentially_outdated_claims[]` {claim, date_context, reason_suspect}, `temporal_coverage_gap` (latest year covered vs. current year) |
| **🔥 Cross-dataset Linkable IDs** | (extracted from article text) | `linkable_identifiers`: {`arxiv_paper_hints[]` (paper titles or DOIs mentioned in references), `linkedin_person_hints[]` {name, role, organization}, `amazon_product_hints[]` (product names, brands, ISBN numbers mentioned), `external_database_ids` {imdb_id, isbn, doi[], patent_numbers[], official_website}} |
| **🆕 Internal Consistency** | (derived from article text) | `citation_needed_gaps[]` {claim, paragraph_index, claim_type (statistical/historical/scientific/attributive), importance (critical/moderate/minor)}, `internal_contradictions[]` {contradiction, location_a, location_b, severity}, `infobox_text_consistency` {mismatches[] {field, infobox_value, text_value}} |
| **🆕 Completeness & Sources** | (derived from article text) | `article_completeness_assessment` {expected_sections_missing[] (e.g., "Criticism" for political topic, "Safety" for chemical compound, "Reception" for film), overall_completeness_score (0-1)}, `source_diversity_assessment` {source_type_distribution {academic, news, government, corporate, self_published}, geographic_diversity_score, over_reliance_on_single_source (bool + details)} |
| **🆕 Advanced Educational** | (derived from article text) | `alternative_explanations[]` {approach (analogy/visual_metaphor/historical_narrative/example_based), explanation_text} (2-3 different ways to explain the core concept), `controversy_map` (for disputed topics: {positions[] {stance, supporting_arguments[], key_proponents[]}}), `section_interdependency_map[]` {section_a, section_b, dependency_type (prerequisite/extends/contradicts/exemplifies)} (for RAG chunking: which sections must be retrieved together) |
| **🆕 Training Data** | (derived from article text) | `qa_pairs_generated[]` {question, answer, difficulty, question_type} (10-15 Q&A pairs per article for RAG/instruction tuning — distinct from quiz_questions: these are open-ended, not MCQ) |
| **Dedup & Normalization** | `dedup_key` (`page_id` + `language`; cross-language: `wikidata_id`), `canonical_url` (normalized article URL) | `url_normalize_regex`: `^https?://([a-z]{2,3}(?:-[a-z]+)?)\.(?:m\.)?wikipedia\.org/wiki/([^?#]+).*$` → `https://$1.wikipedia.org/wiki/$2` (strips mobile `.m.`, query params, hash fragments) |

**Sample Record (JSON):**
```json
{
  "page_id": 12345,
  "title": "Zero-knowledge proof",
  "article_creation_date": "2004-03-15",
  "protection_level": "semi-protected",
  "word_count": 8432,
  "number_of_sections": 12,
  "references_count": 47,
  "external_links_count": 8,
  "has_infobox": false,
  "entity_type": "concept",
  "wikidata_id": "Q899379",
  "one_line_summary": "A cryptographic method to prove a statement is true without revealing any information beyond its validity.",
  "eli5_summary": "Imagine you want to prove to your friend that you know the secret password to a clubhouse, but you don't want to say the password out loud. A zero-knowledge proof is like showing you can open the door without your friend ever hearing what the password is.",
  "academic_summary": "Zero-knowledge proofs (ZKPs), introduced by Goldwasser, Micali, and Rackoff in 1985, are interactive proof protocols where a prover convinces a verifier of a statement's truth without conveying any information beyond the statement's validity. The concept has evolved into practical constructions including zk-SNARKs and zk-STARKs, with applications in blockchain privacy (Zcash, 2016), identity verification, and verifiable computation.",
  "key_takeaways": [
    "Invented in 1985 by Goldwasser, Micali, and Rackoff",
    "Proves truth without revealing underlying information",
    "Key variants: zk-SNARKs (succinct, trusted setup) and zk-STARKs (transparent, post-quantum)",
    "Major applications in blockchain privacy and digital identity",
    "Foundational concept in computational complexity theory"
  ],
  "prerequisite_concepts": [
    {"concept_name": "Interactive proof system", "wikipedia_title_hint": "Interactive proof system", "why_needed": "ZKPs are a special case of interactive proofs where the verifier learns nothing beyond the statement's truth"},
    {"concept_name": "Computational complexity", "wikipedia_title_hint": "Computational complexity theory", "why_needed": "ZKP security relies on computational hardness assumptions"}
  ],
  "difficulty_level": "undergraduate",
  "quiz_questions_generated": [
    {"question": "Who introduced zero-knowledge proofs, and in what year?", "answer": "Shafi Goldwasser, Silvio Micali, and Charles Rackoff in 1985", "difficulty": "factual", "distractor_answers": ["Adi Shamir in 1979", "Whitfield Diffie and Martin Hellman in 1976", "Ralph Merkle in 1982"]}
  ],
  "common_misconceptions": [
    {"misconception": "Zero-knowledge proofs hide the statement being proved", "correction": "The statement itself is public; what's hidden is the witness (the evidence/secret that makes the statement true)", "evidence_from_article": "Section 'Definition' clarifies the distinction between statement and witness"}
  ],
  "bias_detection": [
    {"section_heading": "Applications", "bias_type": "western_centrism", "severity": "minor", "suggested_neutral_framing": "Section focuses heavily on US/European blockchain projects; Chinese and Korean ZKP applications are underrepresented"}
  ],
  "information_freshness_score": 0.72,
  "potentially_outdated_claims": [
    {"claim": "Zcash is the primary production use of zk-SNARKs", "date_context": "as of 2020", "reason_suspect": "zkSync, Scroll, and Polygon zkEVM have since launched with larger-scale zk-SNARK usage"}
  ],
  "images_annotated": [
    {"url": "...", "depicts": ["Ali Baba cave diagram"], "image_type": "diagram", "scientific_annotation": "Illustrates the classic Ali Baba cave analogy: prover enters randomly from A or B, verifier requests exit from a specific side, repeated trials establish knowledge without revealing the path choice"}
  ],
  "linkable_identifiers": {
    "arxiv_paper_hints": ["The Knowledge Complexity of Interactive Proof-Systems (Goldwasser et al., 1985)"],
    "linkedin_person_hints": [{"name": "Shafi Goldwasser", "role": "Professor", "organization": "MIT / Weizmann Institute"}],
    "external_database_ids": {"official_website": null, "doi": []}
  },
  "citation_needed_gaps": [
    {"claim": "ZK proofs are increasingly used in supply chain verification", "paragraph_index": 8, "claim_type": "attributive", "importance": "moderate"}
  ],
  "internal_contradictions": [],
  "infobox_text_consistency": {"mismatches": []},
  "article_completeness_assessment": {
    "expected_sections_missing": ["Implementations (list of major ZKP libraries/frameworks)", "Performance comparison (proving time, verification time benchmarks)"],
    "overall_completeness_score": 0.78
  },
  "source_diversity_assessment": {
    "source_type_distribution": {"academic": 32, "news": 5, "government": 0, "corporate": 7, "self_published": 3},
    "geographic_diversity_score": 0.45,
    "over_reliance_on_single_source": false
  },
  "alternative_explanations": [
    {"approach": "analogy", "explanation_text": "A zero-knowledge proof is like proving you know where Waldo is by covering the entire page except Waldo with a large sheet of paper — the verifier sees Waldo but learns nothing about where he is on the page."},
    {"approach": "example_based", "explanation_text": "Imagine a color-blind friend and two balls, one red and one green. You can prove they're different colors by having your friend hide them behind their back, swap or not swap, and show you one — you always correctly say whether they swapped, proving the colors differ without revealing which is which."}
  ],
  "controversy_map": null,
  "section_interdependency_map": [
    {"section_a": "Definition", "section_b": "Applications", "dependency_type": "prerequisite"},
    {"section_a": "Variants (zk-SNARKs)", "section_b": "Applications (Zcash)", "dependency_type": "exemplifies"}
  ]
}
```

### Use Cases

- **Knowledge Graph Construction:** Pre-extracted SPO triples, entity typing, cross-article relation linking, and infobox-text consistency validation enable rapid, high-quality knowledge graph population
- **RAG Pipeline Foundation:** Section-level embeddings + structured facts + multi-level summaries + section interdependency maps (which sections must be retrieved together) provide high-precision retrieval for LLM grounding
- **AI/LLM Training:** Clean structured world knowledge with multi-level granularity, quiz Q&A pairs and open-ended Q&A pairs for instruction tuning, bias-annotated text for alignment training, alternative explanations for diverse reasoning, and image-text pairs for multimodal models
- **Education Technology:** ELI5 summaries, prerequisite concept chains, auto-generated quizzes with distractors, multiple alternative explanations, misconception corrections, and controversy maps for adaptive learning systems
- **Content Auditing:** Citation-needed gap detection, internal contradiction flagging, source diversity analysis, article completeness assessment, bias detection, freshness scoring, and weasel-word flagging for Wikipedia editors and fact-checkers
- **Cross-dataset Analytics:** Link Wikipedia concepts to arXiv papers, mentioned people to LinkedIn profiles, and products to Amazon listings via extracted identifiers

---

## 4. Amazon Product Dataset

### Overview

The most comprehensive e-commerce intelligence dataset, covering product listings, reviews, seller profiles, and pricing dynamics across all Amazon marketplaces. Our LLM engine transforms raw product pages into deep market intelligence — detecting spec-description mismatches and misleading claims, inferring buyer personas from Q&A, analyzing product images for listing quality, scoring review authenticity and diagnosing complaint root causes, generating buyer-facing FAQs and competitive comparison frameworks, and producing cross-dataset identifiers linking brands to LinkedIn companies and Wikipedia articles.

**Total Records:** 270M+ products · 1B+ reviews · 10M+ sellers · 20+ marketplaces

**Pricing:** Starting at $250 / 100K records · Subscription with daily/weekly refresh

### Sub-Datasets

#### 4.1 Amazon Products Dataset

**270M+ records**


| Category | Standard Fields | 🔥 LLM-Enhanced Fields (Exclusive) |
|----------|----------------|-------------------------------------|
| **Identity** | ASIN, URL, title, brand, seller_name, seller_id | `title_cleaned` (remove keyword stuffing), `brand_standardized` (canonical brand name), `is_brand_official_store` |
| **Pricing** | initial_price, final_price, currency, discount, `coupon_available` (bool), `subscribe_and_save_available` (bool) | `price_tier` (budget/mid/premium/luxury), `deal_quality_score`, `price_signals_on_page` (extracted "was $X", "save X%", "lowest price in 30 days" etc.) |
| **Description** | description (raw HTML), bullet_points, features | `features_structured[]` {feature_name, feature_value, feature_unit}, `key_specs_table`, `use_cases_extracted[]`, `target_audience_inferred` |
| **Category** | categories[], breadcrumbs, category_tree | `category_standardized` (mapped to Google Product Taxonomy / UNSPSC), `niche_tags[]`, `seasonal_relevance` |
| **Ranking** | `best_sellers_rank` (BSR by category), `sales_volume_hint` (e.g., "10K+ bought in past month" — if displayed) | `competitive_position` {rank_in_category, top_competitors[] (from "customers also viewed" on page)}, `listing_quality_score`, `seo_keyword_density` |
| **Visual** | images[], main_image | `image_count`, `has_lifestyle_images`, `has_infographic`, `has_video`, `visual_quality_score` |
| **Availability** | availability, stock_status | `fulfillment_type` (FBA/FBM/AMZ), `shipping_speed_tier`, `prime_eligible` |
| **Reviews Summary** | reviews_count, rating, `answered_questions_count` | `recent_rating_signal` (improving/stable/declining — inferred from visible recent review scores), `review_pattern_risk_indicators` (based on visible review patterns: burst timing, generic language, unverified ratio) |
| **Variants** | sizes[], colors[], styles[] | `variant_matrix_structured` {dimension: [values]}, `best_seller_variant`, `variant_price_range` |
| **Product Details** | `date_first_available`, `product_dimensions`, `product_weight`, `warranty_info`, `a_plus_content_present` (bool) | `certifications_mentioned[]`, `country_of_origin`, `material_composition_extracted`, `safety_warnings[]` |
| **Related Products** | `frequently_bought_together[]` {asin, title}, `customers_also_viewed[]` {asin, title} | `cross_sell_category_hints[]` (complementary product categories inferred from use cases, e.g., headphones → headphone stand, carrying case) |
| **🔥 Multimodal (Product Images)** | images[] (URLs), main_image | `main_image_analysis` {background_type (white/lifestyle/composite), `product_clearly_visible`, `image_resolution_adequate`, `product_angle` (front/side/top/360/in-use)}, `all_images_analysis[]` {image_type (hero/lifestyle/infographic/size_chart/comparison/packaging/closeup), `text_extracted_from_image`, `scene_description`}, `image_text_consistency_score` (do claims in images match the text description?), `listing_visual_completeness` {has_hero, has_lifestyle, has_infographic, has_size_reference, has_packaging, `missing_recommended[]`} |
| **🔥 Multi-level Summary** | (derived from title + description + features) | `buyer_quick_take` (1-sentence: "Best for X who need Y at Z price point"), `product_elevator_pitch` (3-sentence clear product description), `seller_competitive_brief` (how this product positions against competitors mentioned/linked on the page), `seo_optimized_description` (rewritten product description optimized for search) |
| **🔥 Market Positioning** | (derived from description + features + pricing) | `product_lifecycle_stage_inferred` (new_launch/growth/mature/declining — based on: date_first_available, review count, discount depth, variant breadth), `lifecycle_evidence`, `unique_selling_points[]` (features explicitly highlighted as differentiators in the listing), `purchase_decision_factors_from_listing[]` {factor, prominence_in_listing (featured/mentioned/buried), value_claim} |
| **🔥 Listing Quality** | (derived from all listing content) | `listing_optimization_score` (0-100 composite), `listing_issues_detected[]` {issue (title_keyword_stuffing/missing_bullet_points/no_brand_story/poor_image_count/inconsistent_specs/vague_description), severity, `fix_suggestion`}, `listing_completeness` {title_quality, bullet_point_quality, description_quality, image_quality, a_plus_content_present} |
| **🔥 Cross-dataset Linkable IDs** | (extracted from listing) | `linkable_identifiers`: {`brand_website_url` (from brand info section), `brand_linkedin_search_hint`, `wikipedia_product_hint`, `patent_numbers_mentioned[]`, `certification_bodies_mentioned[]` (UL, CE, FCC, etc.), `upc_ean_isbn` (if present), `manufacturer_model_number`} |
| **🆕 Listing Integrity** | (derived from description + specs + images) | `spec_description_mismatch[]` {field, description_claim, spec_value, severity (e.g., bullet says "20-hour battery" but spec table says 18 hours)}, `misleading_claim_flags[]` {claim, flag_type (vague_superlative/unsubstantiated_certification/narrow_category_ranking/ambiguous_comparison), reasoning}, `title_description_coherence_score` (0-1: do title keywords match the actual product description content?) |
| **🆕 Buyer Intelligence** | (derived from Q&A + description + features) | `buyer_persona_from_qa` {personas_detected[] (e.g., international_buyer/parent/technical_user/gift_buyer), evidence_questions[]}, `return_risk_indicators` {risk_factors[] (vague_sizing/complex_installation/expectation_mismatch/fragile_shipping), risk_level (low/medium/high)}, `gift_potential_score` (0-1 based on price range, packaging mentions, gift-related Q&A frequency) |
| **🆕 Generative** | (derived from description + Q&A) | `customer_faq_generated[]` (5 questions buyers are likely to ask but haven't been answered yet — based on ambiguities in the listing, e.g., {question: "Does this work with 220V power outlets?", reasoning: "Product lists US plug type but no voltage info"}), `product_comparison_dimensions[]` (key dimensions for comparing against "customers also viewed" competitors: {dimension, this_product_value, comparison_note}) |
| **Dedup & Normalization** | `dedup_key` (`asin` + `marketplace`), `canonical_url` (normalized product URL) | `url_normalize_regex`: `^https?://(?:www\.)?amazon\.(com|co\.uk|de|...)/(?:.*/)?(dp|gp/product)/([A-Z0-9]{10})(?:[/?#].*)?$` → `https://www.amazon.$1/dp/$3` (strips SEO slug, query params, `/ref=` suffix) |

#### 4.2 Amazon Reviews Dataset

**1B+ records**


| Category | Standard Fields | 🔥 LLM-Enhanced Fields (Exclusive) |
|----------|----------------|-------------------------------------|
| **Identity** | review_id, ASIN, URL, author_name, author_id, `variant_purchased` (specific size/color/model), `review_country` / `marketplace` | `reviewer_profile_type` (power_reviewer/verified_buyer/one_time/suspicious) |
| **Content** | rating, review_text, review_headline, date_posted | `sentiment_overall` (positive/negative/mixed/neutral), `sentiment_aspects[]` {aspect, sentiment, detail} |
| **Analysis** | (not available) | `product_pros_extracted[]`, `product_cons_extracted[]`, `feature_satisfaction_map` {feature: rating}, `use_case_mentioned`, `comparison_to_alternatives[]` {product, advantage/disadvantage} |
| **Quality** | helpful_count, verified_purchase | `review_quality_score`, `review_type` (detailed_analysis/brief_opinion/complaint/praise/question), `authenticity_score`, `information_density` |
| **Structured** | (not available) | `issues_reported[]` {issue, severity, product_component}, `customer_segment_inferred` (professional/hobbyist/first_time/gift_buyer), `purchase_context` (personal/business/gift) |
| **Seller Response** | `seller_response` (seller's reply text, if present) | `seller_response_quality` (helpful/generic/defensive/absent), `issue_resolution_status` (resolved/unresolved/partial — inferred from response text) |
| **Media** | review_images[] | `image_content_described[]`, `shows_product_in_use`, `shows_defect` |
| **🔥 Multimodal (Review Images)** | review_images[] | `review_image_analysis[]` {image_type (product_in_use/defect_photo/comparison/unboxing/size_reference), `defect_described`, `usage_context_shown` (home/office/outdoor/gym/...), `matches_review_text`} |
| **🔥 Multi-level Summary** | (derived from review_text) | `review_one_liner` (1-sentence distillation of the review's key verdict), `purchase_decision_factor` (the single most important factor this reviewer based their opinion on) |
| **🔥 Review Depth** | (derived from review_text) | `usage_duration_mentioned`, `expertise_level_inferred` (novice/intermediate/expert), `actionable_feedback[]` (specific constructive suggestions), `competitor_products_mentioned[]` |
| **🆕 Review Integrity** | (derived from review_text + rating) | `review_text_rating_mismatch` {mismatch_detected (bool), mismatch_type (positive_text_low_rating/negative_text_high_rating/logistics_not_product), evidence}, `sponsored_review_indicators` {likelihood (low/medium/high), indicators[] (disclosure_present/overly_formatted/mentions_free_product/generic_praise_pattern)} |
| **🆕 Problem Analysis** | (derived from review_text) | `temporal_context_of_opinion` {usage_duration_inferred, opinion_maturity (first_impression/short_term/long_term)}, `problem_root_cause_inferred` (when review reports issues: {problem_reported, root_cause_category (manufacturing_defect/design_flaw/sizing_info_gap/user_error/shipping_damage), confidence}) |
| **Dedup & Normalization** | `dedup_key` (`review_id` + `marketplace`), `canonical_url` (normalized review URL) | `url_normalize_regex`: `^https?://(?:www\.)?amazon\.(com|co\.uk|de|...)/gp/customer-reviews/([A-Z0-9]+)(?:[/?#].*)?$` → `https://www.amazon.$1/gp/customer-reviews/$2` |

#### 4.3 Amazon Sellers Dataset

**10M+ records**


| Category | Standard Fields | 🔥 LLM-Enhanced Fields (Exclusive) |
|----------|----------------|-------------------------------------|
| **Identity** | seller_id, URL, seller_name, seller_email, seller_phone | `seller_type` (brand_owner/reseller/arbitrage/manufacturer/dropshipper), `business_name_registered` |
| **Performance** | stars, feedbacks, return_policy | `seller_health_score`, `response_time_tier`, `dispute_rate_estimated` |
| **Storefront** | (from seller page) | `brands_featured_on_storefront[]`, `category_focus[]`, `price_range` |
| **Business Intel** | description, detailed_info | `years_on_amazon`, `geographic_focus`, `fulfillment_strategy` |
| **🔥 Multi-level Summary** | (derived from description + detailed_info) | `seller_one_liner` (e.g., "Mid-size electronics reseller specializing in audio accessories, 4.5★ rating"), `seller_profile_narrative` (2-paragraph business profile) |
| **🔥 Cross-dataset Linkable IDs** | (extracted from description) | `linkable_identifiers`: {`seller_website_url`, `linkedin_company_search_hint`, `brands_featured_on_storefront[]`} |
| **🆕 Seller Intelligence** | (derived from description + return policy) | `seller_legitimacy_signals` {positive_signals[] (clear_return_policy/brand_authorization_claimed/physical_address/customer_service_details), negative_signals[] (no_description/generic_text/grammar_issues/no_contact_info), legitimacy_score (0-1)}, `seller_origin_country_inferred` {country, confidence, evidence (name format, description style, return policy wording)} |
| **Dedup & Normalization** | `dedup_key` (`seller_id` + `marketplace`), `canonical_url` (normalized seller URL) | `url_normalize_regex`: `^https?://(?:www\.)?amazon\.(com|co\.uk|de|...)/(?:sp|shops/seller)\?(?:.*&)?(?:seller|merchant)=([A-Z0-9]+)(?:&.*)?$` → `https://www.amazon.$1/sp?seller=$2` |

**Sample Product Record (JSON):**
```json
{
  "asin": "B0EXAMPLE1",
  "title_cleaned": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
  "brand_standardized": "Sony",
  "best_sellers_rank": {"Electronics": 45, "Over-Ear Headphones": 2},
  "sales_volume_hint": "10K+ bought in past month",
  "date_first_available": "2022-05-20",
  "product_weight": "250 g",
  "product_dimensions": "7.3 x 3.1 x 9.5 inches",
  "warranty_info": "1-year manufacturer warranty",
  "a_plus_content_present": true,
  "coupon_available": false,
  "subscribe_and_save_available": false,
  "answered_questions_count": 842,
  "frequently_bought_together": [
    {"asin": "B0FBT1234", "title": "Replacement Ear Pads for WH-1000XM5"},
    {"asin": "B0FBT5678", "title": "Headphone Stand Aluminum"}
  ],
  "customers_also_viewed": [
    {"asin": "B0BOSEQC", "title": "Bose QuietComfort Ultra Headphones"},
    {"asin": "B0AIRPODS", "title": "Apple AirPods Max"}
  ],
  "buyer_quick_take": "Best for frequent travelers who want industry-leading noise cancellation at a premium price point.",
  "product_elevator_pitch": "Sony's flagship wireless headphones with adaptive noise canceling that automatically adjusts to your environment. 30-hour battery life with quick charge (3 min for 3 hours). Lightweight at 250g with multipoint connection for switching between devices.",
  "seller_competitive_brief": "Positioned at +65% vs. category average. Page links to Bose QC Ultra (similar price, heavier), AirPods Max (higher price, Apple ecosystem lock-in), and Sennheiser Momentum 4 (lower price, less effective ANC per listing claims). Key differentiation: lightest in class + longest battery life.",
  "main_image_analysis": {
    "background_type": "white",
    "product_clearly_visible": true,
    "product_angle": "front"
  },
  "image_text_consistency_score": 0.95,
  "listing_visual_completeness": {
    "has_hero": true, "has_lifestyle": true, "has_infographic": true,
    "has_size_reference": false, "has_packaging": true,
    "missing_recommended": ["size_reference_image"]
  },
  "product_lifecycle_stage_inferred": "mature",
  "lifecycle_evidence": "date_first_available 3 years ago, high review count (15K+), stable pricing with periodic discounts, full variant range (5 colors)",
  "unique_selling_points": ["Industry-leading noise cancellation", "30-hour battery life", "Multipoint connection", "250g lightweight design"],
  "listing_optimization_score": 88,
  "listing_issues_detected": [
    {"issue": "missing_size_reference_image", "severity": "low", "fix_suggestion": "Add image showing headphones next to common object for size context"}
  ],
  "price_tier": "premium",
  "price_signals_on_page": ["Save 12%", "List Price: $399.99"],
  "features_structured": [
    {"feature_name": "Driver Size", "feature_value": "30", "feature_unit": "mm"},
    {"feature_name": "Battery Life", "feature_value": "30", "feature_unit": "hours"},
    {"feature_name": "Noise Canceling", "feature_value": "Adaptive", "feature_unit": null},
    {"feature_name": "Weight", "feature_value": "250", "feature_unit": "g"}
  ],
  "linkable_identifiers": {
    "brand_linkedin_search_hint": "Sony Corporation electronics",
    "wikipedia_product_hint": "Sony WH-1000XM5",
    "manufacturer_model_number": "WH1000XM5/B",
    "certification_bodies_mentioned": ["FCC"]
  },
  "spec_description_mismatch": [],
  "misleading_claim_flags": [
    {"claim": "#1 Best Seller", "flag_type": "narrow_category_ranking", "reasoning": "Best seller rank is in 'Over-Ear Headphones' subcategory, not overall Electronics"}
  ],
  "title_description_coherence_score": 0.92,
  "buyer_persona_from_qa": {
    "personas_detected": ["frequent_traveler", "remote_worker", "audiophile"],
    "evidence_questions": ["Does noise canceling work on airplanes?", "Can I use this on Zoom calls?", "How does the sound quality compare to wired headphones?"]
  },
  "return_risk_indicators": {"risk_factors": ["subjective_comfort_fit"], "risk_level": "low"},
  "gift_potential_score": 0.75,
  "customer_faq_generated": [
    {"question": "Can I use these headphones while charging?", "reasoning": "No mention of play-while-charging in description or specs"},
    {"question": "Are replacement ear pads available from Sony?", "reasoning": "Product is 3 years old; ear pad degradation is common but no info on replacements"}
  ],
  "product_comparison_dimensions": [
    {"dimension": "weight", "this_product_value": "250g", "comparison_note": "Lightest in class vs. Bose QC Ultra (260g) and AirPods Max (385g)"},
    {"dimension": "battery_life", "this_product_value": "30 hours", "comparison_note": "Longest vs. Bose (24h) and AirPods Max (20h)"},
    {"dimension": "multipoint", "this_product_value": "Yes", "comparison_note": "AirPods Max lacks multipoint connection"}
  ]
}
```

### Use Cases

- **Competitive Intelligence:** Real-time pricing monitoring, BSR tracking, competitive positioning via "customers also viewed", feature gap analysis, structured comparison dimension extraction, and visual listing quality benchmarking
- **Product Development:** Structured feature satisfaction data, purchase decision factors, actionable review feedback, root cause analysis of product complaints, and competitor mention tracking from reviews
- **Listing Optimization:** Automated listing quality scoring, spec-description mismatch detection, misleading claim flagging, image completeness assessment, text-image consistency checks, and auto-generated FAQs to preempt buyer questions
- **Seller Intelligence:** Identify high-performing sellers, detect counterfeit/gray market sellers via legitimacy scoring, infer seller origin country, and track seller specialization via storefront brand analysis
- **Review Quality Assurance:** Detect text-rating mismatches, identify sponsored review patterns, assess review temporal context (first impression vs. long-term use), and infer root causes of reported problems
- **Demand Forecasting:** BSR-based sales estimation, product lifecycle stage assessment, seasonal relevance scoring, buyer persona identification from Q&A, and gift potential scoring
- **Cross-dataset Analytics:** Link brands to LinkedIn company profiles, products to Wikipedia articles, and patent numbers to inventor profiles via extracted identifiers
- **AI/LLM Training:** Product understanding, image-text consistency pairs, review sentiment with aspect-level granularity, spec-description mismatch labels, and e-commerce reasoning for shopping assistants

---

## Delivery & Format

### Data Formats

| Format | Best For |
|--------|----------|
| JSON | API integration, document stores |
| NDJSON / JSON Lines | Streaming pipelines, large-scale processing |
| CSV | Spreadsheet analysis, simple imports |
| Parquet | Data warehouses, ML pipelines, columnar analytics |
| XLSX | Business users, quick analysis |

### Delivery Methods

| Method | Description |
|--------|-------------|
| **API Download** | RESTful API with snapshot management |
| **Amazon S3** | Direct delivery to your S3 bucket |
| **Google Cloud Storage** | GCS bucket delivery |
| **Snowflake** | Direct Snowflake table ingestion |
| **Azure Blob** | Azure storage delivery |
| **Webhook** | Push notification on snapshot completion |
| **SFTP** | Secure file transfer |
| **Email** | Download link delivery (< 5GB) |

### Update Frequency

All datasets support customizable refresh schedules: **Real-time** (streaming) · **Daily** · **Weekly** · **Monthly** · **Quarterly** · **One-time**

### API Quick Start

```python
import requests

# Trigger a new dataset snapshot
response = requests.post(
    "https://api.yourplatform.com/datasets/v3/trigger",
    headers={"Authorization": "Bearer YOUR_API_TOKEN"},
    json={
        "dataset_id": "ds_linkedin_profiles",
        "filters": {
            "country_code": "US",
            "seniority_level": ["C-suite", "VP", "Director"],
            "industry_standardized": "Technology"
        },
        "fields": ["name", "standardized_job_title", "experience_structured", "skills_extracted",
                   "recruiter_brief", "open_to_work", "linkable_identifiers", "avatar_quality_assessment"],
        "format": "parquet"
    }
)
snapshot_id = response.json()["snapshot_id"]

# Download when ready
data = requests.get(
    f"https://api.yourplatform.com/datasets/snapshots/{snapshot_id}/download",
    headers={"Authorization": "Bearer YOUR_API_TOKEN"}
)
```

```javascript
const response = await fetch("https://api.yourplatform.com/datasets/v3/trigger", {
  method: "POST",
  headers: {
    "Authorization": "Bearer YOUR_API_TOKEN",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    dataset_id: "ds_amazon_products",
    filters: {
      category_standardized: "Electronics > Audio > Headphones",
      listing_optimization_score_max: 60
    },
    fields: ["asin", "title_cleaned", "listing_optimization_score",
             "listing_issues_detected", "image_text_consistency_score",
             "best_sellers_rank", "product_lifecycle_stage_inferred"],
    format: "ndjson"
  })
});
```

---

## What Sets Us Apart: LLM-Enhanced Data Intelligence

| Capability | Traditional Providers | Our Platform |
|------------|----------------------|--------------|
| **Raw Field Extraction** | ✅ Structured fields from HTML | ✅ Same capability |
| **Semantic Understanding** | ❌ Raw text only | ✅ Extracts meaning from unstructured text |
| **Entity Recognition** | ❌ or basic regex | ✅ Context-aware NER across 50+ languages |
| **Relationship Extraction** | ❌ | ✅ SPO triples, citation graphs, entity relations |
| **Classification & Taxonomy** | ❌ or manual mapping | ✅ Automatic mapping to standard taxonomies (O*NET, NAICS, Google Product, arXiv) |
| **Multi-level Summarization** | ❌ | ✅ Per-record summaries at 4-6 granularity levels (tweet → layman → executive → technical → review) |
| **Multi-audience Summaries** | ❌ | ✅ Same record, different briefs: recruiter / investor / buyer / compliance officer |
| **Multimodal Analysis** | ❌ | ✅ Product image scoring, paper figure analysis, avatar quality assessment, review photo classification |
| **Cross-dataset Linkable IDs** | ❌ | ✅ Per-record extraction of identifiers (GitHub URLs, ORCID, brand domains) for downstream entity resolution across all datasets |
| **Embeddings** | ❌ | ✅ Pre-computed vectors for semantic search |
| **🆕 Internal Consistency Detection** | ❌ | ✅ Profile contradiction flagging, paper claim-vs-evidence checks, spec-description mismatch detection, infobox-text consistency validation |
| **🆕 Credibility & Integrity Scoring** | ❌ | ✅ Profile credibility assessment, review authenticity scoring, sponsored review detection, seller legitimacy scoring, misleading claim flagging |
| **🆕 Intent & Motivation Inference** | ❌ | ✅ Career motivation signals, posting intent, buyer persona inference from Q&A, company stage signals, return risk prediction |
| **🆕 Generative Augmentation** | ❌ | ✅ Cold outreach hooks, interview questions, customer FAQ generation, alternative explanations, follow-up research questions, practitioner takeaways |
| **🆕 Per-record Q&A Pair Generation** | ❌ | ✅ 5-20 structured Q&A pairs per record for RAG fine-tuning and instruction tuning datasets |
| **Bias & Quality Auditing** | ❌ | ✅ Wikipedia bias detection, citation-needed gap detection, article completeness assessment, source diversity analysis, listing quality scoring |
| **Educational Content Generation** | ❌ | ✅ ELI5 summaries, prerequisite chains, quiz Q&A with distractors, alternative explanations, misconception corrections, controversy maps |
| **Research Rigor Assessment** | ❌ | ✅ Experiment rigor scoring, missing baseline detection, cherry-picking indicators, writing quality assessment, readability-for-audience profiling |
| **Risk Scoring** | ❌ or rule-based | ✅ LLM-powered multi-signal risk indicators |
| **Quality Assurance** | Basic validation | ✅ LLM-powered consistency checks + confidence scores |

---

## Cross-Dataset Entity Resolution

Our **linkable identifiers** system enables downstream entity resolution without requiring LLM to process multiple records. Each record independently extracts identifiers that can be joined in post-processing:

| Source Record | Extracts | Links To |
|---------------|----------|----------|
| LinkedIn Profile | `github_urls`, `arxiv_author_query_hint`, `publication_titles_mentioned`, `company_domains_mentioned` | arXiv papers (by author name + affiliation), GitHub repos, Amazon sellers (by company domain) |
| LinkedIn Company | `website_domain`, `amazon_seller_search_hint`, `wikipedia_entity_hint`, `github_org_url` | Amazon sellers (by brand name), Wikipedia articles (by company name), GitHub orgs |
| arXiv Paper | `author_linkedin_hints`, `github_repos_mentioned`, `wikipedia_concept_hints`, `related_arxiv_ids_mentioned` | LinkedIn profiles (by author name), Wikipedia articles (by concept), GitHub repos |
| Wikipedia Article | `arxiv_paper_hints`, `linkedin_person_hints`, `amazon_product_hints`, `external_database_ids` | arXiv papers (by title/DOI), LinkedIn profiles (by person name), Amazon products (by product/ISBN) |
| Amazon Product | `brand_linkedin_search_hint`, `wikipedia_product_hint`, `patent_numbers_mentioned`, `manufacturer_model_number` | LinkedIn companies (by brand), Wikipedia articles (by product/brand), Patent databases |
| Amazon Seller | `seller_website_url`, `linkedin_company_search_hint`, `brands_featured_on_storefront` | LinkedIn companies, Brand Wikipedia pages |

Customers can use simple join logic (exact match on URLs, fuzzy match on names) to build cross-dataset entity graphs. We provide reference join scripts in Python and SQL.

---

## Compliance & Ethics

- All data sourced from publicly accessible information
- Compliant with GDPR, CCPA, and applicable data protection regulations
- Personal data anonymization and pseudonymization options available
- Regular compliance audits and legal review
- Customizable data retention and deletion policies
- Transparent data sourcing methodology documentation

---

*Contact: sales@yourplatform.com · API Docs: docs.yourplatform.com · Request Custom Dataset: custom@yourplatform.com*
