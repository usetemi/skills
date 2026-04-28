"""Create directories on Google Drive."""

from __future__ import annotations

import click

from gdrive import rclone


@click.command()
@click.argument("remote_path")
def mkdir(remote_path: str):
    """Create a directory on Google Drive.

    REMOTE_PATH is in the format remote:path/to/directory.
    """
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    if ":" not in remote_path:
        raise click.ClickException(
            f"Invalid remote path: {remote_path}. Expected format: remote:path/to/dir"
        )

    try:
        rclone.mkdir(remote_path)
        click.echo(f"Created: {remote_path}")
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Failed to create directory: {exc.stderr}") from exc
