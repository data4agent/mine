# Dataset Reference

Mine currently supports four platform families across nine datasets. Schemas are fetched from the platform API and define required fields, dedup keys, and URL normalization rules.

## Dataset Inventory

| # | Dataset ID | Platform | dedup_key | Required Fields | Total Fields | Crawler Type |
|---|---|---|---|---|---|---|
| 1 | `linkedin_profiles` | LinkedIn | `linkedin_num_id` | 5 | 91 | profile |
| 2 | `linkedin_company` | LinkedIn | `company_id` | 5 | 41 | company |
| 3 | `linkedin_jobs` | LinkedIn | `job_posting_id` | 5 | 44 | job |
| 4 | `linkedin_posts` | LinkedIn | `post_id` | 4 | 38 | post |
| 5 | `arxiv` | arXiv | `arxiv_id` (versioned) | 4 | 88 | paper |
| 6 | `wikipedia` | Wikipedia | `page_id + language` | 5 | 70 | article |
| 7 | `amazon_products` | Amazon | `asin + marketplace` | 4 | 98 | product |
| 8 | `amazon_reviews` | Amazon | `review_id + marketplace` | 4 | 49 | review |
| 9 | `amazon_sellers` | Amazon | `seller_id + marketplace` | 4 | 29 | seller |

## Schema Design

Every dataset schema has three common properties:

- **`dedup_key`** (required) — the unique identifier value. Mine uses this directly for dedup checks; no SHA256 hashing is needed.
- **`canonical_url`** (required) — the standardized URL for the record.
- **`url_normalize_regex`** — a regex pattern Mine applies before submission to ensure consistent URL formatting.

## Field Layers

Schema fields fall into three processing layers:

### Layer 1 — Raw Data (crawler output)

Fields directly extracted by the crawler: `title`, `about`, `rating`, `raw_text`, `categories`, `images`, etc. These are available in `records.jsonl` without additional processing.

### Layer 2 — Cleaned / Standardized (rule-based)

Fields produced by deterministic rules: `title_cleaned`, `brand_standardized`, `authors_structured`, `sections_structured`, `categories_cleaned`, etc. No LLM required.

### Layer 3 — AI Analysis (LLM-powered)

Fields requiring LLM inference: `sentiment_aspects`, `career_trajectory_vector`, `qa_pairs_generated`, `novelty_delta_assessment`, `fake_review_risk_score`, etc. These are the primary cost and latency drivers.

## Runtime Behavior

- **First run**: the agent may need to prompt the user to select which datasets to mine if multiple are available.
- **Selected datasets** are persisted in `session.json` and reused on resume.
- **Dataset cooldowns** apply when the platform returns `429`. Only the affected dataset enters cooldown; others continue normally.
- **Occupancy and preflight checks** run before each submission to avoid duplicates and satisfy PoW requirements.
- **Weighted rotation**: when mining multiple datasets, the scheduler prioritizes datasets with the largest remaining gap to their epoch target.

## Processing Strategy

1. Extract required fields first (Layer 1 + Layer 2) to ensure submissions are not rejected.
2. Submit required fields immediately.
3. Optionally enrich with Layer 3 fields to improve quality score.
4. Cache schema per epoch — do not re-fetch within the same epoch.
5. Apply `url_normalize_regex` before submission to ensure dedup accuracy.
