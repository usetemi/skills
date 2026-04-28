"""`ga4 admin annotations` — reporting data annotations (Admin API v1alpha).

Note: this module deliberately omits `from __future__ import annotations` because
the Click group symbol is `annotations`, which would collide with the future flag.
Python 3.12 handles PEP 604 / 604-style union syntax natively so the future import
isn't needed here.
"""

import click
from google.analytics.admin_v1alpha import (
    ListReportingDataAnnotationsRequest,
    ReportingDataAnnotation,
)
from google.api_core import exceptions as gax

from ga4.auth import SCOPE_EDIT, SCOPE_READONLY
from ga4.client import (
    admin_client_alpha,
    build_update_mask,
    collect_paged,
    handle_api_error,
    load_json_arg,
    output_json,
    proto_to_dict,
    require_yes,
)
from ga4.config import resolve_property


def _annotation_name(property_name: str, annotation_id: str) -> str:
    if annotation_id.startswith("properties/"):
        return annotation_id
    return f"{property_name}/reportingDataAnnotations/{annotation_id}"


@click.group()
def annotations() -> None:
    """Manage reporting data annotations (flag date-range events). Alpha."""


@annotations.command("list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def annotations_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List annotations. Alpha."""
    parent = resolve_property(property_flag)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        request = ListReportingDataAnnotationsRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(
            client.list_reporting_data_annotations(request=request), max_results,
        ))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@annotations.command("get")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("annotation_id")
def annotations_get(property_flag: str | None, annotation_id: str) -> None:
    """Get a single annotation. Alpha."""
    name = _annotation_name(resolve_property(property_flag), annotation_id)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        ann = client.get_reporting_data_annotation(name=name)
        output_json(proto_to_dict(ann))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@annotations.command("create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--title", required=True, help="Short annotation title.")
@click.option("--description", default=None)
@click.option("--color", default=None,
              help="Color enum (e.g., PURPLE, BROWN, BLUE, GREEN, RED, CYAN, ORANGE).")
@click.option("--annotation-date", default=None,
              help="Single-date annotation: YYYY-MM-DD. Use either this OR --start-date/--end-date.")
@click.option("--start-date", default=None, help="Date-range start: YYYY-MM-DD.")
@click.option("--end-date", default=None, help="Date-range end: YYYY-MM-DD.")
@click.option("--body-json", default=None,
              help="Full ReportingDataAnnotation JSON (overrides flags).")
def annotations_create(
    property_flag: str | None,
    title: str,
    description: str | None,
    color: str | None,
    annotation_date: str | None,
    start_date: str | None,
    end_date: str | None,
    body_json: str | None,
) -> None:
    """Create a reporting data annotation. Alpha."""
    from google.type.date_pb2 import Date

    parent = resolve_property(property_flag)
    client = admin_client_alpha([SCOPE_EDIT])
    if body_json:
        body = load_json_arg(body_json)
        if not isinstance(body, dict):
            raise click.ClickException("--body-json must be a JSON object.")
        annotation = ReportingDataAnnotation(mapping=body)
    else:
        annotation = ReportingDataAnnotation(title=title)
        if description is not None:
            annotation.description = description
        if color is not None:
            annotation.color = color
        if annotation_date and (start_date or end_date):
            raise click.ClickException(
                "Pass either --annotation-date OR --start-date/--end-date, not both.",
            )
        if annotation_date:
            y, m, d = (int(x) for x in annotation_date.split("-"))
            annotation.annotation_date = Date(year=y, month=m, day=d)
        elif start_date and end_date:
            ys, ms, ds = (int(x) for x in start_date.split("-"))
            ye, me, de = (int(x) for x in end_date.split("-"))
            annotation.annotation_date_range.start_date = Date(year=ys, month=ms, day=ds)
            annotation.annotation_date_range.end_date = Date(year=ye, month=me, day=de)
        else:
            raise click.ClickException(
                "Provide --annotation-date or --start-date/--end-date (or --body-json).",
            )
    try:
        result = client.create_reporting_data_annotation(
            parent=parent, reporting_data_annotation=annotation,
        )
        output_json({"status": "created", "reporting_data_annotation": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@annotations.command("update")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("annotation_id")
@click.option("--title", default=None)
@click.option("--description", default=None)
@click.option("--color", default=None)
@click.option("--body-json", default=None)
@click.option("--update-mask", default=None,
              help="Comma-separated field paths. Auto-computed from flags.")
def annotations_update(
    property_flag: str | None,
    annotation_id: str,
    title: str | None,
    description: str | None,
    color: str | None,
    body_json: str | None,
    update_mask: str | None,
) -> None:
    """Update an annotation. Alpha."""
    from google.protobuf.field_mask_pb2 import FieldMask

    name = _annotation_name(resolve_property(property_flag), annotation_id)
    client = admin_client_alpha([SCOPE_EDIT])
    if body_json:
        body = load_json_arg(body_json)
        if not isinstance(body, dict):
            raise click.ClickException("--body-json must be a JSON object.")
        body["name"] = name
        annotation = ReportingDataAnnotation(mapping=body)
    else:
        annotation = ReportingDataAnnotation(name=name)
        if title is not None:
            annotation.title = title
        if description is not None:
            annotation.description = description
        if color is not None:
            annotation.color = color
    if update_mask:
        mask = FieldMask(paths=[p.strip() for p in update_mask.split(",") if p.strip()])
    else:
        mask = build_update_mask(title=title, description=description, color=color)
        if not mask.paths:
            raise click.ClickException("No fields to update.")
    try:
        result = client.update_reporting_data_annotation(
            reporting_data_annotation=annotation, update_mask=mask,
        )
        output_json({"status": "updated", "reporting_data_annotation": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@annotations.command("delete")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("annotation_id")
@click.option("--yes", "-y", is_flag=True)
def annotations_delete(property_flag: str | None, annotation_id: str, *, yes: bool) -> None:
    """Delete an annotation. Alpha."""
    name = _annotation_name(resolve_property(property_flag), annotation_id)
    require_yes(yes=yes, action="delete", target=f"annotation {name}")
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        client.delete_reporting_data_annotation(name=name)
        output_json({"status": "deleted", "reporting_data_annotation": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
