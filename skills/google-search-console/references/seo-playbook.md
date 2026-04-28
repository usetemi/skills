# SEO Playbook

Reference guide for interpreting Google Search Console and PageSpeed Insights data.

## CTR Benchmarks by SERP Position

Source: First Page Sage 2025 meta-analysis. These apply to standard SERPs without additional features.

| Position | CTR |
|----------|------|
| 1 | 39.8% |
| 2 | 18.7% |
| 3 | 10.2% |
| 4 | 7.2% |
| 5 | 5.1% |
| 6 | 4.4% |
| 7 | 3.0% |
| 8 | 2.1% |
| 9 | 1.9% |
| 10 | 1.6% |

The top 3 results receive ~69% of all clicks. Position 1 alone receives more clicks than positions 3-10 combined.

### SERP Feature CTRs

| Feature | CTR |
|---------|------|
| Featured Snippet (pos 1) | 42.9% |
| AI Overview (pos 1) | 38.9% |
| AI Overview (pos 2) | 29.5% |
| People Also Ask box | 3.0% |
| Knowledge Panel | 1.4% |

### Impact of AI Overviews on CTR

AI Overviews appear on ~31% of search results, 99.9% of informational queries, and 46% are long-tail (7+ words).

- **Organic CTR drop**: ~61% decline (from 1.76% to 0.61%) for queries where AI Overviews appear
- **Position 1 decline**: ~32% year-over-year (from 28% to 19% with AI Overviews present)
- **Average top-5 decline**: ~18% average CTR drop across positions 1-5
- **Citation advantage**: Brands cited within AI Overviews earn 35% more organic clicks
- Informational queries see the largest impact; commercial/transactional queries are less affected
- Brand queries remain largely unaffected

### When CTR is "Low"

CTR below the benchmark for a given position indicates an optimization opportunity. Common causes:
- Weak title tag (not compelling, too generic, truncated)
- Missing or poor meta description (Google generates one, often suboptimal)
- Rich results appearing above (featured snippets, PAA, knowledge panels)
- SERP features pushing organic results below the fold
- Query-title mismatch (ranking for tangential terms)

## Low-CTR High-Impression Optimization

This is the highest-ROI SEO activity: pages already ranking but underperforming on clicks.

### Identification Query

```bash
gsc query sc-domain:example.com -s <30-days-ago> -e <today> -d query -d page --row-limit 5000
```

Filter the results for:
- Impressions > 100 (statistically significant)
- Position between 3-15 (realistic improvement range)
- CTR below benchmark for that position

### Optimization Steps

1. **Audit the title tag**: Should be 50-60 characters, include the target keyword near the front, and have a compelling hook
2. **Audit the meta description**: 120-155 characters, include the keyword, add a call to action
3. **Check for SERP features**: Search the query manually to see what's appearing above your result
4. **Review structured data**: Rich snippets (star ratings, FAQ, how-to) increase CTR significantly
5. **Consider the search intent**: If the page doesn't match what users expect, CTR will be low regardless of title

## Title Tag Best Practices

- **Length**: 50-60 characters (Google truncates around 580-600px width)
- **Keyword placement**: Target keyword near the beginning
- **Format**: `Primary Keyword - Secondary Keyword | Brand` or `Primary Keyword: Descriptive Subtitle`
- **Avoid**: ALL CAPS, keyword stuffing, duplicate titles across pages, clickbait that doesn't match content
- **Unique per page**: Every indexable page should have a unique title

## Meta Description Guidelines

- **Length**: 120-158 characters (desktop ~920px / ~158 chars, mobile ~680px / ~120 chars)
- **Include**: Target keyword (bolded in SERPs), clear value proposition, call to action
- **Avoid**: Duplicate descriptions, quotes (can truncate the snippet), no description at all
- Google rewrites meta descriptions ~60-70% of the time when they don't match search intent

## URL Inspection Verdicts

The `inspectionResult.indexStatusResult.verdict` field:

| Verdict | Meaning | Action |
|---------|---------|--------|
| `PASS` | URL is indexed and can appear in search results | None needed |
| `PARTIAL` | Indexed but has issues (e.g., blocked resources) | Check `pageFetchState` and resource errors |
| `FAIL` | Not indexed | Check `coverageState` for the specific reason |
| `NEUTRAL` | Not yet inspected | Submit for inspection or wait for crawl |

### Page Indexing Statuses

**Not indexed -- typically expected:**

| Status | Meaning | Action |
|--------|---------|--------|
| `Discovered - currently not indexed` | Google knows the URL but hasn't crawled it | Wait; request indexing if urgent |
| `Crawled - currently not indexed` | Crawled but Google chose not to index | Improve content quality, add internal links |
| `Alternate page with proper canonical tag` | Recognized alternate of an indexed canonical | None needed |
| `Duplicate without user-selected canonical` | Google chose the canonical itself | Set canonical tag or differentiate content |
| `Duplicate, Google chose different canonical than user` | Your canonical tag is ignored | Review content similarity |
| `Page with redirect` | Redirects to another page | None unless unintentional |
| `URL marked 'noindex'` | noindex directive prevents indexing | Remove noindex if page should be indexed |
| `Blocked by robots.txt` | robots.txt prevents crawling | Use noindex instead if preventing indexing |
| `Not found (404)` | 404 error | Redirect if a relevant page exists |

**Not indexed -- errors (need fixing):**

| Status | Meaning | Action |
|--------|---------|--------|
| `Server error (5xx)` | 500-level error during crawl | Fix server-side issues |
| `Redirect error` | Redirect loop or chain too long | Fix the redirect chain |
| `Soft 404` | Returns 200 but looks like a "not found" page | Return proper 404 or add real content |
| `Blocked due to unauthorized request (401)` | Requires authentication | Remove auth if page should be public |
| `Blocked due to access forbidden (403)` | 403 Forbidden | Whitelist Googlebot |
| `Indexed, though blocked by robots.txt` | Indexed despite robots.txt (from inbound links) | Remove robots.txt block or add noindex (not both) |

### Page Fetch State

| State | Meaning |
|-------|---------|
| `SUCCESSFUL` | Googlebot fetched the page successfully |
| `SOFT_404` | Page appeared to be a soft 404 |
| `BLOCKED_ROBOTS_TXT` | Blocked by robots.txt |
| `NOT_FOUND` | 404 error |
| `ACCESS_DENIED` | 401/403 error |
| `SERVER_ERROR` | 5xx error |
| `REDIRECT_ERROR` | Too many redirects or redirect loop |
| `ACCESS_FORBIDDEN` | Access forbidden |
| `BLOCKED_4XX` | Other 4xx error |

## Core Web Vitals Thresholds

These are the metrics Google uses for page experience ranking signals.

### Largest Contentful Paint (LCP)

Measures loading performance -- when the largest content element becomes visible.

| Rating | Threshold |
|--------|----------|
| Good | <= 2.5s |
| Needs Improvement | 2.5s - 4.0s |
| Poor | > 4.0s |

Common fixes: optimize images (WebP/AVIF, lazy loading), reduce server response time, remove render-blocking resources, preload critical assets.

### Interaction to Next Paint (INP)

Measures responsiveness -- the latency of all user interactions throughout the page lifecycle.

| Rating | Threshold |
|--------|----------|
| Good | <= 200ms |
| Needs Improvement | 200ms - 500ms |
| Poor | > 500ms |

Common fixes: break up long tasks, reduce JavaScript execution time, use `requestIdleCallback`, optimize event handlers.

### Cumulative Layout Shift (CLS)

Measures visual stability -- how much the page layout shifts unexpectedly.

| Rating | Threshold |
|--------|----------|
| Good | <= 0.1 |
| Needs Improvement | 0.1 - 0.25 |
| Poor | > 0.25 |

Common fixes: set explicit dimensions on images/videos/embeds, avoid inserting content above existing content, use CSS `contain` property.

### First Contentful Paint (FCP)

Measures when the first piece of content is rendered.

| Rating | Threshold |
|--------|----------|
| Good | <= 1.8s |
| Needs Improvement | 1.8s - 3.0s |
| Poor | > 3.0s |

### Time to First Byte (TTFB)

Measures server responsiveness.

| Rating | Threshold |
|--------|----------|
| Good | <= 800ms |
| Needs Improvement | 800ms - 1800ms |
| Poor | > 1800ms |

### Passing Criteria

A page passes Core Web Vitals when at least 75% of page visits meet the "Good" threshold for all three core metrics (LCP, INP, CLS). Google evaluates the 75th percentile, not the average.

### Field Data vs Lab Data

PageSpeed Insights returns both:

- **Field data** (Chrome User Experience Report): Real user measurements over 28 days. This is what Google uses for ranking. Found in `loadingExperience` and `originLoadingExperience`.
- **Lab data** (Lighthouse): Simulated test from a single run. Useful for debugging but does not directly affect rankings. Found in `lighthouseResult`.

Always prioritize field data for ranking assessments. Use lab data for diagnosing specific performance issues.

## Rich Results and Structured Data

URL Inspection's `richResultsResult` shows which structured data types Google detected and whether they're valid.

Common structured data types to monitor:
- **Article**: Blog posts, news articles
- **Product**: E-commerce product pages (price, availability, reviews)
- **FAQ**: Frequently asked questions (expandable in SERPs)
- **HowTo**: Step-by-step instructions
- **BreadcrumbList**: Navigation breadcrumbs
- **Organization**: Company information
- **LocalBusiness**: Physical business locations
- **Review/AggregateRating**: Star ratings in SERPs

Issues are categorized as:
- **Error**: Prevents rich result from appearing -- must fix
- **Warning**: Rich result may still appear but could be improved

## Monthly Monitoring Methodology

### Week 1: Performance Review

```bash
# Compare this month to last month
gsc query sc-domain:example.com -s <month-start> -e <month-end> -d date
gsc query sc-domain:example.com -s <prev-month-start> -e <prev-month-end> -d date

# Top pages by clicks
gsc query sc-domain:example.com -s <month-start> -e <month-end> -d page --row-limit 50

# Device breakdown
gsc query sc-domain:example.com -s <month-start> -e <month-end> -d device
```

### Week 2: Indexing Health

```bash
# Check sitemap status
gsc sitemaps list sc-domain:example.com

# Inspect key landing pages
gsc inspect sc-domain:example.com https://example.com/
gsc inspect sc-domain:example.com https://example.com/pricing
gsc inspect sc-domain:example.com https://example.com/blog
```

### Week 3: CTR Optimization

```bash
# Find low-CTR high-impression opportunities
gsc query sc-domain:example.com -s <30-days-ago> -e <today> -d query -d page --row-limit 5000
```

Filter and prioritize pages where CTR is below benchmark for the ranking position.

### Week 4: Core Web Vitals

```bash
# Test key pages
gsc pagespeed https://example.com --strategy mobile
gsc pagespeed https://example.com/pricing --strategy mobile
gsc pagespeed https://example.com --strategy desktop
```

Focus on pages with "Needs Improvement" or "Poor" scores in field data.

## Useful Query Patterns

### Date Comparison (Week over Week)

```bash
gsc query sc-domain:example.com -s 2026-03-05 -e 2026-03-11 -d date
gsc query sc-domain:example.com -s 2026-02-26 -e 2026-03-04 -d date
```

### Country Analysis

```bash
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d country --row-limit 50
```

### Device Breakdown for Specific Page

```bash
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d device --page-filter "=https://example.com/pricing"
```

### Brand vs Non-Brand Queries

```bash
# Brand queries
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d query --query-filter "example"

# Non-brand queries
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d query --query-filter "!example"
```

### New Content Performance

```bash
# Check recently published pages
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d page --page-filter "/blog/2026/"
```
