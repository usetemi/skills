"""`ga4 data` — Data API v1beta (plus high-value v1alpha additions).

Reporting is the primary value prop of the GA4 API surface. This module covers:
  - run-report, run-pivot-report (beta)
  - batch-run-reports, batch-run-pivot-reports (beta)
  - run-realtime-report (beta)
  - check-compatibility, get-metadata (beta)
  - audience-exports CRUD + query (beta)
  - run-funnel-report (alpha)

Most commands accept a `--request-json` escape hatch (inline JSON or `@file`) for
the full AST, since some of GA4's request shapes (filter expressions, pivots,
cohorts, funnels) are too nested to express cleanly via flags. Simple `run-report`
supports the common-case flags directly.
"""

from __future__ import annotations

from typing import Any

import click
from google.analytics.data_v1beta import (
    BatchRunPivotReportsRequest,
    BatchRunReportsRequest,
    CheckCompatibilityRequest,
    DateRange,
    Dimension,
    GetMetadataRequest,
    Metric,
    MetricAggregation,
    RunPivotReportRequest,
    RunRealtimeReportRequest,
    RunReportRequest,
)
from google.analytics.data_v1beta.types import MinuteRange
from google.api_core import exceptions as gax

from ga4.auth import SCOPE_READONLY
from ga4.client import (
    collect_paged,
    data_client_alpha,
    data_client_beta,
    handle_api_error,
    load_json_arg,
    output_json,
    proto_to_dict,
    split_csv,
)
from ga4.config import resolve_property

METRIC_AGGREGATION_MAP = {
    "TOTAL": MetricAggregation.TOTAL,
    "MAXIMUM": MetricAggregation.MAXIMUM,
    "MINIMUM": MetricAggregation.MINIMUM,
    "COUNT": MetricAggregation.COUNT,
}

MAX_BATCH_REQUESTS = 5  # Data API caps batchRunReports / batchRunPivotReports at 5 each.


@click.group()
def data() -> None:
    """Data API — reports, realtime, metadata, audience exports."""


# ---------- run-report ----------

@data.command("run-report")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--dimensions", "-d", multiple=True,
              help="Dimension name. Repeatable or comma-separated.")
@click.option("--metrics", "-m", multiple=True,
              help="Metric name. Repeatable or comma-separated.")
@click.option("--start-date", "-s", default=None,
              help="YYYY-MM-DD, NdaysAgo, today, yesterday.")
@click.option("--end-date", "-e", default=None)
@click.option("--date-range-name", default=None,
              help="Optional name for the date range (surfaces in response).")
@click.option("--dimension-filter-json", default=None,
              help="dimensionFilter JSON (FilterExpression). `@path` reads from file.")
@click.option("--metric-filter-json", default=None,
              help="metricFilter JSON (FilterExpression). `@path` reads from file.")
@click.option("--order-by-json", default=None,
              help="orderBys JSON array. `@path` reads from file.")
@click.option("--metric-aggregation", multiple=True,
              type=click.Choice(list(METRIC_AGGREGATION_MAP)),
              help="TOTAL | MAXIMUM | MINIMUM | COUNT. Repeatable.")
@click.option("--cohort-spec-json", default=None,
              help="cohortSpec JSON. `@path` reads from file.")
@click.option("--comparisons-json", default=None,
              help="comparisons JSON array. `@path` reads from file.")
@click.option("--limit", "-l", type=int, default=None)
@click.option("--offset", "-o", type=int, default=None)
@click.option("--currency-code", default=None, help="ISO 4217 (overrides property default).")
@click.option("--keep-empty-rows", is_flag=True)
@click.option("--return-property-quota", is_flag=True)
@click.option("--request-json", default=None,
              help="Full RunReportRequest JSON — overrides all other flags except --property.")
def data_run_report(
    property_flag: str | None,
    dimensions: tuple[str, ...],
    metrics: tuple[str, ...],
    start_date: str | None,
    end_date: str | None,
    date_range_name: str | None,
    dimension_filter_json: str | None,
    metric_filter_json: str | None,
    order_by_json: str | None,
    metric_aggregation: tuple[str, ...],
    cohort_spec_json: str | None,
    comparisons_json: str | None,
    limit: int | None,
    offset: int | None,
    currency_code: str | None,
    keep_empty_rows: bool,
    return_property_quota: bool,
    request_json: str | None,
) -> None:
    """Run a Data API report."""
    property_name = resolve_property(property_flag)
    client = data_client_beta([SCOPE_READONLY])
    if request_json:
        body = load_json_arg(request_json)
        if not isinstance(body, dict):
            raise click.ClickException("--request-json must be a JSON object.")
        body["property"] = property_name
        request = RunReportRequest(mapping=body)
    else:
        dim_list = split_csv(dimensions)
        metric_list = split_csv(metrics)
        request = RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name=d) for d in dim_list],
            metrics=[Metric(name=m) for m in metric_list],
            metric_aggregations=[METRIC_AGGREGATION_MAP[m] for m in metric_aggregation],
            limit=limit or 0,
            offset=offset or 0,
            currency_code=currency_code or "",
            keep_empty_rows=keep_empty_rows,
            return_property_quota=return_property_quota,
        )
        if start_date or end_date:
            date_range = DateRange(start_date=start_date or "", end_date=end_date or "")
            if date_range_name:
                date_range.name = date_range_name
            request.date_ranges = [date_range]
        _apply_filters(
            request, dimension_filter_json=dimension_filter_json,
            metric_filter_json=metric_filter_json,
        )
        _apply_order_bys(request, order_by_json)
        if cohort_spec_json:
            from google.analytics.data_v1beta import CohortSpec
            request.cohort_spec = CohortSpec(mapping=load_json_arg(cohort_spec_json))
        if comparisons_json:
            request.comparisons = load_json_arg(comparisons_json)
    try:
        response = client.run_report(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


def _apply_filters(
    request: Any, *, dimension_filter_json: str | None, metric_filter_json: str | None,
) -> None:
    from google.analytics.data_v1beta import FilterExpression
    if dimension_filter_json:
        request.dimension_filter = FilterExpression(mapping=load_json_arg(dimension_filter_json))
    if metric_filter_json:
        request.metric_filter = FilterExpression(mapping=load_json_arg(metric_filter_json))


def _apply_order_bys(request: Any, order_by_json: str | None) -> None:
    if not order_by_json:
        return
    entries = load_json_arg(order_by_json)
    if not isinstance(entries, list):
        raise click.ClickException("--order-by-json must be a JSON array.")
    from google.analytics.data_v1beta import OrderBy
    request.order_bys = [OrderBy(mapping=e) for e in entries]


# ---------- run-pivot-report ----------

@data.command("run-pivot-report")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--request-json", required=True,
              help="Full RunPivotReportRequest JSON. Pivots are too nested for flag construction.")
def data_run_pivot_report(property_flag: str | None, request_json: str) -> None:
    """Run a pivot report. Requires full --request-json (pivots, cohortSpec, etc.)."""
    property_name = resolve_property(property_flag)
    body = load_json_arg(request_json)
    if not isinstance(body, dict):
        raise click.ClickException("--request-json must be a JSON object.")
    body["property"] = property_name
    request = RunPivotReportRequest(mapping=body)
    client = data_client_beta([SCOPE_READONLY])
    try:
        response = client.run_pivot_report(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- batch-run-reports ----------

@data.command("batch-run-reports")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--requests-json", required=True,
              help="JSON array of RunReportRequest bodies (max 5). `@path` reads from file.")
def data_batch_run_reports(property_flag: str | None, requests_json: str) -> None:
    """Batch up to 5 run-report requests in one call."""
    property_name = resolve_property(property_flag)
    bodies = load_json_arg(requests_json)
    if not isinstance(bodies, list):
        raise click.ClickException("--requests-json must be a JSON array.")
    if len(bodies) > MAX_BATCH_REQUESTS:
        raise click.ClickException(
            f"Max {MAX_BATCH_REQUESTS} requests per batch; got {len(bodies)}.",
        )
    requests = [RunReportRequest(mapping=b) for b in bodies]
    request = BatchRunReportsRequest(property=property_name, requests=requests)
    client = data_client_beta([SCOPE_READONLY])
    try:
        response = client.batch_run_reports(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data.command("batch-run-pivot-reports")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--requests-json", required=True,
              help="JSON array of RunPivotReportRequest bodies (max 5). `@path` reads from file.")
def data_batch_run_pivot_reports(property_flag: str | None, requests_json: str) -> None:
    """Batch up to 5 run-pivot-report requests in one call."""
    property_name = resolve_property(property_flag)
    bodies = load_json_arg(requests_json)
    if not isinstance(bodies, list):
        raise click.ClickException("--requests-json must be a JSON array.")
    if len(bodies) > MAX_BATCH_REQUESTS:
        raise click.ClickException(
            f"Max {MAX_BATCH_REQUESTS} requests per batch; got {len(bodies)}.",
        )
    requests = [RunPivotReportRequest(mapping=b) for b in bodies]
    request = BatchRunPivotReportsRequest(property=property_name, requests=requests)
    client = data_client_beta([SCOPE_READONLY])
    try:
        response = client.batch_run_pivot_reports(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- run-realtime-report ----------

@data.command("run-realtime-report")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--dimensions", "-d", multiple=True)
@click.option("--metrics", "-m", multiple=True)
@click.option("--dimension-filter-json", default=None)
@click.option("--metric-filter-json", default=None)
@click.option("--order-by-json", default=None)
@click.option("--metric-aggregation", multiple=True,
              type=click.Choice(list(METRIC_AGGREGATION_MAP)))
@click.option("--start-minutes-ago", type=int, default=None,
              help="Minutes ago to start the window (0-30 for standard, 0-60 for GA360).")
@click.option("--end-minutes-ago", type=int, default=None,
              help="Minutes ago to end the window.")
@click.option("--limit", "-l", type=int, default=None)
@click.option("--return-property-quota", is_flag=True)
@click.option("--request-json", default=None,
              help="Full RunRealtimeReportRequest JSON (overrides flags).")
def data_run_realtime_report(
    property_flag: str | None,
    dimensions: tuple[str, ...],
    metrics: tuple[str, ...],
    dimension_filter_json: str | None,
    metric_filter_json: str | None,
    order_by_json: str | None,
    metric_aggregation: tuple[str, ...],
    start_minutes_ago: int | None,
    end_minutes_ago: int | None,
    limit: int | None,
    return_property_quota: bool,
    request_json: str | None,
) -> None:
    """Run a realtime report. Window is last 30 minutes (60 for GA360)."""
    property_name = resolve_property(property_flag)
    client = data_client_beta([SCOPE_READONLY])
    if request_json:
        body = load_json_arg(request_json)
        if not isinstance(body, dict):
            raise click.ClickException("--request-json must be a JSON object.")
        body["property"] = property_name
        request = RunRealtimeReportRequest(mapping=body)
    else:
        dim_list = split_csv(dimensions)
        metric_list = split_csv(metrics)
        request = RunRealtimeReportRequest(
            property=property_name,
            dimensions=[Dimension(name=d) for d in dim_list],
            metrics=[Metric(name=m) for m in metric_list],
            metric_aggregations=[METRIC_AGGREGATION_MAP[m] for m in metric_aggregation],
            limit=limit or 0,
            return_property_quota=return_property_quota,
        )
        if start_minutes_ago is not None or end_minutes_ago is not None:
            request.minute_ranges = [MinuteRange(
                start_minutes_ago=start_minutes_ago or 0,
                end_minutes_ago=end_minutes_ago or 0,
            )]
        _apply_filters(
            request, dimension_filter_json=dimension_filter_json,
            metric_filter_json=metric_filter_json,
        )
        _apply_order_bys(request, order_by_json)
    try:
        response = client.run_realtime_report(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- check-compatibility ----------

@data.command("check-compatibility")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--dimensions", "-d", multiple=True)
@click.option("--metrics", "-m", multiple=True)
@click.option("--dimension-filter-json", default=None)
@click.option("--metric-filter-json", default=None)
@click.option("--compatibility-filter",
              type=click.Choice(["COMPATIBLE", "INCOMPATIBLE"]),
              default=None, help="Limit results to compatible or incompatible entries.")
def data_check_compatibility(
    property_flag: str | None,
    dimensions: tuple[str, ...],
    metrics: tuple[str, ...],
    dimension_filter_json: str | None,
    metric_filter_json: str | None,
    compatibility_filter: str | None,
) -> None:
    """Check which dimensions + metrics are compatible for a given property."""
    property_name = resolve_property(property_flag)
    client = data_client_beta([SCOPE_READONLY])
    dim_list = split_csv(dimensions)
    metric_list = split_csv(metrics)
    request = CheckCompatibilityRequest(
        property=property_name,
        dimensions=[Dimension(name=d) for d in dim_list],
        metrics=[Metric(name=m) for m in metric_list],
    )
    if compatibility_filter:
        request.compatibility_filter = compatibility_filter
    _apply_filters(
        request, dimension_filter_json=dimension_filter_json,
        metric_filter_json=metric_filter_json,
    )
    try:
        response = client.check_compatibility(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- get-metadata ----------

@data.command("get-metadata")
@click.option("--property", "-p", "property_flag", default=None,
              help="Property id. Pass `properties/0` for universal metadata (no property-specific customs).")
def data_get_metadata(property_flag: str | None) -> None:
    """Get the Dimension + Metric catalog for a property (or universal via `properties/0`)."""
    property_name = resolve_property(property_flag)
    client = data_client_beta([SCOPE_READONLY])
    try:
        response = client.get_metadata(request=GetMetadataRequest(name=f"{property_name}/metadata"))
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- audience exports ----------

@data.group("audience-exports")
def audience_exports() -> None:
    """Audience Export lifecycle: create, get, list, query."""


@audience_exports.command("create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--audience", required=True, help="Audience resource name `properties/X/audiences/Y`.")
@click.option("--dimensions", "-d", multiple=True, required=True,
              help="Dimension names to include in the export. Repeatable.")
def audience_exports_create(
    property_flag: str | None, audience: str, dimensions: tuple[str, ...],
) -> None:
    """Create an audience export. Returns an operation; state machine is CREATING → ACTIVE or FAILED."""
    from google.analytics.data_v1beta import AudienceDimension, AudienceExport
    property_name = resolve_property(property_flag)
    client = data_client_beta([SCOPE_READONLY])
    export = AudienceExport(
        audience=audience,
        dimensions=[AudienceDimension(dimension_name=d) for d in split_csv(dimensions)],
    )
    try:
        operation = client.create_audience_export(parent=property_name, audience_export=export)
        output_json({
            "status": "creating",
            "operation_name": operation.operation.name,
            "metadata": proto_to_dict(operation.metadata) if operation.metadata else None,
        })
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@audience_exports.command("get")
@click.argument("name")
def audience_exports_get(name: str) -> None:
    """Get an audience export by full resource name `properties/X/audienceExports/Y`."""
    client = data_client_beta([SCOPE_READONLY])
    try:
        export = client.get_audience_export(name=name)
        output_json(proto_to_dict(export))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@audience_exports.command("list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def audience_exports_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List audience exports."""
    from google.analytics.data_v1beta import ListAudienceExportsRequest
    property_name = resolve_property(property_flag)
    client = data_client_beta([SCOPE_READONLY])
    try:
        request = ListAudienceExportsRequest(parent=property_name, page_size=page_size or 0)
        output_json(collect_paged(client.list_audience_exports(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@audience_exports.command("query")
@click.argument("name")
@click.option("--limit", "-l", type=int, default=None)
@click.option("--offset", "-o", type=int, default=None)
def audience_exports_query(name: str, limit: int | None, offset: int | None) -> None:
    """Query rows from a completed audience export."""
    from google.analytics.data_v1beta import QueryAudienceExportRequest
    client = data_client_beta([SCOPE_READONLY])
    request = QueryAudienceExportRequest(
        name=name, limit=limit or 0, offset=offset or 0,
    )
    try:
        response = client.query_audience_export(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- run-funnel-report (alpha) ----------

@data.command("run-funnel-report")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--request-json", required=True,
              help="Full RunFunnelReportRequest JSON (funnel steps, breakdown, "
                   "visualization type). `@path` reads from file.")
def data_run_funnel_report(property_flag: str | None, request_json: str) -> None:
    """Run a funnel report (conversion path drop-off). Alpha."""
    from google.analytics.data_v1alpha import RunFunnelReportRequest

    property_name = resolve_property(property_flag)
    body = load_json_arg(request_json)
    if not isinstance(body, dict):
        raise click.ClickException("--request-json must be a JSON object.")
    body["property"] = property_name
    request = RunFunnelReportRequest(mapping=body)
    client = data_client_alpha([SCOPE_READONLY])
    try:
        response = client.run_funnel_report(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
