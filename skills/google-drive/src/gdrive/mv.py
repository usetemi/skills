"""Move files on Google Drive with manifest tracking."""

from __future__ import annotations

import click

from gdrive import rclone
from gdrive.manifest import Manifest
from gdrive.pull import _parse_remote_path


@click.command()
@click.argument("source")
@click.argument("destination")
def mv(source: str, destination: str):
    """Move a file on Google Drive.

    Both SOURCE and DESTINATION should be remote:path format.
    Updates manifest entries that reference the moved path.
    """
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    src_remote, src_path = _parse_remote_path(source)
    dst_remote, dst_path = _parse_remote_path(destination)

    if src_remote != dst_remote:
        raise click.ClickException("Cannot move files between different remotes.")

    # Move on remote
    click.echo(f"Moving {source} -> {destination}...")
    try:
        rclone.moveto(source, destination)
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Move failed: {exc.stderr}") from exc

    # Update manifest entries
    manifest = Manifest()
    matches = manifest.find_by_remote(src_remote, src_path)
    for local_path_str, entry in matches:
        entry.remote_path = dst_path
        from pathlib import Path

        manifest.upsert(Path(local_path_str), entry)
        click.echo(f"Updated manifest for: {local_path_str}")

    click.echo("Move complete.")
