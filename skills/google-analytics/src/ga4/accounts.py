"""`ga4 admin accounts` — account management (Admin API v1beta)."""

from __future__ import annotations

import click
from google.analytics.admin_v1beta import (
    AccessDateRange,
    AccessDimension,
    AccessMetric,
    Account,
    ListAccountsRequest,
    ListAccountSummariesRequest,
    ProvisionAccountTicketRequest,
    RunAccessReportRequest,
    SearchChangeHistoryEventsRequest,
)
from google.api_core import exceptions as gax

from ga4.auth import SCOPE_EDIT, SCOPE_READONLY
from ga4.client import (
    admin_client_beta,
    build_update_mask,
    collect_paged,
    handle_api_error,
    load_json_arg,
    output_json,
    proto_to_dict,
    require_yes,
)


def _account_name(account_id: str) -> str:
    """Normalize an account id to `accounts/<id>` resource-name form."""
    if account_id.startswith("accounts/"):
        return account_id
    return f"accounts/{account_id}"


@click.group()
def accounts() -> None:
    """Manage GA4 accounts."""


@accounts.command("list")
@click.option("--show-deleted", is_flag=True, help="Include soft-deleted accounts.")
@click.option("--max-results", type=int, default=None, help="Cap on rows returned.")
@click.option("--page-size", type=int, default=None, help="API page size hint.")
def accounts_list(*, show_deleted: bool, max_results: int | None, page_size: int | None) -> None:
    """List accounts visible to the caller."""
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListAccountsRequest(
            show_deleted=show_deleted,
            page_size=page_size or 0,
        )
        output_json(collect_paged(client.list_accounts(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@accounts.command("get")
@click.argument("account_id")
def accounts_get(account_id: str) -> None:
    """Get a single account by id."""
    client = admin_client_beta([SCOPE_READONLY])
    try:
        acct = client.get_account(name=_account_name(account_id))
        output_json(proto_to_dict(acct))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@accounts.command("update")
@click.argument("account_id")
@click.option("--display-name", default=None)
@click.option("--region-code", default=None)
def accounts_update(account_id: str, display_name: str | None, region_code: str | None) -> None:
    """Update account fields (display-name, region-code)."""
    if display_name is None and region_code is None:
        raise click.ClickException("At least one of --display-name / --region-code is required.")
    client = admin_client_beta([SCOPE_EDIT])
    account = Account(name=_account_name(account_id))
    if display_name is not None:
        account.display_name = display_name
    if region_code is not None:
        account.region_code = region_code
    update_mask = build_update_mask(display_name=display_name, region_code=region_code)
    try:
        result = client.update_account(account=account, update_mask=update_mask)
        output_json({"status": "updated", "account": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@accounts.command("delete")
@click.argument("account_id")
@click.option("--yes", "-y", is_flag=True, help="Confirm destructive action.")
def accounts_delete(account_id: str, *, yes: bool) -> None:
    """Soft-delete an account (moves it to the trash)."""
    require_yes(yes=yes, action="delete", target=f"account {account_id}")
    client = admin_client_beta([SCOPE_EDIT])
    try:
        client.delete_account(name=_account_name(account_id))
        output_json({"status": "deleted", "account": _account_name(account_id)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@accounts.command("summaries-list")
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def accounts_summaries_list(max_results: int | None, page_size: int | None) -> None:
    """List account summaries — accounts with their nested properties, in one hop."""
    client = admin_client_beta([SCOPE_READONLY])
    try:
        request = ListAccountSummariesRequest(page_size=page_size or 0)
        output_json(collect_paged(client.list_account_summaries(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@accounts.command("get-data-sharing-settings")
@click.argument("account_id")
def accounts_get_data_sharing(account_id: str) -> None:
    """Get account data sharing settings."""
    client = admin_client_beta([SCOPE_READONLY])
    try:
        settings = client.get_data_sharing_settings(
            name=f"{_account_name(account_id)}/dataSharingSettings",
        )
        output_json(proto_to_dict(settings))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@accounts.command("search-change-history")
@click.argument("account_id")
@click.option("--property", "property_filter", default=None,
              help="Optional property filter (`properties/123`). Limits to changes on that property.")
@click.option("--resource-type", multiple=True,
              help="Filter by resource type (e.g., PROPERTY, DATA_STREAM). Repeatable.")
@click.option("--action", multiple=True,
              help="Filter by action (CREATED, UPDATED, DELETED). Repeatable.")
@click.option("--actor-email", multiple=True, help="Filter by actor email. Repeatable.")
@click.option("--earliest-change-time", default=None, help="RFC 3339 timestamp.")
@click.option("--latest-change-time", default=None, help="RFC 3339 timestamp.")
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def accounts_search_change_history(
    account_id: str,
    property_filter: str | None,
    resource_type: tuple[str, ...],
    action: tuple[str, ...],
    actor_email: tuple[str, ...],
    earliest_change_time: str | None,
    latest_change_time: str | None,
    max_results: int | None,
    page_size: int | None,
) -> None:
    """Search change history events for an account."""
    client = admin_client_beta([SCOPE_READONLY])
    request = SearchChangeHistoryEventsRequest(
        account=_account_name(account_id),
        property=property_filter or "",
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


@accounts.command("run-access-report")
@click.argument("account_id")
@click.option("--dimensions", "-d", multiple=True, help="Access dimension (userEmail, epochTimeMicros, etc).")
@click.option("--metrics", "-m", multiple=True, help="Access metric (accessCount).")
@click.option("--start-date", "-s", default=None)
@click.option("--end-date", "-e", default=None)
@click.option("--limit", "-l", type=int, default=None)
@click.option("--offset", "-o", type=int, default=None)
@click.option("--include-all-users", is_flag=True)
@click.option("--expand-groups", is_flag=True)
@click.option("--request-json", default=None, help="Full RunAccessReportRequest JSON (overrides flags).")
def accounts_access_report(
    account_id: str,
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
    """Run an Access Report (who accessed what, when) at the account level."""
    run_access_report(
        entity=_account_name(account_id),
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


def run_access_report(
    *,
    entity: str,
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
    """Shared helper — both `accounts` and `properties` support run-access-report."""
    client = admin_client_beta([SCOPE_READONLY])
    if request_json:
        body = load_json_arg(request_json)
        if not isinstance(body, dict):
            raise click.ClickException("--request-json must be a JSON object.")
        body["entity"] = entity
        request = RunAccessReportRequest(mapping=body)
    else:
        request = RunAccessReportRequest(
            entity=entity,
            dimensions=[AccessDimension(dimension_name=d) for d in dimensions],
            metrics=[AccessMetric(metric_name=m) for m in metrics],
            limit=limit or 0,
            offset=offset or 0,
            include_all_users=include_all_users,
            expand_groups=expand_groups,
        )
        if start_date or end_date:
            request.date_ranges = [
                AccessDateRange(start_date=start_date or "", end_date=end_date or ""),
            ]
    try:
        response = client.run_access_report(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@accounts.command("provision-ticket")
@click.option("--display-name", required=True, help="Display name for the new account.")
@click.option("--redirect-uri", required=True, help="URI to redirect to after ToS acceptance.")
@click.option("--region-code", default=None, help="ISO 3166-1 alpha-2 region code.")
def accounts_provision_ticket(display_name: str, redirect_uri: str, region_code: str | None) -> None:
    """Create an account ticket — the first step in account provisioning.

    Returns an account ticket id. Direct the user to
    `https://analytics.google.com/analytics/web/?provisioningSignup=false#<ticketId>`
    to complete the ToS acceptance flow.
    """
    client = admin_client_beta([SCOPE_EDIT])
    account = Account(display_name=display_name)
    if region_code is not None:
        account.region_code = region_code
    request = ProvisionAccountTicketRequest(account=account, redirect_uri=redirect_uri)
    try:
        response = client.provision_account_ticket(request=request)
        output_json(proto_to_dict(response))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
