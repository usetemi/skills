"""Delete files on Google Drive with manifest cleanup."""

from __future__ import annotations

from pathlib import Path

import click

from gdrive import rclone
from gdrive.manifest import Manifest
from gdrive.pull import _parse_remote_path


@click.command()
@click.argument("remote_path")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def rm(remote_path: str, force: bool):
    """Delete a file on Google Drive.

    REMOTE_PATH is in the format remote:path/to/file.
    Also removes any matching manifest entries.
    """
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    remote, path = _parse_remote_path(remote_path)

    if not force and not click.confirm(f"Delete {remote_path}?", default=False):
        click.echo("Aborted.")
        return

    try:
        rclone.delete_file(remote_path)
        click.echo(f"Deleted: {remote_path}")
    except rclone.RcloneError as exc:
        raise click.ClickException(
            f"Failed to delete: {exc.stderr}",
        ) from exc

    # Clean up manifest entries referencing this remote path
    manifest = Manifest()
    matches = manifest.find_by_remote(remote, path)
    for local_path_str, _entry in matches:
        manifest.remove(Path(local_path_str))
        click.echo(f"Untracked: {local_path_str}")
