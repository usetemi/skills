"""PageSpeed Insights command."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

import click

from gsc.config import get_config_value

VALID_CATEGORIES = {"performance", "accessibility", "best-practices", "seo"}
VALID_STRATEGIES = {"mobile", "desktop"}
API_URL = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"


@click.command()
@click.argument("url")
@click.option(
    "--category",
    multiple=True,
    type=click.Choice(sorted(VALID_CATEGORIES)),
    default=["performance"],
    help="Audit category (can specify multiple, default: performance).",
)
@click.option(
    "--strategy",
    type=click.Choice(sorted(VALID_STRATEGIES)),
    default="mobile",
    help="Test strategy (default: mobile).",
)
@click.option("--locale", help="Locale for results (e.g. en, fr).")
def pagespeed(url: str, category: tuple[str, ...], strategy: str, locale: str | None):
    """Run PageSpeed Insights audit on a URL."""
    api_key = get_config_value("pagespeed-api-key")
    if not api_key:
        raise click.ClickException(
            "PageSpeed API key not configured.\n"
            "1. Create an API key at https://console.cloud.google.com/apis/credentials\n"
            "2. Enable 'PageSpeed Insights API' in your GCP project\n"
            "3. Run: gsc config set pagespeed-api-key <your-key>"
        )

    query_parts = [
        f"url={urllib.parse.quote(url, safe='')}",
        f"key={urllib.parse.quote(api_key, safe='')}",
        f"strategy={strategy}",
    ]
    for cat in category:
        query_parts.append(f"category={urllib.parse.quote(cat, safe='')}")
    if locale:
        query_parts.append(f"locale={urllib.parse.quote(locale, safe='')}")

    request_url = f"{API_URL}?{'&'.join(query_parts)}"

    req = urllib.request.Request(request_url)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode()
        try:
            detail = json.loads(error_body).get("error", {}).get("message", error_body)
        except (json.JSONDecodeError, AttributeError):
            detail = error_body
        raise click.ClickException(f"PageSpeed API error: {detail}") from exc
    except urllib.error.URLError as exc:
        raise click.ClickException(f"Network error: {exc.reason}") from exc

    click.echo(json.dumps(data, indent=2, default=str))
