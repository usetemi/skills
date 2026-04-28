"""`ga4 admin measurement-secrets` — Measurement Protocol secret CRUD (Admin API v1beta)."""

from __future__ import annotations

import click
from google.analytics.admin_v1beta import (
    ListMeasurementProtocolSecretsRequest,
    MeasurementProtocolSecret,
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


def _stream_parent(property_name: str, stream_id: str) -> str:
    if stream_id.startswith("properties/"):
        return stream_id
    return f"{property_name}/dataStreams/{stream_id}"


def _secret_name(property_name: str, stream_id: str, secret_id: str) -> str:
    if secret_id.startswith("properties/"):
        return secret_id
    return f"{_stream_parent(property_name, stream_id)}/measurementProtocolSecrets/{secret_id}"


@click.group()
def measurement_secrets() -> None:
    """Manage Measurement Protocol secrets (MP api_secret values)."""


@measurement_secrets.command("list")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def measurement_secrets_list(
    property_flag: str | None, stream_id: str,
    max_results: int | None, page_size: int | None,
) -> None:
    """List Measurement Protocol secrets for a stream."""
    parent = _stream_parent(resolve_property(property_flag), stream_id)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListMeasurementProtocolSecretsRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(
            client.list_measurement_protocol_secrets(request=request), max_results,
        ))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@measurement_secrets.command("get")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.argument("secret_id")
def measurement_secrets_get(
    property_flag: str | None, stream_id: str, secret_id: str,
) -> None:
    """Get a Measurement Protocol secret (does NOT return the secret_value)."""
    name = _secret_name(resolve_property(property_flag), stream_id, secret_id)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        secret = client.get_measurement_protocol_secret(name=name)
        output_json(proto_to_dict(secret))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@measurement_secrets.command("create")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.option("--display-name", required=True)
def measurement_secrets_create(
    property_flag: str | None, stream_id: str, display_name: str,
) -> None:
    """Create a Measurement Protocol secret.

    Requires `ga4 admin properties acknowledge-user-data` first.
    The returned object includes the secret_value — store it immediately,
    it cannot be retrieved later.
    """
    parent = _stream_parent(resolve_property(property_flag), stream_id)
    client = admin_client_beta([SCOPE_EDIT])
    secret = MeasurementProtocolSecret(display_name=display_name)
    try:
        result = client.create_measurement_protocol_secret(
            parent=parent, measurement_protocol_secret=secret,
        )
        output_json({"status": "created", "measurement_protocol_secret": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@measurement_secrets.command("update")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.argument("secret_id")
@click.option("--display-name", required=True)
def measurement_secrets_update(
    property_flag: str | None, stream_id: str, secret_id: str, display_name: str,
) -> None:
    """Rename a Measurement Protocol secret."""
    name = _secret_name(resolve_property(property_flag), stream_id, secret_id)
    client = admin_client_beta([SCOPE_EDIT])
    secret = MeasurementProtocolSecret(name=name, display_name=display_name)
    mask = build_update_mask(display_name=display_name)
    try:
        result = client.update_measurement_protocol_secret(
            measurement_protocol_secret=secret, update_mask=mask,
        )
        output_json({"status": "updated", "measurement_protocol_secret": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@measurement_secrets.command("delete")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.argument("secret_id")
@click.option("--yes", "-y", is_flag=True)
def measurement_secrets_delete(
    property_flag: str | None, stream_id: str, secret_id: str, *, yes: bool,
) -> None:
    """Delete a Measurement Protocol secret. Irreversible."""
    name = _secret_name(resolve_property(property_flag), stream_id, secret_id)
    require_yes(yes=yes, action="delete", target=f"measurement protocol secret {name}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.delete_measurement_protocol_secret(name=name)
        output_json({"status": "deleted", "measurement_protocol_secret": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
