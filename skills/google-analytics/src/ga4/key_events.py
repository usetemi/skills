"""`ga4 admin key-events` — key event (conversion event) management (Admin API v1beta)."""

from __future__ import annotations

import click
from google.analytics.admin_v1beta import (
    KeyEvent,
    ListKeyEventsRequest,
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


def _key_event_name(property_name: str, event_id: str) -> str:
    if event_id.startswith("properties/"):
        return event_id
    return f"{property_name}/keyEvents/{event_id}"


@click.group()
def key_events() -> None:
    """Manage key events (GA4's replacement for conversion events)."""


@key_events.command("list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def key_events_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List key events for a property."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListKeyEventsRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_key_events(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@key_events.command("get")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("event_id")
def key_events_get(property_flag: str | None, event_id: str) -> None:
    """Get a single key event."""
    name = _key_event_name(resolve_property(property_flag), event_id)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        event = client.get_key_event(name=name)
        output_json(proto_to_dict(event))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@key_events.command("create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--event-name", required=True, help="Event name (e.g., purchase, sign_up).")
@click.option("--counting-method", default="ONCE_PER_EVENT",
              help="ONCE_PER_EVENT (default) or ONCE_PER_SESSION.")
@click.option("--default-value", type=float, default=None,
              help="Default value for this key event.")
@click.option("--default-currency", default=None,
              help="ISO 4217 currency for --default-value (e.g., USD).")
def key_events_create(
    property_flag: str | None,
    event_name: str,
    counting_method: str,
    default_value: float | None,
    default_currency: str | None,
) -> None:
    """Create a key event."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])
    event = KeyEvent(event_name=event_name, counting_method=counting_method)
    if default_value is not None:
        if default_currency is None:
            raise click.ClickException(
                "--default-value requires --default-currency (ISO 4217 code).",
            )
        event.default_value.numeric_value = default_value
        event.default_value.currency_code = default_currency
    try:
        result = client.create_key_event(parent=parent, key_event=event)
        output_json({"status": "created", "key_event": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@key_events.command("update")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("event_id")
@click.option("--counting-method", default=None,
              help="ONCE_PER_EVENT or ONCE_PER_SESSION.")
@click.option("--default-value", type=float, default=None)
@click.option("--default-currency", default=None)
def key_events_update(
    property_flag: str | None,
    event_id: str,
    counting_method: str | None,
    default_value: float | None,
    default_currency: str | None,
) -> None:
    """Update a key event."""
    if counting_method is None and default_value is None:
        raise click.ClickException(
            "Provide at least one of --counting-method, --default-value.",
        )
    name = _key_event_name(resolve_property(property_flag), event_id)
    client = admin_client_beta([SCOPE_EDIT])
    event = KeyEvent(name=name)
    mask_fields: dict = {}
    if counting_method is not None:
        event.counting_method = counting_method
        mask_fields["counting_method"] = counting_method
    if default_value is not None:
        if default_currency is None:
            raise click.ClickException(
                "--default-value requires --default-currency (ISO 4217 code).",
            )
        event.default_value.numeric_value = default_value
        event.default_value.currency_code = default_currency
        mask_fields["default_value"] = default_value
    mask = build_update_mask(**mask_fields)
    try:
        result = client.update_key_event(key_event=event, update_mask=mask)
        output_json({"status": "updated", "key_event": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@key_events.command("delete")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("event_id")
@click.option("--yes", "-y", is_flag=True)
def key_events_delete(property_flag: str | None, event_id: str, *, yes: bool) -> None:
    """Delete a key event. Irreversible."""
    name = _key_event_name(resolve_property(property_flag), event_id)
    require_yes(yes=yes, action="delete", target=f"key event {name}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.delete_key_event(name=name)
        output_json({"status": "deleted", "key_event": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
