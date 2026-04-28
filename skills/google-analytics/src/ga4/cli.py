"""CLI entrypoint — wires every subcommand group into the root `ga4` command."""

from __future__ import annotations

import click

from ga4 import __version__
from ga4.access_bindings import access_bindings
from ga4.accounts import accounts
from ga4.annotations import annotations
from ga4.audiences import audiences
from ga4.auth import auth
from ga4.config import config
from ga4.custom_dimensions import custom_dimensions
from ga4.custom_metrics import custom_metrics
from ga4.data import data
from ga4.data_streams import data_streams
from ga4.doctor import doctor
from ga4.key_events import key_events
from ga4.links import links
from ga4.measurement_secrets import measurement_secrets
from ga4.mp import mp
from ga4.properties import properties


@click.group()
@click.version_option(__version__, package_name="ga4")
def cli() -> None:
    """Google Analytics 4 CLI — Data API, Admin API, and Measurement Protocol."""


@click.group()
def admin() -> None:
    """Admin API — property, stream, event, and access configuration."""


admin.add_command(accounts)
admin.add_command(properties)
admin.add_command(data_streams, "data-streams")
admin.add_command(measurement_secrets, "measurement-secrets")
admin.add_command(key_events, "key-events")
admin.add_command(custom_dimensions, "custom-dimensions")
admin.add_command(custom_metrics, "custom-metrics")
admin.add_command(links)
admin.add_command(audiences)
admin.add_command(access_bindings, "access-bindings")
admin.add_command(annotations)


cli.add_command(auth)
cli.add_command(config)
cli.add_command(doctor)
cli.add_command(data)
cli.add_command(admin)
cli.add_command(mp)
