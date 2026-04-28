"""Sitemap management commands."""

from __future__ import annotations

import click
from googleapiclient.errors import HttpError

from gsc.client import get_webmasters_service, handle_api_error, output_json


@click.group()
def sitemaps():
    """Manage sitemaps."""


@sitemaps.command("list")
@click.argument("site_url")
@click.option("--sitemap-index", help="URL of sitemap index to list entries for.")
def sitemaps_list(site_url: str, sitemap_index: str | None):
    """List sitemaps for a site."""
    service = get_webmasters_service()
    try:
        if sitemap_index:
            result = (
                service.sitemaps()
                .list(siteUrl=site_url, sitemapIndex=sitemap_index)
                .execute()
            )
        else:
            result = service.sitemaps().list(siteUrl=site_url).execute()
    except HttpError as exc:
        handle_api_error(exc)
    output_json(result.get("sitemap", []))


@sitemaps.command("get")
@click.argument("site_url")
@click.argument("sitemap_url")
def sitemaps_get(site_url: str, sitemap_url: str):
    """Get details for a specific sitemap."""
    service = get_webmasters_service()
    try:
        result = (
            service.sitemaps().get(siteUrl=site_url, feedpath=sitemap_url).execute()
        )
    except HttpError as exc:
        handle_api_error(exc)
    output_json(result)


@sitemaps.command("submit")
@click.argument("site_url")
@click.argument("sitemap_url")
def sitemaps_submit(site_url: str, sitemap_url: str):
    """Submit a sitemap for a site."""
    service = get_webmasters_service()
    try:
        service.sitemaps().submit(siteUrl=site_url, feedpath=sitemap_url).execute()
    except HttpError as exc:
        handle_api_error(exc)
    output_json({"status": "submitted", "sitemap_url": sitemap_url})


@sitemaps.command("delete")
@click.argument("site_url")
@click.argument("sitemap_url")
def sitemaps_delete(site_url: str, sitemap_url: str):
    """Delete a sitemap from a site."""
    service = get_webmasters_service()
    try:
        service.sitemaps().delete(siteUrl=site_url, feedpath=sitemap_url).execute()
    except HttpError as exc:
        handle_api_error(exc)
    output_json({"status": "deleted", "sitemap_url": sitemap_url})
