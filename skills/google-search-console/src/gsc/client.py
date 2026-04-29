"""Service builders and shared utilities."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import click
from googleapiclient.discovery import build

from gsc.auth import get_credentials
from gsc.common import output_json  # noqa: F401  (re-exported; callers import it from here)

if TYPE_CHECKING:
    from googleapiclient.errors import HttpError


def get_webmasters_service():
    """Build the webmasters v3 service (analytics, sites, sitemaps)."""
    return build("webmasters", "v3", credentials=get_credentials())


def get_searchconsole_service():
    """Build the searchconsole v1 service (URL inspection)."""
    return build("searchconsole", "v1", credentials=get_credentials())


def handle_api_error(exc: HttpError) -> None:
    """Map HttpError to actionable ClickException."""
    status = exc.resp.status
    try:
        detail = json.loads(exc.content).get("error", {}).get("message", str(exc))
    except (json.JSONDecodeError, AttributeError):
        detail = str(exc)

    messages = {
        401: (
            "Authentication expired. Run: gsc auth login"
            f" --client-secret <path>\nDetail: {detail}"
        ),
        403: (
            "Permission denied. Verify site ownership in"
            f" Search Console.\nDetail: {detail}"
        ),
        429: (f"Rate limit exceeded. Wait a moment and retry.\nDetail: {detail}"),
    }
    raise click.ClickException(messages.get(status, f"API error ({status}): {detail}"))
