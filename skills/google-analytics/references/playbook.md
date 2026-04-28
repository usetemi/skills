# GA4 Interpretation Playbook

How to read the numbers `ga4` returns without drawing bad conclusions. Benchmarks, attribution nuances, funnel design patterns, and common traps.

This is interpretation guidance, not API reference. For schemas see `data-api.md` and `admin-api.md`.

## Engagement rate — the headline metric

GA4's `engagementRate` replaces UA's `bounceRate` as the primary sticky-vs-bouncing metric. A session is "engaged" if it:

- lasted ≥ 10 seconds, OR
- had ≥ 2 page/screen views, OR
- fired a key event (conversion).

Default thresholds are configurable per property (Admin → Data Streams → the stream → Configure Tag Settings → Define internal traffic).

### Reference benchmarks

General B2C content site (Simo Ahava, *simoahava.com* analyses circa 2023–2025):

| Traffic profile | Typical engagement rate |
|---|---|
| Strong direct / branded | 65-80% |
| Organic search (informational) | 50-65% |
| Organic social (non-product) | 30-45% |
| Paid search (high-intent) | 55-70% |
| Paid social (cold audience) | 20-35% |
| Referral (quality source) | 50-70% |
| Email (existing subscribers) | 60-80% |

These are rough bands — a property with a lot of short-answer content (quick lookups) will read lower on all of these without anything being wrong. Interpret relative to the site's own history, not to a universal benchmark.

Julius Fedorovicius (MeasureSchool) notes that the 10-second default is often too lenient for media sites with long articles — users who genuinely engage take longer to reach the 10s threshold; users who bounce can satisfy it by leaving a tab open. Consider raising the threshold if bounce-like behavior is scoring as "engaged".

## Attribution — GA4 defaults and their cost

GA4's default `reportingAttributionModel` as of 2024+ is **data-driven attribution (DDA)** — a machine-learned model that distributes credit across touchpoints. This differs from UA's default of last-non-direct-click, and it affects how `keyEvents`, `conversions`, `totalRevenue`, and anything Ads-related is split.

| Model | What it does | When it helps | When it misleads |
|---|---|---|---|
| **Data-driven** | ML attributes credit based on path patterns | High volume, stable mix | Low volume (GA4 falls back to last-click under a threshold) |
| **Last-click (cross-channel)** | 100% to the last non-direct channel | Simple to explain | Underweights upper-funnel |
| **First-click (cross-channel)** | 100% to the first touch | Discovery-source analysis | Under-weights closing channels |
| **Linear** | Equal credit across touchpoints | Long consideration cycles | Treats every touch as equal |
| **Position-based** | 40% first, 40% last, 20% middle | Balance discovery + close | Arbitrary weighting |
| **Time-decay** | More credit to recent touches | Short sales cycles | Noisy for long cycles |

Charles Farina (Adswerve) has written extensively on model-shift effects — switching attribution models can move reported conversions ±30% without any real-world change. When comparing numbers to an external source (ad platforms, CRM), **check the attribution model of both sides** first.

Krista Seiden's common advice: pick a model that matches your business decision. For "which channel should I invest more in?" → data-driven or position-based. For "where do users first discover us?" → first-click. For "what closes a sale?" → last-click.

## Sessions — subtle differences from UA

- GA4 sessions time out at 30 minutes of inactivity by default (configurable per stream).
- Unlike UA, crossing day boundaries doesn't end a session.
- Unlike UA, a new campaign source mid-session does NOT start a new session.
- `sessions` vs `engagedSessions` — always prefer the latter for quality analysis; `sessions` includes bounces.

Consequence: GA4 typically reports **lower session counts** than UA on the same traffic. Don't panic when migrating.

## Realtime — what it's actually good for

Realtime shows the **last 30 minutes** (60 for GA360). It's optimized for:

- Verifying instrumentation immediately after deploying a tracking change
- Smoke-testing events during QA
- Debugging ("did my test click actually fire?")

It's **not** useful for:

- Dashboards people watch — 30 minutes is too short a window to show meaningful trends
- Cost/revenue reporting — cost data integrations land on a delay
- Attribution (most attribution fields aren't populated in the realtime report)

If the realtime report looks empty, the traffic is genuinely low; that's not a bug.

## Funnel design patterns

### Good funnel

```
Step 1: view_product       (eventName = view_product)
Step 2: add_to_cart        (eventName = add_to_cart)
Step 3: begin_checkout     (eventName = begin_checkout)
Step 4: purchase           (eventName = purchase)
```

- One event per step
- Sequential (each step deeper than the last)
- Uses standard e-commerce events (GA4 recognizes them for richer reporting)

### Anti-patterns

- **Steps defined by `pagePath` only** — brittle; any URL change breaks the funnel. Prefer event-based steps with pagePath as a *filter* on the event if needed.
- **Overlapping steps** — if step 2's filter includes step 1's filter, you'll get phantom "progression" that's really the same user event counted twice.
- **Funnel type mismatch** — a `CLOSED_FUNNEL` requires users to enter at step 1. If you want "any user who ever reached step 3" regardless of whether they came through step 1, use `OPEN_FUNNEL`.
- **Too many steps** — 4-6 steps is ideal; 10+ steps produce reports that are hard to read and that fragment the population too thin for reliable drop-off rates.

Breakdown dimension: add `funnel_breakdown` to see drop-off split by `deviceCategory`, `sessionSource`, or similar. Keep the breakdown dim cardinality low (< 10 values) or the resulting report is unreadable.

## Audiences — sequence vs condition

GA4 audiences have two predicate types:

- **Condition-based** (`conditionClauses`) — "user has done X AND Y" in any order, within the session/lifetime window
- **Sequence-based** (`sequenceFilter`) — "user did X then Y" in order, with optional time bounds between steps

Common mistake: using a condition audience when you needed a sequence. Example — "users who added to cart and then didn't purchase" requires a sequence with a `notEvent` terminal step, not a condition.

Audience membership evaluates continuously; users can enter and leave. `membership_duration_days` bounds how long a user stays a member after qualifying (default: 30 days; max: 540 days).

## Measurement Protocol naming conventions

- Event names are **snake_case**, max 40 chars. Recommended: lowercase, underscored.
- Reserved events: `ad_impression`, `ad_click`, `ad_reward`, `app_clear_data`, `app_exception`, `app_remove`, `app_store_refund`, `app_store_subscription_cancel`, `app_store_subscription_convert`, `app_store_subscription_renew`, `app_upgrade`, `click`, `error`, `file_download`, `first_open`, `first_visit`, `form_start`, `form_submit`, `in_app_purchase`, `notification_foreground`, `os_update`, `page_view`, `screen_view`, `scroll`, `session_start`, `user_engagement`, `video_complete`, `video_progress`, `video_start`, `view_search_results`. **Don't use these** for your own events — GA4 will silently rewrite them.
- Standard e-commerce events (`view_item`, `add_to_cart`, `begin_checkout`, `add_payment_info`, `add_shipping_info`, `purchase`, `refund`) have reserved parameter names that unlock e-commerce reports. Use them verbatim; the reports depend on exact-match.
- Param names are max 40 chars, values max 100 chars (500 for GA360). User property names max 24 chars.
- For monetary values, always include `currency` alongside `value` (ISO 4217).

Simo Ahava's rule of thumb: if you can't think of an analysis you'd actually run using a new custom event, don't send it. Noise inflates quotas and hides the important events.

## BigQuery for long-term analysis

GA4 retains event-level data for 2–14 months depending on settings. For longer retention, enable a BigQuery link (`ga4 admin links bigquery-create`). Daily + streaming export drops raw events into a BQ dataset. Costs: BQ storage + query fees; no GA-side cost.

When to go to BQ:

- Retention > 14 months
- Cross-property joins
- Joins with other data (CRM, ad platforms, server logs)
- Sampling — BQ gives you unsampled event data; `ga4 data run-report` samples above certain thresholds (especially with complex filters on high-traffic properties)

When to stay in GA:

- Quick lookups, standard reports
- Realtime
- Audience/attribution (BQ has event data but not GA's derived attribution — you'd rebuild it)

## Sampling

GA4 samples report results above a per-query threshold (exact threshold is dynamic, documented as "10M events per query" but effectively much lower for complex filters). Check the response envelope for sampling metadata — `metadata.sampling_metadatas[]` indicates which date ranges were sampled and at what rate.

Mitigate: reduce filter complexity, shorten date range, request fewer dimensions, or go to BQ.

## Data freshness

- **Realtime report**: seconds to minutes
- **Standard reports**: up to 24-48 hours for full data; fresh-ish within ~4 hours for most events
- **Attribution-affected metrics**: longer settling window (up to 48-72 hours for ad-click attribution to stabilize)
- **BigQuery daily export**: next-day
- **BigQuery streaming export**: ~minutes

When someone says "GA doesn't match our CRM today" — first check if the GA side is still settling.

## Comparing properties

When running the same report across multiple properties:

1. **Match time zones** — property time zone affects daily rollups. A 24-hour "day" means different things for properties in different zones.
2. **Match currency** — pass `--currency-code USD` explicitly to normalize revenue.
3. **Match data retention** — a property with 2-month retention will return empty rows for 3-months-ago dates even if other properties have them.
4. **Match attribution model** — if properties have different `reporting_attribution_model`, conversions / revenue will look like they diverge even when actual behavior is identical.

## Cited sources

- Simo Ahava, [simoahava.com](https://www.simoahava.com/) — GA4 instrumentation, engagement rate nuances, MP naming conventions.
- Charles Farina, [charlesfarina.com](https://www.charlesfarina.com/) — attribution model shift effects, sampling.
- Krista Seiden, [kristaseiden.com](https://www.kristaseiden.com/) — attribution model selection, KPI design.
- Julius Fedorovicius, [analyticsmania.com](https://www.analyticsmania.com/) / MeasureSchool — engagement threshold tuning, event design.
- Benjamin Mangold, [lovesdata.com](https://www.lovesdata.com/blog) — GA4 migration patterns, session-level analysis.
- Google's official Data + Admin API reference: developers.google.com/analytics/devguides.

Benchmarks above are ranges, not precise figures. Always compare against the property's own historical baseline before comparing against outside benchmarks.
