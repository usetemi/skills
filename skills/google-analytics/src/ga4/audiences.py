"""`ga4 admin audiences` — audience management (Admin API v1alpha)."""

from __future__ import annotations

import click
from google.analytics.admin_v1alpha import (
    Audience,
    ListAudiencesRequest,
)
from google.api_core import exceptions as gax

from ga4.auth import SCOPE_EDIT, SCOPE_READONLY
from ga4.client import (
    admin_client_alpha,
    collect_paged,
    handle_api_error,
    load_json_arg,
    output_json,
    proto_to_dict,
    require_yes,
)
from ga4.config import resolve_property


def _audience_name(property_name: str, audience_id: str) -> str:
    if audience_id.startswith("properties/"):
        return audience_id
    return f"{property_name}/audiences/{audience_id}"


@click.group()
def audiences() -> None:
    """Manage audiences. Alpha — schema may change."""


@audiences.command("list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def audiences_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List audiences. Alpha."""
    parent = resolve_property(property_flag)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        request = ListAudiencesRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_audiences(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@audiences.command("get")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("audience_id")
def audiences_get(property_flag: str | None, audience_id: str) -> None:
    """Get a single audience. Alpha."""
    name = _audience_name(resolve_property(property_flag), audience_id)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        audience = client.get_audience(name=name)
        output_json(proto_to_dict(audience))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@audiences.command("create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--body-json", required=True,
              help="Full Audience JSON (display_name, description, membership_duration_days, "
                   "filter_clauses[], etc.). `@path` reads from file.")
def audiences_create(property_flag: str | None, body_json: str) -> None:
    """Create an audience. Alpha.

    Audiences have a complex nested schema (filter clauses, sequences, scopes).
    Pass the full JSON body rather than trying to express it in flags.
    See references/admin-api.md for schema details.
    """
    parent = resolve_property(property_flag)
    body = load_json_arg(body_json)
    if not isinstance(body, dict):
        raise click.ClickException("--body-json must be a JSON object.")
    audience = Audience(mapping=body)
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        result = client.create_audience(parent=parent, audience=audience)
        output_json({"status": "created", "audience": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@audiences.command("archive")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("audience_id")
@click.option("--yes", "-y", is_flag=True)
def audiences_archive(property_flag: str | None, audience_id: str, *, yes: bool) -> None:
    """Archive an audience. Alpha. Archived audiences no longer accept new members."""
    from google.analytics.admin_v1alpha import ArchiveAudienceRequest

    name = _audience_name(resolve_property(property_flag), audience_id)
    require_yes(yes=yes, action="archive", target=f"audience {name}")
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        client.archive_audience(request=ArchiveAudienceRequest(name=name))
        output_json({"status": "archived", "audience": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
