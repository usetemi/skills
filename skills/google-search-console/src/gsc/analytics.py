"""Search Analytics query command."""

from __future__ import annotations

import click
from googleapiclient.errors import HttpError

from gsc.client import get_webmasters_service, handle_api_error, output_json

VALID_DIMENSIONS = {"query", "page", "country", "device", "searchAppearance", "date"}
VALID_SEARCH_TYPES = {"web", "image", "video", "news", "discover", "googleNews"}
VALID_AGGREGATION_TYPES = {"auto", "byPage", "byProperty"}
VALID_DATA_STATES = {"all", "final"}


def _build_filters(
    query_filter, page_filter, country_filter, device_filter
) -> list[dict] | None:
    """Build dimensionFilterGroups from individual filter options."""
    filters = []
    for dimension, expression in [
        ("query", query_filter),
        ("page", page_filter),
        ("country", country_filter),
        ("device", device_filter),
    ]:
        if expression:
            # Support operator prefix: ~contains, =equals (default contains)
            if expression.startswith("="):
                filters.append(
                    {
                        "dimension": dimension,
                        "operator": "equals",
                        "expression": expression[1:],
                    }
                )
            elif expression.startswith("!"):
                filters.append(
                    {
                        "dimension": dimension,
                        "operator": "notContains",
                        "expression": expression[1:],
                    }
                )
            else:
                # Strip optional ~ prefix for contains
                expr = expression.lstrip("~")
                filters.append(
                    {
                        "dimension": dimension,
                        "operator": "contains",
                        "expression": expr,
                    }
                )
    if not filters:
        return None
    return [{"filters": filters}]


@click.command()
@click.argument("site_url")
@click.option("-s", "--start-date", required=True, help="Start date (YYYY-MM-DD).")
@click.option("-e", "--end-date", required=True, help="End date (YYYY-MM-DD).")
@click.option(
    "-d",
    "--dimensions",
    multiple=True,
    type=click.Choice(sorted(VALID_DIMENSIONS)),
    help="Dimensions to group by (can specify multiple).",
)
@click.option(
    "--query-filter",
    help="Filter by query (= exact, ! not-contains, default contains).",
)
@click.option("--page-filter", help="Filter by page URL.")
@click.option("--country-filter", help="Filter by country (3-letter code).")
@click.option("--device-filter", help="Filter by device (DESKTOP, MOBILE, TABLET).")
@click.option(
    "--search-type",
    type=click.Choice(sorted(VALID_SEARCH_TYPES)),
    default="web",
    help="Search type (default: web).",
)
@click.option(
    "--row-limit", type=int, default=1000, help="Max rows (default 1000, max 25000)."
)
@click.option("--start-row", type=int, default=0, help="Row offset for pagination.")
@click.option(
    "--aggregation-type",
    type=click.Choice(sorted(VALID_AGGREGATION_TYPES)),
    help="Aggregation type.",
)
@click.option(
    "--data-state",
    type=click.Choice(sorted(VALID_DATA_STATES)),
    help="Data freshness (all includes fresh data).",
)
def query(
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: tuple[str, ...],
    query_filter: str | None,
    page_filter: str | None,
    country_filter: str | None,
    device_filter: str | None,
    search_type: str,
    row_limit: int,
    start_row: int,
    aggregation_type: str | None,
    data_state: str | None,
):
    """Query Search Analytics data for a site."""
    row_limit = min(row_limit, 25000)

    body: dict = {
        "startDate": start_date,
        "endDate": end_date,
        "type": search_type,
        "rowLimit": row_limit,
        "startRow": start_row,
    }

    if dimensions:
        body["dimensions"] = list(dimensions)

    filter_groups = _build_filters(
        query_filter, page_filter, country_filter, device_filter
    )
    if filter_groups:
        body["dimensionFilterGroups"] = filter_groups

    if aggregation_type:
        body["aggregationType"] = aggregation_type

    if data_state:
        body["dataState"] = data_state

    service = get_webmasters_service()
    try:
        result = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    except HttpError as exc:
        handle_api_error(exc)
    output_json(result)
