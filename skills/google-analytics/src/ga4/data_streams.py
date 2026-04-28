"""`ga4 admin data-streams` — data stream management (Admin API v1beta + v1alpha)."""

from __future__ import annotations

import click
from google.analytics.admin_v1beta import (
    DataStream,
    ListDataStreamsRequest,
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


def _stream_name(property_name: str, stream_id: str) -> str:
    if stream_id.startswith("properties/"):
        return stream_id
    return f"{property_name}/dataStreams/{stream_id}"


@click.group()
def data_streams() -> None:
    """Manage data streams (web / Android / iOS)."""


# ---------- list / get / create / update / delete ----------

@data_streams.command("list")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def data_streams_list(
    property_flag: str | None, max_results: int | None, page_size: int | None,
) -> None:
    """List data streams under a property."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListDataStreamsRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_data_streams(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data_streams.command("get")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
def data_streams_get(property_flag: str | None, stream_id: str) -> None:
    """Get a single data stream by id."""
    name = _stream_name(resolve_property(property_flag), stream_id)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        stream = client.get_data_stream(name=name)
        output_json(proto_to_dict(stream))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data_streams.command("create")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--type", "stream_type", required=True,
              help="WEB_DATA_STREAM | ANDROID_APP_DATA_STREAM | IOS_APP_DATA_STREAM")
@click.option("--display-name", required=True)
@click.option("--uri", default=None, help="For WEB streams: default URI (e.g., https://example.com).")
@click.option("--package-name", default=None, help="For ANDROID streams: package name.")
@click.option("--bundle-id", default=None, help="For IOS streams: bundle id.")
@click.option("--body-json", default=None, help="Full DataStream JSON (overrides flags).")
def data_streams_create(
    property_flag: str | None,
    stream_type: str,
    display_name: str,
    uri: str | None,
    package_name: str | None,
    bundle_id: str | None,
    body_json: str | None,
) -> None:
    """Create a data stream."""
    parent = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])

    if body_json:
        body = load_json_arg(body_json)
        if not isinstance(body, dict):
            raise click.ClickException("--body-json must be a JSON object.")
        stream = DataStream(mapping=body)
    else:
        stream = DataStream(display_name=display_name, type_=stream_type)
        if stream_type == "WEB_DATA_STREAM":
            if not uri:
                raise click.ClickException("WEB_DATA_STREAM requires --uri.")
            stream.web_stream_data.default_uri = uri
        elif stream_type == "ANDROID_APP_DATA_STREAM":
            if not package_name:
                raise click.ClickException("ANDROID_APP_DATA_STREAM requires --package-name.")
            stream.android_app_stream_data.package_name = package_name
        elif stream_type == "IOS_APP_DATA_STREAM":
            if not bundle_id:
                raise click.ClickException("IOS_APP_DATA_STREAM requires --bundle-id.")
            stream.ios_app_stream_data.bundle_id = bundle_id
        else:
            raise click.ClickException(f"Unknown stream type: {stream_type!r}")

    try:
        result = client.create_data_stream(parent=parent, data_stream=stream)
        output_json({"status": "created", "data_stream": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data_streams.command("update")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.option("--display-name", default=None)
@click.option("--body-json", default=None, help="Full DataStream JSON (overrides flags).")
@click.option("--update-mask", default=None, help="Comma-separated field paths.")
def data_streams_update(
    property_flag: str | None,
    stream_id: str,
    display_name: str | None,
    body_json: str | None,
    update_mask: str | None,
) -> None:
    """Update a data stream."""
    from google.protobuf.field_mask_pb2 import FieldMask

    name = _stream_name(resolve_property(property_flag), stream_id)
    client = admin_client_beta([SCOPE_EDIT])
    if body_json:
        body = load_json_arg(body_json)
        if not isinstance(body, dict):
            raise click.ClickException("--body-json must be a JSON object.")
        body["name"] = name
        stream = DataStream(mapping=body)
    else:
        stream = DataStream(name=name)
        if display_name is not None:
            stream.display_name = display_name
    if update_mask:
        mask = FieldMask(paths=[p.strip() for p in update_mask.split(",") if p.strip()])
    else:
        mask = build_update_mask(display_name=display_name)
        if not mask.paths:
            raise click.ClickException("No fields to update. Pass flags or --update-mask.")
    try:
        result = client.update_data_stream(data_stream=stream, update_mask=mask)
        output_json({"status": "updated", "data_stream": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data_streams.command("delete")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.option("--yes", "-y", is_flag=True)
def data_streams_delete(property_flag: str | None, stream_id: str, *, yes: bool) -> None:
    """Delete a data stream. Irreversible."""
    name = _stream_name(resolve_property(property_flag), stream_id)
    require_yes(yes=yes, action="delete", target=f"data stream {name}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.delete_data_stream(name=name)
        output_json({"status": "deleted", "data_stream": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- alpha helpers: global site tag, enhanced measurement, data redaction ----------

@data_streams.command("get-global-site-tag")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
def data_streams_get_global_site_tag(property_flag: str | None, stream_id: str) -> None:
    """Get the global site tag snippet for a web stream. Alpha."""
    name = _stream_name(resolve_property(property_flag), stream_id)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        tag = client.get_global_site_tag(name=f"{name}/globalSiteTag")
        output_json(proto_to_dict(tag))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data_streams.command("get-enhanced-measurement")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
def data_streams_get_enhanced_measurement(property_flag: str | None, stream_id: str) -> None:
    """Get enhanced measurement settings for a web stream. Alpha."""
    name = _stream_name(resolve_property(property_flag), stream_id)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        settings = client.get_enhanced_measurement_settings(
            name=f"{name}/enhancedMeasurementSettings",
        )
        output_json(proto_to_dict(settings))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data_streams.command("update-enhanced-measurement")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.option("--body-json", required=True, help="Full EnhancedMeasurementSettings JSON.")
@click.option("--update-mask", required=True, help="Comma-separated field paths.")
def data_streams_update_enhanced_measurement(
    property_flag: str | None, stream_id: str, body_json: str, update_mask: str,
) -> None:
    """Update enhanced measurement settings. Alpha."""
    from google.analytics.admin_v1alpha import EnhancedMeasurementSettings
    from google.protobuf.field_mask_pb2 import FieldMask

    name = _stream_name(resolve_property(property_flag), stream_id)
    body = load_json_arg(body_json)
    if not isinstance(body, dict):
        raise click.ClickException("--body-json must be a JSON object.")
    body["name"] = f"{name}/enhancedMeasurementSettings"
    settings = EnhancedMeasurementSettings(mapping=body)
    mask = FieldMask(paths=[p.strip() for p in update_mask.split(",") if p.strip()])
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        result = client.update_enhanced_measurement_settings(
            enhanced_measurement_settings=settings, update_mask=mask,
        )
        output_json({"status": "updated", "enhanced_measurement_settings": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data_streams.command("get-data-redaction")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
def data_streams_get_data_redaction(property_flag: str | None, stream_id: str) -> None:
    """Get data redaction settings (PII scrubbing) for a stream. Alpha."""
    name = _stream_name(resolve_property(property_flag), stream_id)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        settings = client.get_data_redaction_settings(name=f"{name}/dataRedactionSettings")
        output_json(proto_to_dict(settings))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@data_streams.command("update-data-redaction")
@click.option("--property", "-p", "property_flag", default=None)
@click.argument("stream_id")
@click.option("--body-json", required=True, help="Full DataRedactionSettings JSON.")
@click.option("--update-mask", required=True, help="Comma-separated field paths.")
def data_streams_update_data_redaction(
    property_flag: str | None, stream_id: str, body_json: str, update_mask: str,
) -> None:
    """Update data redaction settings. Alpha."""
    from google.analytics.admin_v1alpha import DataRedactionSettings
    from google.protobuf.field_mask_pb2 import FieldMask

    name = _stream_name(resolve_property(property_flag), stream_id)
    body = load_json_arg(body_json)
    if not isinstance(body, dict):
        raise click.ClickException("--body-json must be a JSON object.")
    body["name"] = f"{name}/dataRedactionSettings"
    settings = DataRedactionSettings(mapping=body)
    mask = FieldMask(paths=[p.strip() for p in update_mask.split(",") if p.strip()])
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        result = client.update_data_redaction_settings(
            data_redaction_settings=settings, update_mask=mask,
        )
        output_json({"status": "updated", "data_redaction_settings": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
