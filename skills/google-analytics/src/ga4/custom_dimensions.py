"""`ga4 admin custom-dimensions` — custom dimension CRUD (Admin API v1beta)."""

from __future__ import annotations

import click
from google.analytics.admin_v1beta import (
    ArchiveCustomDimensionRequest,
    CustomDimension,
    ListCustomDimensionsRequest,
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


def _dim_name(property_name: str, dim_id: str) -> str:
    if dim_id.startswith("properties/"):
        return dim_id
    return f"{property_name}/customDimensions/{dim_id}"


@click.group()
def custom_dimensions() -> None:
    """Manage custom dimensions."""


@custom_dimensions.command("list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def custom_dimensions_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List custom dimensions for a property."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListCustomDimensionsRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_custom_dimensions(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@custom_dimensions.command("get")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("dim_id")
def custom_dimensions_get(property_flag: str | None, dim_id: str) -> None:
    """Get a single custom dimension."""
    name = _dim_name(resolve_property(property_flag), dim_id)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        dim = client.get_custom_dimension(name=name)
        output_json(proto_to_dict(dim))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@custom_dimensions.command("create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--parameter-name", required=True, help="Event parameter name (e.g., `article_id`).")
@click.option("--display-name", required=True)
@click.option("--description", default=None)
@click.option("--scope", required=True, help="EVENT | USER | ITEM.")
@click.option("--disallow-ads-personalization", is_flag=True)
def custom_dimensions_create(
    property_flag: str | None,
    parameter_name: str,
    display_name: str,
    description: str | None,
    scope: str,
    disallow_ads_personalization: bool,
) -> None:
    """Create a custom dimension."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])
    dim = CustomDimension(
        parameter_name=parameter_name,
        display_name=display_name,
        scope=scope,
        disallow_ads_personalization=disallow_ads_personalization,
    )
    if description is not None:
        dim.description = description
    try:
        result = client.create_custom_dimension(parent=parent, custom_dimension=dim)
        output_json({"status": "created", "custom_dimension": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@custom_dimensions.command("update")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("dim_id")
@click.option("--display-name", default=None)
@click.option("--description", default=None)
@click.option("--disallow-ads-personalization", type=bool, default=None)
def custom_dimensions_update(
    property_flag: str | None,
    dim_id: str,
    display_name: str | None,
    description: str | None,
    disallow_ads_personalization: bool | None,
) -> None:
    """Update a custom dimension (parameter_name and scope are immutable)."""
    if display_name is None and description is None and disallow_ads_personalization is None:
        raise click.ClickException(
            "Provide at least one of --display-name, --description, "
            "--disallow-ads-personalization.",
        )
    name = _dim_name(resolve_property(property_flag), dim_id)
    client = admin_client_beta([SCOPE_EDIT])
    dim = CustomDimension(name=name)
    if display_name is not None:
        dim.display_name = display_name
    if description is not None:
        dim.description = description
    if disallow_ads_personalization is not None:
        dim.disallow_ads_personalization = disallow_ads_personalization
    mask = build_update_mask(
        display_name=display_name,
        description=description,
        disallow_ads_personalization=disallow_ads_personalization,
    )
    try:
        result = client.update_custom_dimension(custom_dimension=dim, update_mask=mask)
        output_json({"status": "updated", "custom_dimension": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@custom_dimensions.command("archive")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("dim_id")
@click.option("--yes", "-y", is_flag=True)
def custom_dimensions_archive(property_flag: str | None, dim_id: str, *, yes: bool) -> None:
    """Archive a custom dimension (data retained, no longer collected)."""
    name = _dim_name(resolve_property(property_flag), dim_id)
    require_yes(yes=yes, action="archive", target=f"custom dimension {name}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.archive_custom_dimension(request=ArchiveCustomDimensionRequest(name=name))
        output_json({"status": "archived", "custom_dimension": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
