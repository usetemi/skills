"""`ga4 admin properties` — property management (Admin API v1beta + v1alpha)."""

from __future__ import annotations

import click
from google.analytics.admin_v1beta import (
    DataRetentionSettings,
    ListPropertiesRequest,
    Property,
    SearchChangeHistoryEventsRequest,
)
from google.api_core import exceptions as gax

from ga4.accounts import run_access_report
from ga4.auth import SCOPE_EDIT, SCOPE_READONLY, SCOPE_USER_DELETION
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
from ga4.config import normalize_property, resolve_property


@click.group()
def properties() -> None:
    """Manage GA4 properties."""


# ---------- list / get / create / update / delete ----------

@properties.command("list")
@click.option("--filter", "filter_", default=None,
              help='API filter (e.g., "parent:accounts/123" or "ancestor:accounts/123").')
@click.option("--account", default=None,
              help="Shorthand: list all properties under account id (sets filter=parent:accounts/<id>).")
@click.option("--show-deleted", is_flag=True)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def properties_list(
    filter_: str | None,
    account: str | None,
    *,
    show_deleted: bool,
    max_results: int | None,
    page_size: int | None,
) -> None:
    """List properties (must provide --filter or --account)."""
    if account and not filter_:
        if not account.startswith("accounts/"):
            account = f"accounts/{account}"
        filter_ = f"parent:{account}"
    if not filter_:
        raise click.ClickException(
            "Provide --filter or --account. Example: --account 12345, "
            'or --filter "parent:accounts/12345".',
        )
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListPropertiesRequest(
            filter=filter_,
            show_deleted=show_deleted,
            page_size=page_size or 0,
        )
        output_json(collect_paged(client.list_properties(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@properties.command("get")
@click.option("--property", "-p", "property_flag", default=None)
def properties_get(property_flag: str | None) -> None:
    """Get a single property."""
    name = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        prop = client.get_property(name=name)
        output_json(proto_to_dict(prop))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@properties.command("create")
@click.option("--parent", required=True, help="Parent account (`accounts/12345` or `12345`).")
@click.option("--display-name", required=True)
@click.option("--time-zone", required=True, help="IANA timezone, e.g. America/Los_Angeles.")
@click.option("--currency-code", default=None, help="ISO 4217 currency code (default: USD).")
@click.option("--industry-category", default=None,
              help="Industry enum, e.g. AUTOMOTIVE, RETAIL. See API docs.")
@click.option("--property-type", default=None,
              help="Type enum: PROPERTY_TYPE_ORDINARY (default), PROPERTY_TYPE_SUBPROPERTY, _ROLLUP.")
def properties_create(
    parent: str,
    display_name: str,
    time_zone: str,
    currency_code: str | None,
    industry_category: str | None,
    property_type: str | None,
) -> None:
    """Create a new GA4 property."""
    if not parent.startswith("accounts/"):
        parent = f"accounts/{parent}"
    client = admin_client_beta([SCOPE_EDIT])
    prop = Property(
        parent=parent,
        display_name=display_name,
        time_zone=time_zone,
    )
    if currency_code is not None:
        prop.currency_code = currency_code
    if industry_category is not None:
        prop.industry_category = industry_category
    if property_type is not None:
        prop.property_type = property_type
    try:
        result = client.create_property(property=prop)
        output_json({"status": "created", "property": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@properties.command("update")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--display-name", default=None)
@click.option("--time-zone", default=None)
@click.option("--currency-code", default=None)
@click.option("--industry-category", default=None)
@click.option("--body-json", default=None,
              help="Full Property JSON (overrides individual flags). `@path` reads from file.")
@click.option("--update-mask", default=None,
              help="Comma-separated field paths. Auto-computed from flags if not given.")
def properties_update(
    property_flag: str | None,
    display_name: str | None,
    time_zone: str | None,
    currency_code: str | None,
    industry_category: str | None,
    body_json: str | None,
    update_mask: str | None,
) -> None:
    """Update property fields."""
    name = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])
    if body_json:
        body = load_json_arg(body_json)
        if not isinstance(body, dict):
            raise click.ClickException("--body-json must be a JSON object.")
        body["name"] = name
        prop = Property(mapping=body)
    else:
        prop = Property(name=name)
        if display_name is not None:
            prop.display_name = display_name
        if time_zone is not None:
            prop.time_zone = time_zone
        if currency_code is not None:
            prop.currency_code = currency_code
        if industry_category is not None:
            prop.industry_category = industry_category

    if update_mask:
        from google.protobuf.field_mask_pb2 import FieldMask
        mask = FieldMask(paths=[p.strip() for p in update_mask.split(",") if p.strip()])
    else:
        mask = build_update_mask(
            display_name=display_name,
            time_zone=time_zone,
            currency_code=currency_code,
            industry_category=industry_category,
        )
        if not mask.paths:
            raise click.ClickException(
                "No fields to update. Pass field flags or --update-mask.",
            )
    try:
        result = client.update_property(property=prop, update_mask=mask)
        output_json({"status": "updated", "property": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@properties.command("delete")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--yes", "-y", is_flag=True)
def properties_delete(property_flag: str | None, *, yes: bool) -> None:
    """Soft-delete a property (moves to trash; recoverable for 35 days)."""
    name = resolve_property(property_flag)
    require_yes(yes=yes, action="delete", target=f"property {name}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.delete_property(name=name)
        output_json({"status": "deleted", "property": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- acknowledgements ----------

@properties.command("acknowledge-user-data")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--acknowledgement", required=True,
              help="Required exact string; see API docs for the current wording.")
def properties_acknowledge_user_data(property_flag: str | None, acknowledgement: str) -> None:
    """Acknowledge the user data collection terms (required before creating Measurement Protocol secrets)."""
    name = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])
    try:
        response = client.acknowledge_user_data_collection(
            property=name, acknowledgement=acknowledgement,
        )
        output_json({"status": "acknowledged", "response": proto_to_dict(response)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- data retention ----------

@properties.command("get-data-retention")
@click.option("--property", "-p", "property_flag", default=None)
def properties_get_data_retention(property_flag: str | None) -> None:
    """Get data retention settings (event data + user data on new activity)."""
    name = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_READONLY])
    try:
        settings = client.get_data_retention_settings(name=f"{name}/dataRetentionSettings")
        output_json(proto_to_dict(settings))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@properties.command("update-data-retention")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--event-data-retention", default=None,
              help="TWO_MONTHS | FOURTEEN_MONTHS | TWENTY_SIX_MONTHS | THIRTY_EIGHT_MONTHS | FIFTY_MONTHS")
@click.option("--reset-user-data-on-new-activity", type=bool, default=None)
def properties_update_data_retention(
    property_flag: str | None,
    event_data_retention: str | None,
    reset_user_data_on_new_activity: bool | None,
) -> None:
    """Update data retention settings."""
    if event_data_retention is None and reset_user_data_on_new_activity is None:
        raise click.ClickException(
            "Provide at least one of --event-data-retention, --reset-user-data-on-new-activity.",
        )
    name = resolve_property(property_flag)
    client = admin_client_beta([SCOPE_EDIT])
    settings = DataRetentionSettings(name=f"{name}/dataRetentionSettings")
    if event_data_retention is not None:
        settings.event_data_retention = event_data_retention
    if reset_user_data_on_new_activity is not None:
        settings.reset_user_data_on_new_activity = reset_user_data_on_new_activity
    update_mask = build_update_mask(
        event_data_retention=event_data_retention,
        reset_user_data_on_new_activity=reset_user_data_on_new_activity,
    )
    try:
        result = client.update_data_retention_settings(
            data_retention_settings=settings, update_mask=update_mask,
        )
        output_json({"status": "updated", "data_retention_settings": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- attribution (v1alpha) ----------

@properties.command("get-attribution-settings")
@click.option("--property", "-p", "property_flag", default=None)
def properties_get_attribution_settings(property_flag: str | None) -> None:
    """Get attribution settings (reporting model, lookback windows). Alpha."""
    name = resolve_property(property_flag)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        settings = client.get_attribution_settings(name=f"{name}/attributionSettings")
        output_json(proto_to_dict(settings))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@properties.command("update-attribution-settings")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--body-json", required=True,
              help="Full AttributionSettings JSON. `@path` reads from file.")
@click.option("--update-mask", required=True,
              help="Comma-separated field paths (e.g., `reporting_attribution_model`).")
def properties_update_attribution_settings(
    property_flag: str | None, body_json: str, update_mask: str,
) -> None:
    """Update attribution settings. Alpha."""
    from google.analytics.admin_v1alpha import AttributionSettings
    from google.protobuf.field_mask_pb2 import FieldMask

    name = resolve_property(property_flag)
    body = load_json_arg(body_json)
    if not isinstance(body, dict):
        raise click.ClickException("--body-json must be a JSON object.")
    body["name"] = f"{name}/attributionSettings"
    settings = AttributionSettings(mapping=body)
    mask = FieldMask(paths=[p.strip() for p in update_mask.split(",") if p.strip()])
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        result = client.update_attribution_settings(
            attribution_settings=settings, update_mask=mask,
        )
        output_json({"status": "updated", "attribution_settings": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- signals settings (v1alpha) ----------

@properties.command("get-signals-settings")
@click.option("--property", "-p", "property_flag", default=None)
def properties_get_signals_settings(property_flag: str | None) -> None:
    """Get Google Signals settings. Alpha."""
    name = resolve_property(property_flag)
    client = admin_client_alpha([SCOPE_READONLY])
    try:
        settings = client.get_google_signals_settings(name=f"{name}/googleSignalsSettings")
        output_json(proto_to_dict(settings))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@properties.command("update-signals-settings")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--state", default=None,
              help="GOOGLE_SIGNALS_ENABLED | GOOGLE_SIGNALS_DISABLED")
@click.option("--consent", default=None,
              help="GOOGLE_SIGNALS_CONSENT_CONSENTED | GOOGLE_SIGNALS_CONSENT_NOT_CONSENTED")
@click.option("--body-json", default=None, help="Full settings JSON (overrides flags).")
@click.option("--update-mask", default=None, help="Comma-separated field paths.")
def properties_update_signals_settings(
    property_flag: str | None,
    state: str | None,
    consent: str | None,
    body_json: str | None,
    update_mask: str | None,
) -> None:
    """Update Google Signals settings. Alpha."""
    from google.analytics.admin_v1alpha import GoogleSignalsSettings
    from google.protobuf.field_mask_pb2 import FieldMask

    name = resolve_property(property_flag)
    if body_json:
        body = load_json_arg(body_json)
        if not isinstance(body, dict):
            raise click.ClickException("--body-json must be a JSON object.")
        body["name"] = f"{name}/googleSignalsSettings"
        settings = GoogleSignalsSettings(mapping=body)
    else:
        settings = GoogleSignalsSettings(name=f"{name}/googleSignalsSettings")
        if state is not None:
            settings.state = state
        if consent is not None:
            settings.consent = consent
    if update_mask:
        mask = FieldMask(paths=[p.strip() for p in update_mask.split(",") if p.strip()])
    else:
        mask = build_update_mask(state=state, consent=consent)
        if not mask.paths:
            raise click.ClickException(
                "No fields to update. Pass --state, --consent, or --update-mask with --body-json.",
            )
    client = admin_client_alpha([SCOPE_EDIT])
    try:
        result = client.update_google_signals_settings(
            google_signals_settings=settings, update_mask=mask,
        )
        output_json({"status": "updated", "google_signals_settings": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- access report + change history ----------

@properties.command("run-access-report")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--dimensions", "-d", multiple=True)
@click.option("--metrics", "-m", multiple=True)
@click.option("--start-date", "-s", default=None)
@click.option("--end-date", "-e", default=None)
@click.option("--limit", "-l", type=int, default=None)
@click.option("--offset", "-o", type=int, default=None)
@click.option("--include-all-users", is_flag=True)
@click.option("--expand-groups", is_flag=True)
@click.option("--request-json", default=None)
def properties_access_report(
    property_flag: str | None,
    dimensions: tuple[str, ...],
    metrics: tuple[str, ...],
    start_date: str | None,
    end_date: str | None,
    limit: int | None,
    offset: int | None,
    include_all_users: bool,
    expand_groups: bool,
    request_json: str | None,
) -> None:
    """Run an Access Report at the property level."""
    run_access_report(
        entity=resolve_property(property_flag),
        dimensions=dimensions,
        metrics=metrics,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        include_all_users=include_all_users,
        expand_groups=expand_groups,
        request_json=request_json,
    )


@properties.command("search-change-history")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--resource-type", multiple=True)
@click.option("--action", multiple=True)
@click.option("--actor-email", multiple=True)
@click.option("--earliest-change-time", default=None)
@click.option("--latest-change-time", default=None)
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def properties_search_change_history(
    property_flag: str | None,
    resource_type: tuple[str, ...],
    action: tuple[str, ...],
    actor_email: tuple[str, ...],
    earliest_change_time: str | None,
    latest_change_time: str | None,
    max_results: int | None,
    page_size: int | None,
) -> None:
    """Search change history events on a property's parent account, scoped to this property."""
    property_name = resolve_property(property_flag)
    # Parent account comes from a get_property() call.
    client = admin_client_beta([SCOPE_READONLY])
    try:
        prop = client.get_property(name=property_name)
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
        return
    account = prop.parent
    request = SearchChangeHistoryEventsRequest(
        account=account,
        property=property_name,
        resource_type=list(resource_type),
        action=list(action),
        actor_email=list(actor_email),
        page_size=page_size or 0,
    )
    if earliest_change_time:
        request.earliest_change_time.FromJsonString(earliest_change_time)
    if latest_change_time:
        request.latest_change_time.FromJsonString(latest_change_time)
    try:
        output_json(collect_paged(
            client.search_change_history_events(request=request), max_results,
        ))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- GDPR user deletion (v1alpha) ----------

@properties.command("submit-user-deletion")
@click.option("--property", "-p", "property_flag", default=None)
@click.option("--user-id", default=None, help="GA4 user_id to delete.")
@click.option("--client-id", default=None, help="Client id (cid) to delete.")
@click.option("--app-instance-id", default=None, help="Firebase app instance id to delete.")
@click.option("--user-provided-data", default=None,
              help="User-provided data (email, phone) to delete.")
@click.option("--yes", "-y", is_flag=True)
def properties_submit_user_deletion(
    property_flag: str | None,
    user_id: str | None,
    client_id: str | None,
    app_instance_id: str | None,
    user_provided_data: str | None,
    *,
    yes: bool,
) -> None:
    """Submit a GDPR user-deletion request. Alpha. Irreversible."""
    from google.analytics.admin_v1alpha import SubmitUserDeletionRequest

    provided = {
        "user_id": user_id,
        "client_id": client_id,
        "app_instance_id": app_instance_id,
        "user_provided_data": user_provided_data,
    }
    provided = {k: v for k, v in provided.items() if v is not None}
    if len(provided) != 1:
        raise click.ClickException(
            "Provide exactly one identifier among --user-id / --client-id / "
            "--app-instance-id / --user-provided-data.",
        )
    name = normalize_property(property_flag) if property_flag else resolve_property(None)
    require_yes(yes=yes, action="submit user deletion for", target=f"property {name}")
    client = admin_client_alpha([SCOPE_USER_DELETION])
    request = SubmitUserDeletionRequest(name=name, **provided)
    try:
        response = client.submit_user_deletion(request=request)
        output_json({"status": "submitted", "deletion_request_time": proto_to_dict(response)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
