"""CLI entrypoint -- registers all commands."""

from __future__ import annotations

import click

from gsc.analytics import query
from gsc.auth import auth
from gsc.config import config
from gsc.inspect_url import inspect_url
from gsc.pagespeed import pagespeed
from gsc.sitemaps import sitemaps
from gsc.sites import sites


@click.group()
@click.version_option(package_name="gsc")
def cli():
    """Google Search Console CLI -- query analytics, inspect URLs, manage sitemaps."""


cli.add_command(auth)
cli.add_command(config)
cli.add_command(query)
cli.add_command(inspect_url, "inspect")
cli.add_command(sites)
cli.add_command(sitemaps)
cli.add_command(pagespeed)
