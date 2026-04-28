"""Remove files from manifest without deleting them."""

from __future__ import annotations

from pathlib import Path

import click

from gdrive.manifest import Manifest


@click.command()
@click.argument("local_path", type=click.Path())
def untrack(local_path: str):
    """Remove a file from manifest tracking.

    The local file and remote file are left untouched.
    Only the manifest entry is removed.
    """
    path = Path(local_path).resolve()
    manifest = Manifest()
    entry = manifest.get(path)

    if entry is None:
        raise click.ClickException(f"Not tracked: {path}")

    remote_ref = f"{entry.remote}:{entry.remote_path}"
    manifest.remove(path)
    click.echo(f"Untracked: {path}")
    click.echo(f"  Was linked to: {remote_ref}")
