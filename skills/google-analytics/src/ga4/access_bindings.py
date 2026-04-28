"""`ga4 admin access-bindings` — user access management (Admin API v1alpha).

Requires the `analytics.manage.users` scope, not `analytics.edit`.
"""

from __future__ import annotations

import click
from google.analytics.admin_v1alpha import (
    AccessBinding,
    BatchCreateAccessBindingsRequest,
    BatchDeleteAccessBindingsRequest,
    BatchGetAccessBindingsRequest,
    BatchUpdateAccessBindingsRequest,
    CreateAccessBindingRequest,
    DeleteAccessBindingRequest,
    ListAccessBindingsRequest,
    UpdateAccessBindingRequest,
)
from google.api_core import exceptions as gax

from ga4.auth import SCOPE_MANAGE_USERS
from ga4.client import (
    admin_client_alpha,
    collect_paged,
    handle_api_error,
    load_json_arg,
    output_json,
    proto_to_dict,
    require_yes,
)


def _resolve_parent(account: str | None, property_arg: str | None) -> str:
    """Return a `accounts/<id>` or `properties/<id>` parent, given one of the two."""
    if account and property_arg:
        raise click.ClickException("Pass exactly one of --account / --property.")
    if account:
        return account if account.startswith("accounts/") else f"accounts/{account}"
    if property_arg:
        return property_arg if property_arg.startswith("properties/") else f"properties/{property_arg}"
    raise click.ClickException("Pass --account <id> or --property <id>.")


def _binding_name(parent: str, binding_id: str) -> str:
    if binding_id.startswith(("accounts/", "properties/")):
        return binding_id
    return f"{parent}/accessBindings/{binding_id}"


@click.group()
def access_bindings() -> None:
    """Manage user access roles. Requires analytics.manage.users scope."""


@access_bindings.command("list")
@click.option("--account", default=None, help="Account id (or leave blank for --property).")
@click.option("--property", "property_arg", default=None, help="Property id.")
@click.option("--max-results", type=int, default=None)
@click.option("--page-size", type=int, default=None)
def access_bindings_list(
    account: str | None, property_arg: str | None,
    max_results: int | None, page_size: int | None,
) -> None:
    """List access bindings on an account or property."""
    parent = _resolve_parent(account, property_arg)
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    try:
        request = ListAccessBindingsRequest(parent=parent, page_size=page_size or 0)
        output_json(collect_paged(client.list_access_bindings(request=request), max_results))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@access_bindings.command("get")
@click.option("--account", default=None)
@click.option("--property", "property_arg", default=None)
@click.argument("binding_id")
def access_bindings_get(
    account: str | None, property_arg: str | None, binding_id: str,
) -> None:
    """Get a single access binding."""
    parent = _resolve_parent(account, property_arg)
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    try:
        binding = client.get_access_binding(name=_binding_name(parent, binding_id))
        output_json(proto_to_dict(binding))
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@access_bindings.command("create")
@click.option("--account", default=None)
@click.option("--property", "property_arg", default=None)
@click.option("--user", default=None,
              help="User email (mutually exclusive with --group).")
@click.option("--group", default=None,
              help="Group resource name (mutually exclusive with --user).")
@click.option("--roles", "-r", multiple=True, required=True,
              help="Role name (e.g., predefinedRoles/admin, predefinedRoles/no-cost-data). "
                   "Repeatable.")
def access_bindings_create(
    account: str | None, property_arg: str | None,
    user: str | None, group: str | None, roles: tuple[str, ...],
) -> None:
    """Create an access binding."""
    parent = _resolve_parent(account, property_arg)
    if not user and not group:
        raise click.ClickException("Provide --user <email> or --group <resource>.")
    if user and group:
        raise click.ClickException("Pass only one of --user / --group.")
    binding = AccessBinding(roles=list(roles))
    if user:
        binding.user = user
    elif group:
        binding.group = group
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    try:
        result = client.create_access_binding(
            request=CreateAccessBindingRequest(parent=parent, access_binding=binding),
        )
        output_json({"status": "created", "access_binding": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@access_bindings.command("update")
@click.option("--account", default=None)
@click.option("--property", "property_arg", default=None)
@click.argument("binding_id")
@click.option("--roles", "-r", multiple=True, required=True)
def access_bindings_update(
    account: str | None, property_arg: str | None,
    binding_id: str, roles: tuple[str, ...],
) -> None:
    """Update an access binding's roles."""
    parent = _resolve_parent(account, property_arg)
    name = _binding_name(parent, binding_id)
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    binding = AccessBinding(name=name, roles=list(roles))
    try:
        result = client.update_access_binding(
            request=UpdateAccessBindingRequest(access_binding=binding),
        )
        output_json({"status": "updated", "access_binding": proto_to_dict(result)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@access_bindings.command("delete")
@click.option("--account", default=None)
@click.option("--property", "property_arg", default=None)
@click.argument("binding_id")
@click.option("--yes", "-y", is_flag=True)
def access_bindings_delete(
    account: str | None, property_arg: str | None,
    binding_id: str, *, yes: bool,
) -> None:
    """Delete an access binding."""
    parent = _resolve_parent(account, property_arg)
    name = _binding_name(parent, binding_id)
    require_yes(yes=yes, action="delete", target=f"access binding {name}")
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    try:
        client.delete_access_binding(request=DeleteAccessBindingRequest(name=name))
        output_json({"status": "deleted", "access_binding": name})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


# ---------- batch ----------

@access_bindings.command("batch-create")
@click.option("--account", default=None)
@click.option("--property", "property_arg", default=None)
@click.option("--bindings-json", required=True,
              help="JSON array of {user|group, roles[]} entries. `@path` reads from file.")
def access_bindings_batch_create(
    account: str | None, property_arg: str | None, bindings_json: str,
) -> None:
    """Batch-create access bindings."""
    parent = _resolve_parent(account, property_arg)
    entries = load_json_arg(bindings_json)
    if not isinstance(entries, list):
        raise click.ClickException("--bindings-json must be a JSON array.")
    requests = [
        CreateAccessBindingRequest(parent=parent, access_binding=AccessBinding(mapping=e))
        for e in entries
    ]
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    try:
        result = client.batch_create_access_bindings(
            request=BatchCreateAccessBindingsRequest(parent=parent, requests=requests),
        )
        output_json({"status": "created", "count": len(result.access_bindings),
                     "access_bindings": [proto_to_dict(b) for b in result.access_bindings]})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@access_bindings.command("batch-get")
@click.option("--account", default=None)
@click.option("--property", "property_arg", default=None)
@click.option("--binding-id", "binding_ids", multiple=True, required=True,
              help="Binding id. Repeatable.")
def access_bindings_batch_get(
    account: str | None, property_arg: str | None, binding_ids: tuple[str, ...],
) -> None:
    """Batch-get access bindings."""
    parent = _resolve_parent(account, property_arg)
    names = [_binding_name(parent, b) for b in binding_ids]
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    try:
        result = client.batch_get_access_bindings(
            request=BatchGetAccessBindingsRequest(parent=parent, names=names),
        )
        output_json([proto_to_dict(b) for b in result.access_bindings])
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@access_bindings.command("batch-update")
@click.option("--account", default=None)
@click.option("--property", "property_arg", default=None)
@click.option("--bindings-json", required=True,
              help="JSON array of {name, roles[]} entries. `@path` reads from file.")
def access_bindings_batch_update(
    account: str | None, property_arg: str | None, bindings_json: str,
) -> None:
    """Batch-update access bindings."""
    parent = _resolve_parent(account, property_arg)
    entries = load_json_arg(bindings_json)
    if not isinstance(entries, list):
        raise click.ClickException("--bindings-json must be a JSON array.")
    requests = [
        UpdateAccessBindingRequest(access_binding=AccessBinding(mapping=e))
        for e in entries
    ]
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    try:
        result = client.batch_update_access_bindings(
            request=BatchUpdateAccessBindingsRequest(parent=parent, requests=requests),
        )
        output_json({"status": "updated", "count": len(result.access_bindings),
                     "access_bindings": [proto_to_dict(b) for b in result.access_bindings]})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)


@access_bindings.command("batch-delete")
@click.option("--account", default=None)
@click.option("--property", "property_arg", default=None)
@click.option("--binding-id", "binding_ids", multiple=True, required=True)
@click.option("--yes", "-y", is_flag=True)
def access_bindings_batch_delete(
    account: str | None, property_arg: str | None,
    binding_ids: tuple[str, ...], *, yes: bool,
) -> None:
    """Batch-delete access bindings."""
    parent = _resolve_parent(account, property_arg)
    require_yes(
        yes=yes, action="delete", target=f"{len(binding_ids)} access binding(s)",
    )
    requests = [
        DeleteAccessBindingRequest(name=_binding_name(parent, b)) for b in binding_ids
    ]
    client = admin_client_alpha([SCOPE_MANAGE_USERS])
    try:
        client.batch_delete_access_bindings(
            request=BatchDeleteAccessBindingsRequest(parent=parent, requests=requests),
        )
        output_json({"status": "deleted", "count": len(binding_ids)})
    except gax.GoogleAPIError as exc:
        handle_api_error(exc)
