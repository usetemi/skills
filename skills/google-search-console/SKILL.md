---
name: google-search-console
description: Query Google Search Console analytics, inspect URL indexing status, manage sitemaps, and run PageSpeed Insights audits. Use when the user needs SEO data, search performance reports, indexing diagnostics, or Core Web Vitals analysis.
---

# Google Search Console

## Architecture

`gsc` is a Python CLI wrapping two Google APIs:
- **Search Console API** (webmasters v3 + searchconsole v1) -- search analytics, site management, sitemaps, URL inspection
- **PageSpeed Insights API** (v5) -- Lighthouse lab tests for performance, accessibility, SEO, best practices

All commands output JSON to stdout. Errors go to stderr. Designed for Claude to invoke and parse programmatically.

## Before First Use

1. **uv**: Run `which uv`. If missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Project sync**: `uv sync --project <skill-dir>`
3. **Auth**: See below.
4. **PageSpeed API key**: See below.

### Search Console Auth (OAuth)

Save your OAuth client_secret.json (downloaded from GCP) to a known path, then authenticate:

```bash
gsc auth login --client-secret /path/to/client_secret.json
```

A browser opens for OAuth consent. On a headless machine, open an SSH tunnel first: `ssh -L 8085:localhost:8085 <this-host>`, then open the printed URL on a machine with a browser. Credentials are stored at `~/.config/gsc/credentials.json` and auto-refresh.

If you need to create a new OAuth client, see `references/setup.md` for the full GCP click-path.

### PageSpeed Insights API Key

Set the key once and gsc remembers it:

```bash
gsc config set pagespeed-api-key <your-key>
```

If you don't have a key, create one in your GCP project's Credentials page, restrict it to the "PageSpeed Insights API", and pass it to `gsc config set` above.

## Invocation

```bash
uv run --project /path/to/skills/google-search-console gsc <command> [args]
```

For brevity, examples below use `gsc` directly.

## Commands

### auth -- Manage authentication

```bash
# Authenticate with OAuth
gsc auth login --client-secret ./client_secret.json --port 8085

# Check auth status
gsc auth status

# Remove stored credentials
gsc auth logout
```

### config -- Manage settings

```bash
# Set PageSpeed API key
gsc config set pagespeed-api-key AIza...

# Get a config value
gsc config get pagespeed-api-key

# Show all config (secrets masked)
gsc config show
```

### query -- Search Analytics

```bash
# Basic query: clicks, impressions, CTR, position for last 7 days
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07

# Group by query keyword
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d query

# Group by page and query
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d page -d query

# Daily breakdown
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d date

# Filter by query containing "pricing"
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d query --query-filter pricing

# Exact match filter
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 --query-filter "=best coffee shop"

# Mobile only
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 --device-filter "=MOBILE"

# Image search
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 --search-type image

# Paginate results
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 --row-limit 5000 --start-row 0
```

Filter prefix operators: `=` exact match, `!` not-contains, no prefix or `~` for contains.

### inspect -- URL Inspection

```bash
gsc inspect sc-domain:example.com https://example.com/page
gsc inspect https://example.com/ https://example.com/page --language en-US
```

Returns: indexing verdict, crawl info, canonical URL, mobile usability, rich results status.

### sites -- Manage properties

```bash
gsc sites list
gsc sites get sc-domain:example.com
gsc sites add https://example.com/
```

### sitemaps -- Manage sitemaps

```bash
gsc sitemaps list sc-domain:example.com
gsc sitemaps get sc-domain:example.com https://example.com/sitemap.xml
gsc sitemaps submit sc-domain:example.com https://example.com/sitemap.xml
gsc sitemaps delete sc-domain:example.com https://example.com/sitemap.xml
```

### pagespeed -- PageSpeed Insights

```bash
# Mobile performance (default)
gsc pagespeed https://example.com

# Desktop, all categories
gsc pagespeed https://example.com --strategy desktop \
  --category performance --category accessibility --category seo --category best-practices

# Specific locale
gsc pagespeed https://example.com --locale fr
```

Requires API key: `gsc config set pagespeed-api-key <key>`. Lab tests take 30-60s.

## Site URL Formats

Google Search Console supports two property types:

| Type | Format | Example | Scope |
|------|--------|---------|-------|
| Domain property | `sc-domain:example.com` | `sc-domain:example.com` | All subdomains, protocols, paths |
| URL-prefix property | `https://example.com/` | `https://example.com/` | Exact prefix match only |

Use domain properties when possible -- they cover all variations.

## Common Workflows

### Weekly Performance Check

```bash
# This week vs last week, grouped by date
gsc query sc-domain:example.com -s 2026-03-05 -e 2026-03-11 -d date
gsc query sc-domain:example.com -s 2026-02-26 -e 2026-03-04 -d date

# Top queries by clicks
gsc query sc-domain:example.com -s 2026-03-05 -e 2026-03-11 -d query --row-limit 25
```

### Indexing Health Check

```bash
# Check if key pages are indexed
gsc inspect sc-domain:example.com https://example.com/important-page
gsc inspect sc-domain:example.com https://example.com/new-blog-post

# Verify sitemap coverage
gsc sitemaps list sc-domain:example.com
gsc sitemaps get sc-domain:example.com https://example.com/sitemap.xml
```

### CTR Optimization

```bash
# Find high-impression, low-CTR queries (position 3-10)
gsc query sc-domain:example.com -s 2026-02-10 -e 2026-03-11 -d query -d page --row-limit 5000

# Filter results to find optimization opportunities:
# Look for rows where impressions > 100 and position between 3-10 but CTR < 3%
```

### Device Comparison

```bash
gsc query sc-domain:example.com -s 2026-03-01 -e 2026-03-07 -d device
```

### Core Web Vitals Check

```bash
gsc pagespeed https://example.com --strategy mobile
gsc pagespeed https://example.com --strategy desktop
```

## Interpreting Output

See `references/seo-playbook.md` for detailed interpretation guides including:
- CTR benchmarks by SERP position
- Core Web Vitals thresholds
- URL inspection verdicts
- Title/description optimization
- Monthly monitoring methodology

## Configuration Files

- **OAuth credentials**: `~/.config/gsc/credentials.json`
- **Config (API keys)**: `~/.config/gsc/config.json`

## Troubleshooting

**"Not authenticated"** -- Run `gsc auth login --client-secret /path/to/client_secret.json`. Credentials may have expired or be missing on a new machine.

**"Permission denied"** -- The authenticated account must be a verified owner or user of the Search Console property. Check property access at https://search.google.com/search-console.

**"Rate limit exceeded"** -- Search Console API has per-minute and per-day quotas. Wait 60 seconds and retry. See `references/setup.md` for quota details.

**URL Inspection returns no data** -- The URL may not be in Google's index. Check the `verdict` field. Only URLs within verified properties can be inspected.

**PageSpeed timeout** -- Lighthouse lab tests can take 30-60 seconds. The command uses a 120-second timeout. Retry if it fails.

**"Unknown key" on config set** -- Only `pagespeed-api-key` is a valid config key.
