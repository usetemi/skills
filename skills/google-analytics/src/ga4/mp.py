"""`ga4 mp` — Measurement Protocol (GA4) event ingestion.

Sends event payloads directly to Google's MP endpoints. Uses raw HTTP (httpx)
because there is no official Python client — MP is a simple fire-and-forget
HTTP endpoint plus a validation endpoint.

Endpoints:
  POST https://www.google-analytics.com/mp/collect       — production
  POST https://www.google-analytics.com/debug/mp/collect — validation (returns findings)
  POST https://region1.google-analytics.com/mp/collect   — EU regional endpoint

Auth is a per-stream `api_secret` + either `measurement_id` (web) or
`firebase_app_id` (Firebase/app). Not an OAuth flow.
"""

from __future__ import annotations

import json

import click
import httpx

from ga4.client import load_json_arg, output_json

PROD_ENDPOINT = "https://www.google-analytics.com/mp/collect"
DEBUG_ENDPOINT = "https://www.google-analytics.com/debug/mp/collect"
EU_PROD_ENDPOINT = "https://region1.google-analytics.com/mp/collect"

EVENT_NAME_MAX = 40
PARAM_NAME_MAX = 40
USER_PROP_NAME_MAX = 24
EVENTS_PER_REQUEST = 25
PARAMS_PER_EVENT = 25


def _build_body(
    client_id: str | None,
    user_id: str | None,
    timestamp_micros: int | None,
    user_properties: str | None,
    consent: str | None,
    events: list,
) -> dict:
    body: dict = {"events": events}
    if client_id is not None:
        body["client_id"] = client_id
    if user_id is not None:
        body["user_id"] = user_id
    if timestamp_micros is not None:
        body["timestamp_micros"] = timestamp_micros
    if user_properties:
        body["user_properties"] = load_json_arg(user_properties)
    if consent:
        body["consent"] = load_json_arg(consent)
    return body


def _validate_events(events: list) -> None:
    if len(events) > EVENTS_PER_REQUEST:
        raise click.ClickException(
            f"Too many events: {len(events)} > {EVENTS_PER_REQUEST} per request.",
        )
    for event in events:
        if not isinstance(event, dict) or "name" not in event:
            raise click.ClickException(f"Each event needs a 'name' field: {event!r}")
        name = event["name"]
        if len(name) > EVENT_NAME_MAX:
            raise click.ClickException(
                f"Event name {name!r} exceeds {EVENT_NAME_MAX} chars.",
            )
        params = event.get("params") or {}
        if len(params) > PARAMS_PER_EVENT:
            raise click.ClickException(
                f"Event {name!r} has {len(params)} params (> {PARAMS_PER_EVENT}).",
            )


@click.group()
def mp() -> None:
    """Measurement Protocol — send and validate GA4 events."""


def _shared_mp_options(func):
    for option in reversed([
        click.option("--measurement-id", default=None,
                     help="Web stream measurement id (G-XXXXXXXX). "
                          "Mutually exclusive with --firebase-app-id."),
        click.option("--firebase-app-id", default=None,
                     help="Firebase/app stream id. Mutually exclusive with --measurement-id."),
        click.option("--api-secret", required=True,
                     help="MP api_secret for the stream (from ga4 admin measurement-secrets)."),
        click.option("--client-id", default=None, help="Required for browser/device events."),
        click.option("--user-id", default=None, help="Optional authenticated user id."),
        click.option("--timestamp-micros", type=int, default=None,
                     help="Unix epoch microseconds. Backdate up to 72 hours."),
        click.option("--user-properties", default=None,
                     help='JSON map of user_properties (e.g., `{"tier":{"value":"pro"}}`). `@path` ok.'),
        click.option("--consent", default=None,
                     help='Consent JSON (e.g., `{"ad_user_data":"GRANTED"}`). `@path` ok.'),
        click.option("--events-json", default=None,
                     help="JSON array of events. `@path/to/file.json` reads from disk."),
        click.option("--event-name", default=None,
                     help="Shortcut: single event with this name. Use with --event-params."),
        click.option("--event-params", default=None,
                     help="Shortcut: JSON params for the single --event-name event."),
        click.option("--endpoint",
                     type=click.Choice(["us", "eu"], case_sensitive=False),
                     default="us", help="Regional endpoint."),
    ]):
        func = option(func)
    return func


def _resolve_events(
    events_json: str | None, event_name: str | None, event_params: str | None,
) -> list:
    if events_json and (event_name or event_params):
        raise click.ClickException(
            "Pass either --events-json OR --event-name/--event-params, not both.",
        )
    if events_json:
        events = load_json_arg(events_json)
        if not isinstance(events, list):
            raise click.ClickException("--events-json must be a JSON array.")
        return events
    if event_name:
        event: dict = {"name": event_name}
        if event_params:
            params = load_json_arg(event_params)
            if not isinstance(params, dict):
                raise click.ClickException("--event-params must be a JSON object.")
            event["params"] = params
        return [event]
    raise click.ClickException(
        "Provide --events-json or --event-name [--event-params].",
    )


def _validate_ids(measurement_id: str | None, firebase_app_id: str | None) -> None:
    if not measurement_id and not firebase_app_id:
        raise click.ClickException(
            "Provide --measurement-id (web) or --firebase-app-id (app).",
        )
    if measurement_id and firebase_app_id:
        raise click.ClickException(
            "Pass only one of --measurement-id / --firebase-app-id.",
        )


def _endpoint_url(*, endpoint: str, debug: bool) -> str:
    if endpoint.lower() == "eu":
        return EU_PROD_ENDPOINT if not debug else DEBUG_ENDPOINT
    return PROD_ENDPOINT if not debug else DEBUG_ENDPOINT


def _post(url: str, params: dict, body: dict) -> httpx.Response:
    return httpx.post(url, params=params, json=body, timeout=30.0)


@mp.command("send")
@_shared_mp_options
def mp_send(
    measurement_id: str | None,
    firebase_app_id: str | None,
    api_secret: str,
    client_id: str | None,
    user_id: str | None,
    timestamp_micros: int | None,
    user_properties: str | None,
    consent: str | None,
    events_json: str | None,
    event_name: str | None,
    event_params: str | None,
    endpoint: str,
) -> None:
    """Send events to the GA4 Measurement Protocol.

    Production endpoint returns 2xx regardless of payload validity — use `ga4 mp validate`
    first if you're unsure whether events will be accepted.
    """
    _validate_ids(measurement_id, firebase_app_id)
    events = _resolve_events(events_json, event_name, event_params)
    _validate_events(events)
    body = _build_body(client_id, user_id, timestamp_micros, user_properties, consent, events)
    url = _endpoint_url(endpoint=endpoint, debug=False)
    params: dict = {"api_secret": api_secret}
    if measurement_id:
        params["measurement_id"] = measurement_id
    if firebase_app_id:
        params["firebase_app_id"] = firebase_app_id
    try:
        response = _post(url, params, body)
    except httpx.HTTPError as exc:
        raise click.ClickException(f"HTTP error: {exc}") from exc
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise click.ClickException(
            f"MP /collect returned {exc.response.status_code}: {exc.response.text}",
        ) from exc
    output_json({
        "status": "sent",
        "endpoint": url,
        "http_status": response.status_code,
        "events_count": len(events),
    })


@mp.command("validate")
@_shared_mp_options
def mp_validate(
    measurement_id: str | None,
    firebase_app_id: str | None,
    api_secret: str,
    client_id: str | None,
    user_id: str | None,
    timestamp_micros: int | None,
    user_properties: str | None,
    consent: str | None,
    events_json: str | None,
    event_name: str | None,
    event_params: str | None,
    endpoint: str,
) -> None:
    """Validate events against the debug endpoint. Returns per-event findings."""
    _validate_ids(measurement_id, firebase_app_id)
    events = _resolve_events(events_json, event_name, event_params)
    _validate_events(events)
    body = _build_body(client_id, user_id, timestamp_micros, user_properties, consent, events)
    url = _endpoint_url(endpoint=endpoint, debug=True)
    params: dict = {"api_secret": api_secret}
    if measurement_id:
        params["measurement_id"] = measurement_id
    if firebase_app_id:
        params["firebase_app_id"] = firebase_app_id
    try:
        response = _post(url, params, body)
    except httpx.HTTPError as exc:
        raise click.ClickException(f"HTTP error: {exc}") from exc
    try:
        parsed = response.json()
    except json.JSONDecodeError:
        parsed = {"raw": response.text}
    output_json({
        "endpoint": url,
        "http_status": response.status_code,
        "validation": parsed,
    })
