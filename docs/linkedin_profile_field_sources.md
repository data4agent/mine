# LinkedIn profile field sources

**Last Updated**: 2026-04-03

## Bug fixes applied

### About section pulling footer content — fixed (2026-04-03)

- **Issue**: The `about` field sometimes captured LinkedIn footer text instead of the bio
- **Cause**: HTML fallback via `_section_text_by_heading` returned footer content
- **Fix**: Added `_is_linkedin_footer_content()` validation
- **File**: `crawler/platforms/linkedin.py`

## 1. Fields available directly from the API (15)

Taken from Voyager API responses:

| Field | API path | Status |
|------|---------|------|
| name | firstName + lastName | OK |
| headline | headline | OK |
| linkedin_num_id | entityUrn | OK |
| public_identifier | publicIdentifier | OK |
| city | geoLocation.geo.defaultLocalizedName | OK |
| country_code | geoLocation.countryISOCode | OK |
| is_premium | premium | OK |
| is_influencer | influencer | OK |
| is_creator | creator | OK |
| content_creator_tier | topVoiceBadge.badgeText | OK |
| profile_url | constructed | OK |
| avatar | profilePicture | OK |
| timestamp | created | OK |
| personal_website | creatorInfo.creatorWebsite | OK |
| featured_content_themes | extracted | OK |

## 2. Fields that require HTML extraction (10)

Not returned by the API; must be parsed from page HTML:

| Field | Page location | Current status | Browser check (2026-04-03) |
|------|----------|----------|------------------------|
| followers | e.g. "40,147,671 followers" / localized | OK | Present |
| about | About section | OK after fix | "Chair of the Gates Foundation..." |
| banner_image | Cover photo URL | OK | Present |
| connections | Connection count (often hidden for celebrities) | Missing on page | Not on Bill Gates profile |
| people_also_viewed | People also viewed carousel | Partial | Present |
| recent_posts | Activity section | Not implemented | Featured posts visible |
| experience | Experience section | Empty | Not on Bill Gates profile |
| education | Education section | Empty | Not on Bill Gates profile |
| skills | Skills section | Empty | Not on Bill Gates profile |
| certifications | Certifications section | Empty | Not on Bill Gates profile |

### Browser check (Bill Gates profile)

**Actual about text**:

> Chair of the Gates Foundation. Founder of Breakthrough Energy. Co-founder of Microsoft. Voracious reader. Avid traveler. Active blogger.

## 3. Fields that need LLM enrichment (59)

Cannot be derived from raw crawl data; produced by AI analysis:

### Identity

- name_gender_inference
- name_ethnicity_estimation
- profile_language_detected

### About

- about_summary
- about_sentiment
- about_topics
- about_readability_score

### Career

- standardized_job_title
- seniority_level
- job_function_category
- current_company (inferred)
- career_trajectory_vector
- career_narrative_type
- career_transition_detected
- job_change_signal_strength
- experience_gap_analysis

### Education

- education_structured
- highest_degree
- education_level

### Influence

- influence_score
- credibility_assessment
- engagement_rate
- content_activity_level

### Recruiting

- open_to_work (may be in API)
- cold_outreach_hooks
- interview_questions_suggested
- culture_fit_indicators

### Completeness

- profile_completeness_score
- internal_consistency_flags

### Advanced

- investor_brief
- full_profile_narrative
- skills_extracted (from about)

## 4. Action plan

### Short term (fix current code)

1. Fix API field mapping in `schema_contract.py`
2. Ensure all fields returned by Voyager are extracted

### Medium term (stronger HTML extraction)

1. Fallback to Playwright/Camoufox when the API fails
2. Add HTML extraction for followers, about, banner_image

### Long term (LLM enrich)

1. Implement enrich pipeline for the 59 analytical fields
2. Process in groups: identity, about_analysis, career_analysis, etc.
