"""List configured remotes or files on a remote."""

from __future__ import annotations

import click

from gdrive import rclone
from gdrive.auth import import_rclone_remotes, load_config


@click.command()
@click.argument("path", required=False)
@click.option("-l", "--long", is_flag=True, help="Show detailed listing")
@click.option("-R", "--recursive", is_flag=True, help="List recursively")
def ls(path: str | None, long: bool, recursive: bool):
    """List configured drives or files at remote:path.

    Without arguments, shows all configured remotes.
    With a remote:path argument, lists files at that location.
    """
    if path is None:
        _list_remotes()
    else:
        _list_files(path, long=long, recursive=recursive)


def _list_remotes() -> None:
    """List all configured gdrive remotes."""
    config = load_config()
    remotes = config.get("remotes", {})

    if not remotes:
        # Try importing any existing rclone drive remotes
        config = import_rclone_remotes()
        remotes = config.get("remotes", {})

    if not remotes:
        click.echo("No remotes configured. Run 'gdrive auth' first.")
        return

    click.echo("Configured remotes:\n")
    for name, info in remotes.items():
        drive_name = info.get("drive_name", "Unknown")
        drive_type = info.get("type", "unknown")
        click.echo(f"  {name}:  {drive_name}  ({drive_type})")

    click.echo("\nUse 'gdrive ls <remote>:' to list files.")


def _list_files(path: str, *, long: bool, recursive: bool) -> None:
    """List files at a remote path."""
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        if long:
            output = rclone.lsf(path, long=True, recursive=recursive)
        else:
            output = rclone.lsf(path, recursive=recursive)
        if output.strip():
            click.echo(output.rstrip())
        else:
            click.echo("(empty)")
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Failed to list: {exc.stderr}") from exc
