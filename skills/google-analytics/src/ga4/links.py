"""`ga4 admin links` — third-party integration links (Firebase, Google Ads, BigQuery).

Firebase + Google Ads are v1beta. BigQuery is v1alpha.
"""

from __future__ import annotations

import click
from google.analytics.admin_v1beta import (
    FirebaseLink,
    GoogleAdsLink,
    ListFirebaseLinksRequest,
    ListGoogleAdsLinksRequest,
)
from google.api_core import exceptions as gax

from ga4.auth import SCOPE_EDIT, SCOPE_READONLY
from ga4.client import (
    admin_client_alpha,
    admin_client_beta,
    build_update_mask,
    collect_paged,
    handle_api_error,
    load_json_arg,
    output_json,
    proto_to_dict,
    require_yes,
)
from ga4.config import resolve_property


def _link_name(property_name: str, link_type: str, link_id: str) -> str:
    if link_id.startswith("properties/"):
        return link_id
    return f"{property_name}/{link_type}/{link_id}"


@click.group()
def links() -> None:
    """Manage third-party integration links (firebase, ads, bigquery)."""


# ---------- Firebase ----------

@links.command("firebase-list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def links_firebase_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List Firebase links."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListFirebaseLinksRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_firebase_links(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("firebase-create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--firebase-project", required=True,
              help="Firebase project resource name (e.g., projects/my-firebase-project).")
def links_firebase_create(property_flag: str | None, firebase_project: str) -> None:
    """Create a Firebase link."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])
    link = FirebaseLink(project=firebase_project)
    try:
        result = client.create_firebase_link(parent=parent, firebase_link=link)
        output_json({"status": "created", "firebase_link": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("firebase-delete")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("link_id")
@click.option("--yes", "-y", is_flag=True)
def links_firebase_delete(property_flag: str | None, link_id: str, *, yes: bool) -> None:
    """Delete a Firebase link."""
    name = _link_name(resolve_property(property_flag), "firebaseLinks", link_id)
    require_yes(yes=yes, action="delete", target=f"firebase link {name}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.delete_firebase_link(name=name)
        output_json({"status": "deleted", "firebase_link": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- Google Ads ----------

@links.command("ads-list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def links_ads_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List Google Ads links."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListGoogleAdsLinksRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_google_ads_links(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("ads-create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--customer-id", required=True, help="Google Ads customer id (digits only).")
@click.option("--ads-personalization-enabled/--no-ads-personalization", default=True)
def links_ads_create(
    property_flag: str | None,
    customer_id: str,
    ads_personalization_enabled: bool,
) -> None:
    """Create a Google Ads link."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])
    link = GoogleAdsLink(
        customer_id=customer_id,
        ads_personalization_enabled=ads_personalization_enabled,
    )
    try:
        result = client.create_google_ads_link(parent=parent, google_ads_link=link)
        output_json({"status": "created", "google_ads_link": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("ads-update")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("link_id")
@click.option("--ads-personalization-enabled", type=bool, default=None)
def links_ads_update(
    property_flag: str | None, link_id: str, ads_personalization_enabled: bool | None,
) -> None:
    """Update a Google Ads link (only ads_personalization_enabled is mutable)."""
    if ads_personalization_enabled is None:
        raise click.ClickException("--ads-personalization-enabled is required.")
    name = _link_name(resolve_property(property_flag), "googleAdsLinks", link_id)
    client = admin_client_beta([SCOPE_EDIT])
    link = GoogleAdsLink(name=name, ads_personalization_enabled=ads_personalization_enabled)
    mask = build_update_mask(ads_personalization_enabled=ads_personalization_enabled)
    try:
        result = client.update_google_ads_link(google_ads_link=link, update_mask=mask)
        output_json({"status": "updated", "google_ads_link": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("ads-delete")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("link_id")
@click.option("--yes", "-y", is_flag=True)
def links_ads_delete(property_flag: str | None, link_id: str, *, yes: bool) -> None:
    """Delete a Google Ads link."""
    name = _link_name(resolve_property(property_flag), "googleAdsLinks", link_id)
    require_yes(yes=yes, action="delete", target=f"google ads link {name}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.delete_google_ads_link(name=name)
        output_json({"status": "deleted", "google_ads_link": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- BigQuery (v1alpha) ----------

@links.command("bigquery-list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def links_bigquery_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List BigQuery links. Alpha."""
    from google.analytics.admin_v1alpha import ListBigQueryLinksRequest

    parent = resolve_property(property_flag)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        request = ListBigQueryLinksRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_big_query_links(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("bigquery-get")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("link_id")
def links_bigquery_get(property_flag: str | None, link_id: str) -> None:
    """Get a single BigQuery link. Alpha."""
    name = _link_name(resolve_property(property_flag), "bigQueryLinks", link_id)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        link = client.get_big_query_link(name=name)
        output_json(proto_to_dict(link))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("bigquery-create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--project", required=True,
              help="GCP project resource name (e.g., projects/my-project).")
@click.option("--daily-export-enabled/--no-daily-export", default=True)
@click.option("--streaming-export-enabled/--no-streaming-export", default=False)
@click.option("--fresh-daily-export-enabled/--no-fresh-daily-export", default=False)
@click.option("--include-advertising-id/--no-advertising-id", default=False)
@click.option("--dataset-location", default=None)
@click.option("--body-json", default=None, help="Full BigQueryLink JSON (overrides flags).")
def links_bigquery_create(
    property_flag: str | None,
    project: str,
    daily_export_enabled: bool,
    streaming_export_enabled: bool,
    fresh_daily_export_enabled: bool,
    include_advertising_id: bool,
    dataset_location: str | None,
    body_json: str | None,
) -> None:
    """Create a BigQuery link. Alpha."""
    from google.analytics.admin_v1alpha import BigQueryLink

    parent = resolve_property(property_flag)
    client = admin_client_alpha([SCOPE_EDIT])
    if body_json:
        body = load_json_arg(body_json)
        if not isinstance(body, dict):
            raise click.ClickException("--body-json must be a JSON object.")
        link = BigQueryLink(mapping=body)
    else:
        link = BigQueryLink(
            project=project,
            daily_export_enabled=daily_export_enabled,
            streaming_export_enabled=streaming_export_enabled,
            fresh_daily_export_enabled=fresh_daily_export_enabled,
            include_advertising_id=include_advertising_id,
        )
        if dataset_location is not None:
            link.dataset_location = dataset_location
    try:
        result = client.create_big_query_link(parent=parent, bigquery_link=link)
        output_json({"status": "created", "bigquery_link": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("bigquery-update")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("link_id")
@click.option("--body-json", required=True, help="Full BigQueryLink JSON.")
@click.option("--update-mask", required=True, help="Comma-separated field paths.")
def links_bigquery_update(
    property_flag: str | None, link_id: str, body_json: str, update_mask: str,
) -> None:
    """Update a BigQuery link. Alpha."""
    from google.analytics.admin_v1alpha import BigQueryLink
    from google.protobuf.field_mask_pb2 import FieldMask

    name = _link_name(resolve_property(property_flag), "bigQueryLinks", link_id)
    body = load_json_arg(body_json)
    if not isinstance(body, dict):
        raise click.ClickException("--body-json must be a JSON object.")
    body["name"] = name
    link = BigQueryLink(mapping=body)
    mask = FieldMask(paths=[p.strip() for p in update_mask.split(",") if p.strip()])
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        result = client.update_big_query_link(bigquery_link=link, update_mask=mask)
        output_json({"status": "updated", "bigquery_link": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@links.command("bigquery-delete")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("link_id")
@click.option("--yes", "-y", is_flag=True)
def links_bigquery_delete(property_flag: str | None, link_id: str, *, yes: bool) -> None:
    """Delete a BigQuery link. Alpha."""
    name = _link_name(resolve_property(property_flag), "bigQueryLinks", link_id)
    require_yes(yes=yes, action="delete", target=f"bigquery link {name}")
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        client.delete_big_query_link(name=name)
        output_json({"status": "deleted", "bigquery_link": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
