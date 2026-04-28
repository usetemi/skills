"""URL Inspection command."""

from __future__ import annotations

import click
from googleapiclient.errors import HttpError

from gsc.client import get_searchconsole_service, handle_api_error, output_json


@click.command("inspect")
@click.argument("site_url")
@click.argument("url")
@click.option(
    "--language", default="en-US", help="Language code for results (default: en-US)."
)
def inspect_url(site_url: str, url: str, language: str):
    """Inspect a URL's index status, crawl info, and rich results."""
    body = {
        "inspectionUrl": url,
        "siteUrl": site_url,
        "languageCode": language,
    }

    service = get_searchconsole_service()
    try:
        result = service.urlInspection().index().inspect(body=body).execute()
    except HttpError as exc:
        handle_api_error(exc)
    output_json(result)
