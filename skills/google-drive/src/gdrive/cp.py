"""Copy files on Google Drive."""

from __future__ import annotations

import click

from gdrive import rclone
from gdrive.pull import _parse_remote_path


@click.command()
@click.argument("source")
@click.argument("destination")
def cp(source: str, destination: str):
    """Copy a file on Google Drive.

    Both SOURCE and DESTINATION should be remote:path format.
    Works across different remotes (unlike mv).
    """
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    _parse_remote_path(source)
    _parse_remote_path(destination)

    click.echo(f"Copying {source} -> {destination}...")
    try:
        rclone.copyto(source, destination)
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Copy failed: {exc.stderr}") from exc

    click.echo("Copy complete.")
