---
name: google-analytics
description: Query GA4 reports (users, sessions, conversions, funnels, realtime), manage properties / data streams / key events / custom dimensions / audiences / access bindings, and send Measurement Protocol events via the `ga4` CLI. Use this skill whenever the user mentions GA4, Google Analytics, property IDs starting with `properties/`, tracking events, engagement or traffic metrics, attribution, conversions, key events, audiences, BigQuery links, access roles, or realtime users — even if they don't explicitly say "GA4". Do not use for Google Search Console (see google-search-console skill) or generic web analytics where the source isn't GA4 (ask first).
---

# Google Analytics

## Architecture

`ga4` is a standalone Python CLI that wraps three GA4 APIs:

- **Data API** (v1beta + v1alpha) — `ga4 data …` — reporting, realtime, metadata, funnels, audience exports
- **Admin API** (v1beta + v1alpha) — `ga4 admin …` — accounts, properties, streams, key events, custom dims/metrics, measurement secrets, links, audiences, access bindings, annotations
- **Measurement Protocol** — `ga4 mp …` — event ingestion (send + validate against debug endpoint)

All commands emit JSON to stdout with `indent=2`. Errors go to stderr as plain text with exit 1. Destructive operations require `--yes/-y` on the CLI; the skill adds an additional user-confirmation layer (see **Destructive operations** below).

Auth is OAuth-user-only via `ga4 auth login --client-secret <Desktop-OAuth-client.json>`. The CLI owns its own state at `~/.config/skills/ga4/` (not under the skill's path — `ga4` is usable outside this skill).

## Before First Use

1. **Install** — `uv sync --project /abs/path/to/skills/google-analytics`
2. **Create an OAuth Desktop client in GCP** — https://console.cloud.google.com/apis/credentials → Create Credentials → OAuth client ID → Desktop app → download the JSON. ADC (`gcloud auth application-default login`) is deliberately not supported — Google is phasing out analytics scopes on the default gcloud client ID.
3. **Auth** — `ga4 auth login --client-secret /path/to/downloaded.json`. A browser opens for consent. On a headless machine, open an SSH tunnel first: `ssh -L 8086:localhost:8086 <this-host>` and open the printed URL on a machine with a browser. Scopes default to readonly + edit + manage-users; override with `--scope` (repeatable) for provision / user-deletion.
4. **Grant GA access** — in GA Admin → Access Management, add the Google account you just authed with as Viewer (reads) or Editor/Administrator (writes, user management). See `references/setup.md` for click-path.
5. **Default property** (optional, recommended) — `ga4 config set-property 123456789`.
6. **Verify** — `ga4 doctor` should be all-green.

## Canonical invocation

```bash
uv run --project /path/to/skills/google-analytics ga4 <command> [args]
```

For brevity, examples below use `ga4` directly. When running from outside the skill directory, always use the full `uv run --project <abs-path>` form.

## Destructive operations

**Before running any `delete` or `archive` subcommand, show the user the exact command (including target resource name) and ask for confirmation in conversation. Only pass `--yes/-y` after an affirmative answer in the current turn. Never chain multiple destructive ops without re-confirming each one.**

The CLI's `--yes` flag is a non-interactive guardrail. The skill's job is to make sure a human explicitly agrees before a `properties delete`, `key-events delete`, `custom-dimensions archive`, `custom-metrics archive`, `audiences archive`, `access-bindings delete`, `access-bindings batch-delete`, `annotations delete`, `data-streams delete`, `measurement-secrets delete`, `links firebase-delete`, `links ads-delete`, `links bigquery-delete`, `properties submit-user-deletion`, or `accounts delete` is executed. If the user is in a hurry, still ask — a single clear confirmation is cheap compared to clobbering a production property.

## Command index

### `ga4 auth`, `ga4 config`, `ga4 doctor`

| Command | Purpose | Min scope |
|---|---|---|
| `ga4 auth login --client-secret <path>` | OAuth Desktop flow | n/a |
| `ga4 auth status` | Report OAuth credential status | n/a |
| `ga4 auth whoami` | Scopes and expiry on the current token | readonly |
| `ga4 auth logout` | Remove OAuth credentials | n/a |
| `ga4 config set-property <id>` | Persist default property (stored as `properties/<id>`) | n/a |
| `ga4 config get default-property` | Read default | n/a |
| `ga4 config show` | Dump all config | n/a |
| `ga4 doctor` | Health check (config, OAuth credentials, scopes, Admin API ping) | readonly |

Property ids accept either `123456789` or `properties/123456789`.

### `ga4 data` — Data API

| Command | Purpose | Min scope |
|---|---|---|
| `ga4 data run-report -p <id> -d <dims> -m <metrics> -s <start> -e <end>` | Standard report | readonly |
| `ga4 data run-pivot-report -p <id> --request-json @body.json` | Pivot report | readonly |
| `ga4 data batch-run-reports -p <id> --requests-json @bodies.json` | Up to 5 reports in one call | readonly |
| `ga4 data batch-run-pivot-reports -p <id> --requests-json @bodies.json` | Up to 5 pivot reports | readonly |
| `ga4 data run-realtime-report -p <id> -d <dims> -m <metrics>` | Last 30 (or 60 for GA360) minutes | readonly |
| `ga4 data run-funnel-report -p <id> --request-json @funnel.json` | Funnel analysis. **Alpha**. | readonly |
| `ga4 data check-compatibility -p <id> -d <dims> -m <metrics>` | Validate dim+metric combo | readonly |
| `ga4 data get-metadata -p <id>` | Dimensions + metrics catalog for the property (pass `properties/0` for universal) | readonly |
| `ga4 data audience-exports create --audience <name> -d <dims>` | Create audience export | readonly |
| `ga4 data audience-exports get <name>` / `list` / `query <name>` | Audience export lifecycle | readonly |

Common `run-report` flags: `--dimension-filter-json`, `--metric-filter-json`, `--order-by-json`, `--metric-aggregation`, `--cohort-spec-json`, `--comparisons-json`, `--limit`, `--offset`, `--currency-code`, `--keep-empty-rows`, `--return-property-quota`, `--request-json` (full body override).

Filter/order/cohort JSON can be inline (`--dimension-filter-json '{"filter":...}'`) or a file (`--dimension-filter-json @/tmp/f.json`). See `references/data-api.md` for the filter grammar.

### `ga4 admin accounts` — Accounts

| Command | Purpose | Min scope |
|---|---|---|
| `accounts list` / `get <id>` / `summaries-list` | Read accounts | readonly |
| `accounts update <id> --display-name …` | Rename | edit |
| `accounts delete <id> --yes` | Soft-delete | edit |
| `accounts search-change-history <id>` | Audit trail | readonly |
| `accounts run-access-report <id> -d <dims> -m <metrics>` | Who-accessed-what audit | readonly |
| `accounts get-data-sharing-settings <id>` | Read sharing settings | readonly |
| `accounts provision-ticket --display-name … --redirect-uri …` | New-account provisioning ticket | edit |

### `ga4 admin properties` — Properties

| Command | Purpose | Min scope |
|---|---|---|
| `properties list --account <id>` / `get -p <id>` | Read properties | readonly |
| `properties create --parent <account> --display-name … --time-zone …` | Create | edit |
| `properties update -p <id> --display-name …` | Update (or `--body-json` + `--update-mask`) | edit |
| `properties delete -p <id> --yes` | Soft-delete | edit |
| `properties get-data-retention -p <id>` / `update-data-retention …` | Retention settings | edit |
| `properties get-attribution-settings -p <id>` / `update…` | Attribution model. **Alpha**. | edit |
| `properties get-signals-settings -p <id>` / `update…` | Google Signals. **Alpha**. | edit |
| `properties run-access-report -p <id> …` | Access audit at property scope | readonly |
| `properties search-change-history -p <id>` | Change history | readonly |
| `properties acknowledge-user-data -p <id> --acknowledgement …` | Prereq for Measurement Protocol secrets | edit |
| `properties submit-user-deletion -p <id> --user-id …` | GDPR deletion. **Alpha**. Irreversible. | user.deletion |

### `ga4 admin data-streams`, `measurement-secrets`

| Command | Purpose | Min scope |
|---|---|---|
| `data-streams list -p <id>` / `get -p <id> <stream>` | Read streams | readonly |
| `data-streams create -p <id> --type WEB_DATA_STREAM --display-name … --uri …` | Create web stream | edit |
| `data-streams create --type ANDROID_APP_DATA_STREAM --package-name …` | Android | edit |
| `data-streams create --type IOS_APP_DATA_STREAM --bundle-id …` | iOS | edit |
| `data-streams update -p <id> <stream> --display-name …` | Rename | edit |
| `data-streams delete -p <id> <stream> --yes` | Delete | edit |
| `data-streams get-global-site-tag -p <id> <stream>` | gtag snippet. **Alpha**. | readonly |
| `data-streams get-enhanced-measurement -p <id> <stream>` / `update…` | EM settings. **Alpha**. | edit |
| `data-streams get-data-redaction -p <id> <stream>` / `update…` | PII redaction. **Alpha**. | edit |
| `measurement-secrets list -p <id> <stream>` / `get`, `create --display-name …`, `update`, `delete` | MP secrets CRUD (requires `acknowledge-user-data` first) | edit |

### `ga4 admin key-events`, `custom-dimensions`, `custom-metrics`

| Command | Purpose | Min scope |
|---|---|---|
| `key-events list -p <id>` / `get` / `create --event-name … --counting-method …` / `update` / `delete --yes` | Conversion events (replaces `conversionEvents`) | edit |
| `custom-dimensions list -p <id>` / `get` / `create --parameter-name … --display-name … --scope EVENT` / `update` / `archive --yes` | Custom dims | edit |
| `custom-metrics list -p <id>` / `get` / `create --parameter-name … --measurement-unit …` / `update` / `archive --yes` | Custom metrics | edit |

### `ga4 admin links` — Third-party links

| Command | Purpose | Min scope |
|---|---|---|
| `links firebase-list -p <id>` / `firebase-create --firebase-project projects/…` / `firebase-delete <id> --yes` | Firebase links | edit |
| `links ads-list -p <id>` / `ads-create --customer-id …` / `ads-update` / `ads-delete <id> --yes` | Google Ads links | edit |
| `links bigquery-list -p <id>` / `bigquery-get` / `bigquery-create --project projects/… [--daily-export …]` / `bigquery-update` / `bigquery-delete <id> --yes` | BigQuery links. **Alpha**. | edit |

### `ga4 admin audiences`, `access-bindings`, `annotations` — all alpha

| Command | Purpose | Min scope |
|---|---|---|
| `audiences list -p <id>` / `get` / `create --body-json @audience.json` / `archive --yes` | Audiences. **Alpha**. | edit |
| `access-bindings list --account <id>` (or `--property`) / `get` / `create --user <email> -r predefinedRoles/admin` / `update` / `delete --yes` | Per-user roles. **Alpha**. | manage.users |
| `access-bindings batch-{create,get,update,delete} --bindings-json @list.json` | Batch operations. **Alpha**. | manage.users |
| `annotations list -p <id>` / `get` / `create --title … --annotation-date YYYY-MM-DD` (or `--start-date/--end-date`) / `update` / `delete --yes` | Reporting-data annotations. **Alpha**. | edit |

Alpha endpoints may change shape without notice; keep an eye on `google-analytics-admin` release notes if you script against them.

### `ga4 mp` — Measurement Protocol

| Command | Purpose |
|---|---|
| `ga4 mp send --measurement-id G-XXX --api-secret … --events-json @events.json` | Fire-and-forget send to `/mp/collect` |
| `ga4 mp validate --measurement-id G-XXX --api-secret … --events-json @events.json` | Debug endpoint — returns per-event validation findings |

Single-event shortcut: `--event-name purchase --event-params '{"value":12.34,"currency":"USD"}'`. For Firebase/app streams, replace `--measurement-id` with `--firebase-app-id`. `--endpoint eu` routes through the EU regional endpoint.

MP limits (enforced locally before sending): 25 events/request, 40-char event names, 25 params/event. See `references/admin-api.md` for full limits including param value length.

## Writing reports

```bash
# Last 7 days of active users by country
ga4 data run-report -p 123456789 -d country -m activeUsers -s 7daysAgo -e today

# Week-over-week comparison with two date ranges via request JSON
cat <<'EOF' > /tmp/wow.json
{
  "dimensions": [{"name": "deviceCategory"}],
  "metrics": [{"name": "engagementRate"}, {"name": "sessions"}],
  "date_ranges": [
    {"start_date": "7daysAgo",  "end_date": "yesterday", "name": "this_week"},
    {"start_date": "14daysAgo", "end_date": "8daysAgo",  "name": "last_week"}
  ]
}
EOF
ga4 data run-report -p 123456789 --request-json @/tmp/wow.json

# Filter: only mobile, only pages matching /blog/*
cat <<'EOF' > /tmp/filter.json
{"andGroup": {"expressions": [
  {"filter": {"fieldName": "deviceCategory", "stringFilter": {"value": "mobile"}}},
  {"filter": {"fieldName": "pagePath", "stringFilter": {"matchType": "BEGINS_WITH", "value": "/blog/"}}}
]}}
EOF
ga4 data run-report -p 123456789 -d pagePath -m sessions -s 7daysAgo -e today \
  --dimension-filter-json @/tmp/filter.json
```

For deep filter grammar (AND/OR/NOT, string/numeric/between/in-list filter types), the valid metric-aggregation set, cohort specs, and the "quota token" math, read `references/data-api.md`.

## Admin safety

- **Always `list`/`get` first** before `update`/`delete`/`archive`. Validate you're targeting the right resource.
- **Use `search-change-history`** to audit recent changes before making new ones, and to find who made the last change to a resource.
- **Alpha endpoints may change shape.** If you get an unexpected schema error, check the `google-analytics-admin` package version and the alpha changelog.
- **`update_mask`** — most admin updates require a field mask. The CLI auto-computes it from flag-based updates, but for `--body-json` updates you must pass `--update-mask` explicitly.
- **Scopes** — the CLI requests the union of scopes its commands need. If a command 403s with "insufficient permissions", re-auth with a broader scope (see **Before First Use**).

## Funnel / audience / access patterns

- **Funnels (`run-funnel-report`)** are built as an array of steps, each with a filter expression. The response has two sub-reports — funnel table and funnel visualization. See `references/data-api.md` for step-design patterns (sequential vs. any-order steps, breakdown dimensions, continuous vs. direct).
- **Audiences** (`audiences create`) have a deeply nested schema (filter clauses, scopes, sequences). Build the JSON separately and pass `--body-json @audience.json`. Start from an existing audience (`audiences get`) to see the shape.
- **Access bindings** use `predefinedRoles/*` role names. Common: `predefinedRoles/no-cost-data`, `predefinedRoles/read-and-analyze`, `predefinedRoles/editor`, `predefinedRoles/admin`. Changes at account scope apply to all properties.

## Interpreting output

Engagement benchmarks, attribution model differences, funnel drop-off heuristics, audience sequence vs. condition patterns, realtime reporting caveats, and BigQuery long-term-storage tradeoffs are all in `references/playbook.md`. Read it before drawing conclusions about whether numbers are "good" — GA4's sampling and attribution defaults differ meaningfully from UA and from other analytics tools.

## Troubleshooting

- **"No credentials. Run: ga4 auth login …"** — Exactly what it says. Get a Desktop OAuth client JSON from GCP and log in.
- **"Permission denied"** — The Google account you auth'd with doesn't have GA access. Grant Viewer/Editor in GA Admin → Access Management. Verify with `ga4 admin accounts summaries-list`.
- **"Quota exhausted"** — Pass `--return-property-quota` on a report to see live consumption. Data API tokens reset hourly/daily. GA360 gets 10x limits.
- **"insufficient_scope"** — The stored token was obtained with fewer scopes than this command needs. Re-run `ga4 auth login --client-secret <path> --scope <extra-scope>` (repeatable) to include them.
- **"No property id"** — Pass `--property/-p`, set `GA_PROPERTY_ID`, or `ga4 config set-property <id>`.
- **Alpha schema changed** — Pin `google-analytics-admin` and `google-analytics-data` in `pyproject.toml`, then `uv sync`.
- **Realtime report is empty** — The realtime window is only the last 30 minutes (60 for GA360). If there's genuinely no active traffic, the report will be empty; this is correct.
- **MP send returned 2xx but the event didn't appear** — `mp send` always returns 2xx regardless of validity. Use `mp validate` first to check for rejection reasons.

## Configuration files

- `~/.config/skills/ga4/config.json` — default property and other CLI settings
- `~/.config/skills/ga4/credentials.json` — OAuth user creds (written by `ga4 auth login`)
- Override the config dir with `GA4_CONFIG_DIR=/path/to/dir`

### Migrating from earlier versions

If upgrading from a build that stored config at `~/.config/ga4/`, run `ga4 config migrate --apply` to move the credentials and config to the new location. `ga4 auth status` emits a `deprecation_warning` until the migration runs.
