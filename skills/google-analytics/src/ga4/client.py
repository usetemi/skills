"""Client factories and shared utilities.

Wraps Google's generated clients:
  - BetaAnalyticsDataClient / AlphaAnalyticsDataClient (Data API)
  - AnalyticsAdminServiceClient (v1beta and v1alpha) (Admin API)

All CLI responses flow through `output_json()` so callers (agents, humans,
scripts) get a single consistent shape. Protobuf responses are converted via
`proto_to_dict()`. API errors are mapped to actionable `click.ClickException`s
by `handle_api_error()`.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import click
from google.analytics.admin_v1alpha import (
    AnalyticsAdminServiceClient as AdminClientAlpha,
)
from google.analytics.admin_v1beta import (
    AnalyticsAdminServiceClient as AdminClientBeta,
)
from google.analytics.data_v1alpha import AlphaAnalyticsDataClient
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.api_core import exceptions as gax
from google.protobuf.field_mask_pb2 import FieldMask
from google.protobuf.json_format import MessageToDict

from ga4.auth import SCOPE_READONLY, get_credentials

# ---------- client factories ----------

def data_client_beta(scopes: list[str] | None = None) -> BetaAnalyticsDataClient:
    """Data API v1beta — run-report, run-pivot-report, realtime, metadata, etc."""
    return BetaAnalyticsDataClient(credentials=get_credentials(scopes or [SCOPE_READONLY]))


def data_client_alpha(scopes: list[str] | None = None) -> AlphaAnalyticsDataClient:
    """Data API v1alpha — run-funnel-report, audience-lists, report-tasks."""
    return AlphaAnalyticsDataClient(credentials=get_credentials(scopes or [SCOPE_READONLY]))


def admin_client_beta(scopes: list[str] | None = None) -> AdminClientBeta:
    """Admin API v1beta — accounts, properties, streams, key-events, custom-*, etc."""
    return AdminClientBeta(credentials=get_credentials(scopes or [SCOPE_READONLY]))


def admin_client_alpha(scopes: list[str] | None = None) -> AdminClientAlpha:
    """Admin API v1alpha — audiences, access-bindings, annotations, etc."""
    return AdminClientAlpha(credentials=get_credentials(scopes or [SCOPE_READONLY]))


# ---------- proto conversion ----------

def proto_to_dict(message: Any) -> dict:
    """Convert a protobuf message (or proto-plus wrapper) to a plain dict.

    Preserves API field names (snake_case → snake_case). Handles both raw
    protobuf Message instances and proto-plus wrappers that expose `._pb`.
    """
    pb = message._pb if hasattr(message, "_pb") else message
    return MessageToDict(pb, preserving_proto_field_name=True)


def build_update_mask(**fields: Any) -> FieldMask:
    """Build a FieldMask from kwargs, including only keys whose values are not None.

    Example: build_update_mask(display_name="Foo", time_zone=None) → mask with ["display_name"].
    """
    paths = [key for key, value in fields.items() if value is not None]
    return FieldMask(paths=paths)


def collect_paged(pager: Any, max_results: int | None = None) -> list[dict]:
    """Walk a google-api pager, converting each item to a dict. Caps at max_results."""
    out: list[dict] = []
    for item in pager:
        out.append(proto_to_dict(item))
        if max_results is not None and len(out) >= max_results:
            break
    return out


# ---------- I/O helpers ----------

def output_json(data: Any) -> None:
    """Write JSON to stdout. Uses `default=str` so datetimes and protobuf timestamps serialize."""
    json.dump(data, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def load_json_arg(value: str | None) -> Any:
    """Load a JSON argument that may be inline JSON or `@path/to/file.json`.

    Used for filter expressions, funnel specs, request bodies — anything where
    building the full AST on the command line is impractical. Returns None for None.
    """
    if value is None:
        return None
    if value.startswith("@"):
        path = value[1:]
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except OSError as exc:
            raise click.ClickException(f"Cannot read {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON in {path}: {exc}") from exc
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON: {exc}") from exc


def split_csv(values: tuple[str, ...]) -> list[str]:
    """Split a tuple of possibly-comma-joined strings into a flat list.

    Lets users pass either `-d country -d city` or `-d country,city`.
    """
    out: list[str] = []
    for item in values:
        out.extend(s.strip() for s in item.split(",") if s.strip())
    return out


# ---------- error mapping ----------

def handle_api_error(exc: Exception) -> None:
    """Map google.api_core exceptions to actionable ClickExceptions. Always raises."""
    if isinstance(exc, gax.Unauthenticated):
        raise click.ClickException(
            "Authentication failed. Re-auth with:\n"
            "  ga4 auth login --client-secret <path-to-oauth-client.json>\n"
            f"Detail: {exc}",
        ) from exc
    if isinstance(exc, gax.PermissionDenied):
        raise click.ClickException(
            "Permission denied. The authenticated identity lacks GA access for this "
            "resource. Grant Viewer (read) or Editor (write) in GA Admin → Account "
            f"Access Management.\nDetail: {exc}",
        ) from exc
    if isinstance(exc, gax.ResourceExhausted):
        raise click.ClickException(
            "Quota exhausted. Data API tokens reset hourly/daily; pass "
            "--return-property-quota on a report to inspect current state.\n"
            f"Detail: {exc}",
        ) from exc
    if isinstance(exc, gax.InvalidArgument):
        raise click.ClickException(f"Invalid argument: {exc}") from exc
    if isinstance(exc, gax.NotFound):
        raise click.ClickException(f"Not found: {exc}") from exc
    if isinstance(exc, gax.FailedPrecondition):
        raise click.ClickException(f"Failed precondition: {exc}") from exc
    if isinstance(exc, gax.GoogleAPIError):
        raise click.ClickException(f"GA API error: {exc}") from exc
    raise exc


def require_yes(yes: bool, action: str, target: str) -> None:
    """Guard destructive operations behind --yes."""
    if not yes:
        raise click.ClickException(
            f"Refusing to {action} {target} without --yes / -y. "
            f"Re-run with --yes to proceed.",
        )
