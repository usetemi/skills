# GA4 Data API — Deep Reference

Everything you need to construct valid Data API requests without guessing. This is the "schema cheat sheet" — SKILL.md has the CLI shape, this doc has the wire shape.

## Request body overview

All Data API methods share a similar skeleton:

```json
{
  "property": "properties/123456789",
  "dimensions": [{"name": "country"}, {"name": "deviceCategory"}],
  "metrics": [{"name": "activeUsers"}, {"name": "engagementRate"}],
  "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
  "dimension_filter": {...},
  "metric_filter": {...},
  "order_bys": [{...}],
  "metric_aggregations": ["TOTAL"],
  "limit": 10000,
  "offset": 0,
  "currency_code": "USD",
  "keep_empty_rows": false,
  "return_property_quota": true
}
```

`runPivotReport` adds a `pivots` array. `runRealtimeReport` swaps `date_ranges` for `minute_ranges` and drops `cohort_spec` / `comparisons` / `currency_code`. `batchRunReports` wraps an array of these in `{"requests": [...]}`.

## Dimensions and metrics

A short, high-traffic subset. The full catalog is huge — use `ga4 data get-metadata -p <id>` for the authoritative list.

### Common dimensions

| Name | What it is |
|---|---|
| `date` | `YYYYMMDD` |
| `dateHour` | `YYYYMMDDHH` |
| `country`, `city`, `region` | Geo |
| `deviceCategory` | `mobile` \| `desktop` \| `tablet` |
| `browser`, `operatingSystem` | Client |
| `sessionSource`, `sessionMedium`, `sessionCampaignName` | Acquisition |
| `sessionDefaultChannelGroup` | Channel grouping (Organic Search, Paid Search, etc.) |
| `firstUserSource`, `firstUserMedium`, `firstUserCampaignName` | User acquisition (first touch) |
| `pagePath`, `pageTitle`, `pageLocation`, `pageReferrer` | Page |
| `landingPage` | Session landing page |
| `eventName` | Event name |
| `userAgeBracket`, `userGender` | Demographics (requires Signals) |
| `unifiedScreenName` | For app streams |

### Common metrics

| Name | What it is |
|---|---|
| `totalUsers`, `activeUsers`, `newUsers` | Users |
| `sessions`, `engagedSessions`, `sessionsPerUser` | Sessions |
| `engagementRate`, `userEngagementDuration`, `averageSessionDuration` | Engagement |
| `bounceRate` | 1 − engagementRate. Still returned but engagementRate is the modern metric. |
| `screenPageViews`, `screenPageViewsPerSession` | Page views |
| `eventCount`, `eventCountPerUser`, `eventsPerSession` | Events |
| `conversions` | Legacy name (maps to key events). |
| `keyEvents`, `keyEventRate`, `sessionKeyEventRate` | Key events (GA4 name for conversions). |
| `totalRevenue`, `purchaseRevenue` | Revenue |
| `adImpressions`, `adClicks`, `adCost` | Ads (with Google Ads link) |

### Custom dimensions / metrics

Once created via `ga4 admin custom-dimensions create` / `custom-metrics create`, they're referenced by `customEvent:<parameter_name>`, `customUser:<parameter_name>`, or `customItem:<parameter_name>` in reports.

### Compatibility

Not every dim+metric combo is queryable together. Validate before running:

```bash
ga4 data check-compatibility -p <id> -d country -d pagePath -m totalRevenue
```

Returns `{"dimension_compatibilities": [...], "metric_compatibilities": [...]}` with `COMPATIBLE` / `INCOMPATIBLE` per field.

## Filters (`FilterExpression`)

The filter AST is recursive. Four node types:

### 1. `filter` — leaf

```json
{"filter": {"fieldName": "deviceCategory", "stringFilter": {"value": "mobile", "matchType": "EXACT"}}}
```

Filter subtypes:
- `stringFilter`: `{value, matchType, caseSensitive?}`. matchType: `EXACT` (default) \| `BEGINS_WITH` \| `ENDS_WITH` \| `CONTAINS` \| `FULL_REGEXP` \| `PARTIAL_REGEXP`
- `inListFilter`: `{values: [...], caseSensitive?}`
- `numericFilter`: `{operation, value: {int64Value|doubleValue}}`. operation: `EQUAL` \| `LESS_THAN` \| `LESS_THAN_OR_EQUAL` \| `GREATER_THAN` \| `GREATER_THAN_OR_EQUAL`
- `betweenFilter`: `{fromValue, toValue}` each `{int64Value|doubleValue}`

### 2. `andGroup` / `orGroup` — combine

```json
{"andGroup": {"expressions": [
  {"filter": {...}},
  {"orGroup": {"expressions": [{"filter": {...}}, {"filter": {...}}]}}
]}}
```

### 3. `notExpression` — negate

```json
{"notExpression": {"filter": {"fieldName": "country", "stringFilter": {"value": "United States"}}}}
```

### Real examples

Mobile users from the US:

```json
{"andGroup": {"expressions": [
  {"filter": {"fieldName": "deviceCategory", "stringFilter": {"value": "mobile"}}},
  {"filter": {"fieldName": "country",        "stringFilter": {"value": "United States"}}}
]}}
```

Pages under `/blog/` OR `/guides/`, excluding `/blog/legacy/*`:

```json
{"andGroup": {"expressions": [
  {"orGroup": {"expressions": [
    {"filter": {"fieldName": "pagePath", "stringFilter": {"matchType": "BEGINS_WITH", "value": "/blog/"}}},
    {"filter": {"fieldName": "pagePath", "stringFilter": {"matchType": "BEGINS_WITH", "value": "/guides/"}}}
  ]}},
  {"notExpression": {"filter": {"fieldName": "pagePath", "stringFilter": {"matchType": "BEGINS_WITH", "value": "/blog/legacy/"}}}}
]}}
```

Revenue ≥ $100:

```json
{"filter": {"fieldName": "totalRevenue", "numericFilter": {
  "operation": "GREATER_THAN_OR_EQUAL", "value": {"doubleValue": 100}
}}}
```

## Date ranges

- `YYYY-MM-DD` (ISO) — e.g., `"2026-04-01"`
- Relative: `"NdaysAgo"` (e.g., `"7daysAgo"`, `"30daysAgo"`), `"today"`, `"yesterday"`
- Up to 4 date ranges per request (each with optional `name` for labeling in the response)
- Comparisons (`comparisons` array) are separate from `date_ranges` — used for base-vs-variant splits within a single date range

## `order_bys`

```json
[
  {"metric": {"metricName": "sessions"}, "desc": true},
  {"dimension": {"dimensionName": "date", "orderType": "ALPHANUMERIC"}}
]
```

`dimension.orderType`: `ALPHANUMERIC` (default) \| `CASE_INSENSITIVE_ALPHANUMERIC` \| `NUMERIC`. Use `NUMERIC` when sorting on a string-typed dimension that holds numeric values (e.g., a custom dim).

## Pagination

Data API is explicit pagination:
- `limit` — default 10,000, max 250,000
- `offset` — default 0

For result sets > 250k, issue multiple requests with incrementing `offset`.

`row_count` in the response tells you the total — compare against `offset + len(rows)` to know if you're done.

## Quota

Pass `"return_property_quota": true` to get live quota state in every response:

```json
{
  "property_quota": {
    "tokens_per_day":      {"consumed": 127,  "remaining": 199873},
    "tokens_per_hour":     {"consumed": 42,   "remaining": 39958},
    "concurrent_requests": {"consumed": 1,    "remaining": 9},
    "server_errors_per_project_per_hour": {"consumed": 0, "remaining": 10},
    "potentially_thresholded_requests_per_hour": {"consumed": 0, "remaining": 120}
  }
}
```

Standard property limits (GA360 gets 10x):

| Quota | Daily | Hourly | Concurrent |
|---|---|---|---|
| Core (runReport, batch, compatibility, metadata, audience exports) | 200,000 | 40,000 | 10 |
| Realtime | 200,000 | 40,000 | 10 |
| Funnel | 200,000 | 40,000 | 10 |

Token cost scales with row count, dimension/metric count, filter complexity, date range length. Complex multi-date + filter + many-dim queries can cost hundreds of tokens per call.

## Pivot reports

Up to 4 pivots per request. Each pivot has its own `fieldNames`, `orderBys`, `offset`, `limit`. Responses are harder to parse than flat reports — each row is tagged with which pivot it belongs to. Use for cross-tabulated views (e.g., rows = country, columns = deviceCategory).

Pivot JSON skeleton:

```json
{
  "pivots": [
    {"fieldNames": ["country"], "limit": 10, "orderBys": [{"metric": {"metricName": "sessions"}, "desc": true}]},
    {"fieldNames": ["deviceCategory"], "limit": 3}
  ]
}
```

## Batch

`batchRunReports` and `batchRunPivotReports` each accept up to 5 requests. Every sub-request is billed independently for quota. Use batch when you need strict parallelism (single round-trip) or when multiple reports share the same property + scopes.

## Realtime

- Window: last 30 minutes (60 for GA360)
- `minute_ranges`: up to 2 per request. Each: `{start_minutes_ago, end_minutes_ago}` — values 0-30 (0-60 GA360). `end=0` means "now".
- No `date_ranges`, no `cohort_spec`, no `comparisons`, no `currency_code`
- Dimensions and metrics are a smaller subset than standard reporting — many aren't available. `unifiedScreenName`, `country`, `deviceCategory`, `eventName`, `activeUsers`, `screenPageViews`, `keyEvents`, `eventCount` all work.

## Funnel reports (alpha)

`runFunnelReport` (v1alpha) is **unstable** — breaking changes possible. Request shape:

```json
{
  "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
  "funnel": {
    "steps": [
      {"name": "view_product",  "filter_expression": {...}},
      {"name": "add_to_cart",   "filter_expression": {...}},
      {"name": "purchase",      "filter_expression": {...}}
    ]
  },
  "funnel_breakdown": {"breakdown_dimension": {"name": "deviceCategory"}},
  "funnel_visualization_type": "STANDARD_FUNNEL"
}
```

Response is a pair of sub-reports: `funnel_table` (row per step with counts) and `funnel_visualization` (optimized for plotting).

`steps[].filter_expression` uses the same FilterExpression schema as `dimension_filter`. Event-path funnels typically filter on `eventName`: `{"filter": {"fieldName": "eventName", "stringFilter": {"value": "add_to_cart"}}}`.

Funnels can be "closed" (`"funnel_type": "CLOSED_FUNNEL"`, default) — users must enter at step 1 — or "open" — users enter at any step. For "any of these steps" vs "strict order", use `"funnel_type"` and per-step `"is_directly_followed_by"` / `"within_duration_from_prior_step"` controls.

## Audience exports

Lifecycle:

1. `ga4 data audience-exports create --audience properties/X/audiences/Y -d <dims>` → returns an operation name, state `CREATING`.
2. `ga4 data audience-exports get <name>` — poll until `state: ACTIVE` (or `FAILED`).
3. `ga4 data audience-exports query <name> -l 10000 -o 0` — fetch rows.

Exports are async because audience membership evaluation is expensive. `CREATING` → `ACTIVE` typically takes under a minute for small audiences but can be 10+ minutes for large ones.

Dimensions in the export are limited to a subset (mostly identity + first-touch acquisition dims). Check `get_metadata` for which dims are `usage: audience_export` capable.
