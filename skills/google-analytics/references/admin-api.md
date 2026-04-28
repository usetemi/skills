# GA4 Admin API — Deep Reference

Resource hierarchy, update_mask conventions, enum values, and the not-obvious rules that trip up CRUD commands.

## Resource hierarchy

```
accounts/{accountId}
├── dataSharingSettings            (1 per account, get only)
├── accessBindings/{bindingId}     (users + roles on this account)
└── properties/{propertyId}
    ├── dataRetentionSettings      (1 per property)
    ├── attributionSettings        (1 per property, alpha)
    ├── googleSignalsSettings      (1 per property, alpha)
    ├── reportingIdentitySettings  (alpha)
    ├── userProvidedDataSettings   (alpha)
    ├── accessBindings/{bindingId}
    ├── keyEvents/{keyEventName}
    ├── customDimensions/{customDimensionId}
    ├── customMetrics/{customMetricId}
    ├── audiences/{audienceId}
    ├── calculatedMetrics/{calculatedMetricId}   (alpha)
    ├── channelGroups/{channelGroupId}           (alpha)
    ├── expandedDataSets/{expandedDataSetId}     (alpha)
    ├── reportingDataAnnotations/{annotationId}  (alpha)
    ├── firebaseLinks/{firebaseLinkId}
    ├── googleAdsLinks/{googleAdsLinkId}
    ├── bigQueryLinks/{bigQueryLinkId}           (alpha)
    ├── displayVideo360AdvertiserLinks/...       (alpha, not in v1)
    ├── searchAds360Links/...                    (alpha, not in v1)
    └── dataStreams/{dataStreamId}
        ├── measurementProtocolSecrets/{secretId}
        ├── sKAdNetworkConversionValueSchema/... (alpha, not in v1)
        ├── eventCreateRules/...                 (alpha, not in v1)
        ├── eventEditRules/...                   (alpha, not in v1)
        ├── globalSiteTag                        (1, alpha)
        ├── enhancedMeasurementSettings          (1, alpha)
        └── dataRedactionSettings                (1, alpha)
```

Every resource name is the full path. E.g., a measurement protocol secret's full resource name is `properties/123/dataStreams/456/measurementProtocolSecrets/789`. The `ga4` CLI accepts short ids where unambiguous and auto-expands.

## `update_mask` on PATCH

Admin API writes use PATCH semantics — you pass the full resource with the fields you want to change, plus an `update_mask` (FieldMask) listing which fields to apply. Fields not in the mask are ignored even if set in the resource body.

Field paths are snake_case. Nested fields use dotted paths.

Examples:
- Rename a property: `update_mask = "display_name"`
- Rename + change time zone: `update_mask = "display_name,time_zone"`
- Update a nested stream URI: `update_mask = "web_stream_data.default_uri"`

The `ga4` CLI auto-computes the mask when you pass individual flags. When using `--body-json`, you must pass `--update-mask` explicitly.

**Bad idea**: `update_mask = "*"` — most Admin resources don't accept wildcard mask. Always list exact paths.

## Soft-delete vs archive vs delete

Three distinct lifecycle operations with different semantics:

| Op | Applies to | Reversible? | Data fate |
|---|---|---|---|
| `delete` | `accounts`, `properties`, `dataStreams` | Recoverable from trash for 35 days (accounts, properties); data streams are ~immediate | Data retained under retention settings |
| `archive` | `customDimensions`, `customMetrics`, `audiences` | Yes (no "unarchive" endpoint exists, but data is preserved — contact GA support) | Data retained, no new collection |
| `delete` | `keyEvents`, `measurementProtocolSecrets`, `firebaseLinks`, `googleAdsLinks`, `bigQueryLinks`, `accessBindings`, `reportingDataAnnotations`, `customDimensions` (deprecated), `customMetrics` (deprecated) | No | Config lost; collected data unchanged |

Archive is the safer op where available. Delete on custom dims/metrics is deprecated in favor of archive.

## Key events replace conversion events

GA4's "conversion events" were renamed to "key events" in 2024. The two API resources coexist:

- `conversionEvents.*` — **deprecated**. Still works on older properties but not on new ones.
- `keyEvents.*` — current API. Same shape (eventName, countingMethod, defaultValue).

Always use `ga4 admin key-events` for new properties. Existing `conversionEvents` stay as-is unless migrated.

`counting_method`:
- `ONCE_PER_EVENT` (default) — every matching event increments the count
- `ONCE_PER_SESSION` — only the first match per session counts

`default_value` is a `{numeric_value, currency_code}` pair. Used when the event doesn't carry an explicit `value` param. Optional.

## Custom dimensions and metrics

Custom dimension `scope`:
- `EVENT` — most common. Tied to a specific event parameter.
- `USER` — user-scoped. Tied to a `user_properties` key (set via `gtag` or MP).
- `ITEM` — e-commerce item scope.

Custom metric `scope`:
- `EVENT` — the only supported scope.

`parameter_name` and `scope` are **immutable** after creation. Only `display_name`, `description`, `disallow_ads_personalization`, and `measurement_unit` (for metrics) can be patched.

`measurement_unit` enum for custom metrics: `STANDARD` (count), `CURRENCY`, `FEET`, `METERS`, `KILOMETERS`, `MILES`, `MILLISECONDS`, `SECONDS`, `MINUTES`, `HOURS`.

`restricted_metric_type` (for metrics): `COST_DATA` or `REVENUE_DATA`. Marks the metric so access can be restricted to specific roles.

## Data retention

`event_data_retention` enum (default is `TWO_MONTHS`):

- `TWO_MONTHS` — default for standard properties
- `FOURTEEN_MONTHS` — max for standard properties
- `TWENTY_SIX_MONTHS`, `THIRTY_EIGHT_MONTHS`, `FIFTY_MONTHS` — GA360 only

`reset_user_data_on_new_activity` (bool, default true) — extend user-level data's retention window on any new activity. If false, user data rolls off on a fixed schedule regardless of whether the user returned.

Recommended default for most properties: `FOURTEEN_MONTHS`, `reset_user_data_on_new_activity=true`.

## Enhanced measurement (alpha)

`enhancedMeasurementSettings` (one per web stream) controls the auto-collected event set:

- `stream_enabled` — master switch
- `scrolls_enabled`, `outbound_clicks_enabled`, `site_search_enabled`
- `video_engagement_enabled`, `file_downloads_enabled`
- `form_interactions_enabled`, `page_changes_enabled` (SPA route changes)
- `search_query_parameter` — comma-separated list of query params to treat as site search (`q,s,search,query,keyword`)

All default to true. Turning things off reduces the event stream but also reduces data for reports.

## Measurement Protocol secrets

Two important rules:

1. **You must call `properties acknowledge-user-data` first** before `measurement-secrets create` succeeds. The acknowledgement string changes; see the current value in the API error message if your first attempt fails.
2. **The `secret_value` is only returned on `create`.** Subsequent `get` / `list` / `update` calls return the metadata but not the secret. If you lose the secret, delete and recreate.

Each data stream can have multiple MP secrets (useful for rotating keys). Rotate by creating a new one, migrating callers, then deleting the old one.

## Access bindings

`roles` is a list of role resource names. Common predefined:

| Role | What it allows |
|---|---|
| `predefinedRoles/no-cost-data` | Reports without cost data |
| `predefinedRoles/no-revenue-data` | Reports without revenue data |
| `predefinedRoles/read-and-analyze` | Full read |
| `predefinedRoles/collaborate` | Read + collaborate on shared assets |
| `predefinedRoles/editor` | Read + write config (not users) |
| `predefinedRoles/admin` | Editor + user management |

`user` is an email. `group` is a group resource name (Cloud Identity groups).

A single binding can carry multiple roles. The effective permission is the union.

Account-level bindings cascade to all properties. Property-level bindings scope tighter.

## Accounts vs properties — subtle gotchas

- **`accounts.update` is very limited** — only `display_name` and `region_code` are mutable. Everything else on the account (industry, ownership) is immutable once set.
- **`provision-ticket`** returns a ticket id; direct the user to `https://analytics.google.com/analytics/web/?provisioningSignup=false#<ticketId>` to finish creation. Not a one-shot create.
- **`properties.delete` is soft** — recoverable from the trash for 35 days. `accounts.delete` likewise. After 35 days, the resource and its collected data are permanently purged.
- **`properties.create` requires `parent` as an account resource name** (`accounts/123`), not a bare account id. The CLI's `--parent 123` shortcut auto-expands.
- **Roll-up properties, subproperties** — not in v1 of this CLI.

## Links

Three link types are covered in v1:

- **Firebase** (`firebaseLinks`) — minimal shape, just a `project` field (Firebase project resource name).
- **Google Ads** (`googleAdsLinks`) — `customer_id` (digits only), `ads_personalization_enabled`. Link has effective auto-tagging and Ads reporting.
- **BigQuery** (`bigQueryLinks`) — `project` (GCP project), `daily_export_enabled`, `streaming_export_enabled`, `fresh_daily_export_enabled`, `include_advertising_id`, `dataset_location`. Alpha.

Not yet covered: DV360, SA360, AdSense. Easy to add later with the same pattern.

## Annotations (alpha)

Reporting data annotations mark a single date or a date range in reports with a title + optional description + color. Useful for flagging "we launched feature X on 2026-03-04" so spikes in data have context.

`color` enum: `PURPLE`, `BROWN`, `BLUE`, `GREEN`, `RED`, `CYAN`, `ORANGE` (plus a few others — check the alpha proto).

Either `annotation_date` (single day, `YYYY-MM-DD`) or `annotation_date_range` (`{start_date, end_date}`), not both.

## Change history

`search_change_history_events` is the forensic tool. Filter by:

- `resource_type` — `ACCOUNT`, `PROPERTY`, `DATA_STREAM`, `KEY_EVENT`, `CUSTOM_DIMENSION`, `CUSTOM_METRIC`, `AUDIENCE`, `ACCESS_BINDING`, and several more.
- `action` — `CREATED`, `UPDATED`, `DELETED`.
- `actor_email` — who did it.
- `earliest_change_time` / `latest_change_time` — RFC 3339 timestamps.

Retention: ~6 months. For longer audit needs, export periodically via this API.

## Access report

Who accessed what GA data, when. Distinct from the change-history API — change history is about config mutations; access report is about data reads.

Dimensions: `userEmail`, `userId`, `epochTimeMicros`, `dateTime`, `accessCount`, `propertyId`, `reportType`, `method`.

Metrics: `accessCount`.

Runs at both account and property scope. Filters work the same as Data API `dimension_filter` / `metric_filter`.

Common use: **"who queried this property in the last 7 days"** — `-d userEmail -m accessCount -s 7daysAgo -e today`.
