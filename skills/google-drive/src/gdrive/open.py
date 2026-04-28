"""Get the Google Drive web URL for a file."""

from __future__ import annotations

import click

from gdrive import rclone
from gdrive.pull import _get_remote_metadata


@click.command(name="open")
@click.argument("remote_path")
def open_cmd(remote_path: str):
    """Print the Google Drive web URL for a file.

    REMOTE_PATH is in the format remote:path/to/file.
    """
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        metadata = _get_remote_metadata(remote_path)
    except rclone.RcloneError as exc:
        raise click.ClickException(
            f"Failed to get metadata: {exc.stderr}",
        ) from exc

    file_id = metadata.get("ID", "")
    if not file_id:
        raise click.ClickException("Could not determine file ID.")

    url = f"https://drive.google.com/file/d/{file_id}/view"
    click.echo(url)
