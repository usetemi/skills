"""`ga4 admin custom-metrics` — custom metric CRUD (Admin API v1beta)."""

from __future__ import annotations

import click
from google.analytics.admin_v1beta import (
    ArchiveCustomMetricRequest,
    CustomMetric,
    ListCustomMetricsRequest,
)
from google.api_core import exceptions as gax

from ga4.auth import SCOPE_EDIT, SCOPE_READONLY
from ga4.client import (
    admin_client_beta,
    build_update_mask,
    collect_paged,
    handle_api_error,
    output_json,
    proto_to_dict,
    require_yes,
)
from ga4.config import resolve_property


def _metric_name(property_name: str, metric_id: str) -> str:
    if metric_id.startswith("properties/"):
        return metric_id
    return f"{property_name}/customMetrics/{metric_id}"


@click.group()
def custom_metrics() -> None:
    """Manage custom metrics."""


@custom_metrics.command("list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def custom_metrics_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List custom metrics."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListCustomMetricsRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_custom_metrics(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@custom_metrics.command("get")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("metric_id")
def custom_metrics_get(property_flag: str | None, metric_id: str) -> None:
    """Get a single custom metric."""
    name = _metric_name(resolve_property(property_flag), metric_id)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        metric = client.get_custom_metric(name=name)
        output_json(proto_to_dict(metric))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@custom_metrics.command("create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--parameter-name", required=True)
@click.option("--display-name", required=True)
@click.option("--description", default=None)
@click.option("--measurement-unit", required=True,
              help="STANDARD | CURRENCY | FEET | METERS | KILOMETERS | MILES | "
                   "MILLISECONDS | SECONDS | MINUTES | HOURS")
@click.option("--scope", default="EVENT", help="EVENT (the only supported scope as of now).")
@click.option("--restricted-metric-type", multiple=True,
              help="COST_DATA | REVENUE_DATA. Repeatable.")
def custom_metrics_create(
    property_flag: str | None,
    parameter_name: str,
    display_name: str,
    description: str | None,
    measurement_unit: str,
    scope: str,
    restricted_metric_type: tuple[str, ...],
) -> None:
    """Create a custom metric."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])
    metric = CustomMetric(
        parameter_name=parameter_name,
        display_name=display_name,
        measurement_unit=measurement_unit,
        scope=scope,
        restricted_metric_type=list(restricted_metric_type),
    )
    if description is not None:
        metric.description = description
    try:
        result = client.create_custom_metric(parent=parent, custom_metric=metric)
        output_json({"status": "created", "custom_metric": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@custom_metrics.command("update")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("metric_id")
@click.option("--display-name", default=None)
@click.option("--description", default=None)
@click.option("--measurement-unit", default=None)
def custom_metrics_update(
    property_flag: str | None,
    metric_id: str,
    display_name: str | None,
    description: str | None,
    measurement_unit: str | None,
) -> None:
    """Update a custom metric (parameter_name and scope are immutable)."""
    if display_name is None and description is None and measurement_unit is None:
        raise click.ClickException(
            "Provide at least one of --display-name, --description, --measurement-unit.",
        )
    name = _metric_name(resolve_property(property_flag), metric_id)
    client = admin_client_beta([SCOPE_EDIT])
    metric = CustomMetric(name=name)
    if display_name is not None:
        metric.display_name = display_name
    if description is not None:
        metric.description = description
    if measurement_unit is not None:
        metric.measurement_unit = measurement_unit
    mask = build_update_mask(
        display_name=display_name,
        description=description,
        measurement_unit=measurement_unit,
    )
    try:
        result = client.update_custom_metric(custom_metric=metric, update_mask=mask)
        output_json({"status": "updated", "custom_metric": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@custom_metrics.command("archive")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("metric_id")
@click.option("--yes", "-y", is_flag=True)
def custom_metrics_archive(property_flag: str | None, metric_id: str, *, yes: bool) -> None:
    """Archive a custom metric (data retained, no longer collected)."""
    name = _metric_name(resolve_property(property_flag), metric_id)
    require_yes(yes=yes, action="archive", target=f"custom metric {name}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.archive_custom_metric(request=ArchiveCustomMetricRequest(name=name))
        output_json({"status": "archived", "custom_metric": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
