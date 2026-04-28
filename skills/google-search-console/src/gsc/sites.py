"""Site management commands."""

from __future__ import annotations

import click
from googleapiclient.errors import HttpError

from gsc.client import get_webmasters_service, handle_api_error, output_json


@click.group()
def sites():
    """Manage verified sites."""


@sites.command("list")
def sites_list():
    """List all verified sites."""
    service = get_webmasters_service()
    try:
        result = service.sites().list().execute()
    except HttpError as exc:
        handle_api_error(exc)
    output_json(result.get("siteEntry", []))


@sites.command("get")
@click.argument("site_url")
def sites_get(site_url: str):
    """Get details for a specific site."""
    service = get_webmasters_service()
    try:
        result = service.sites().get(siteUrl=site_url).execute()
    except HttpError as exc:
        handle_api_error(exc)
    output_json(result)


@sites.command("add")
@click.argument("site_url")
def sites_add(site_url: str):
    """Add a site to Search Console."""
    service = get_webmasters_service()
    try:
        service.sites().add(siteUrl=site_url).execute()
    except HttpError as exc:
        handle_api_error(exc)
    output_json({"status": "added", "site_url": site_url})
