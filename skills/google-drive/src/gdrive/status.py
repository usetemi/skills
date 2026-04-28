"""Compare local vs remote state for tracked files."""

from __future__ import annotations

from pathlib import Path

import click

from gdrive.manifest import Manifest, compute_md5


def _categorize_entries(
    entries: dict,
    filter_remote: str | None,
) -> tuple[list, list, list]:
    """Bucket tracked entries into (up_to_date, local_newer, missing_locally)."""
    up_to_date: list = []
    local_newer: list = []
    missing_locally: list = []
    for local_path_str, entry in entries.items():
        if filter_remote and entry.remote != filter_remote:
            continue
        local_path = Path(local_path_str)
        if not local_path.exists():
            missing_locally.append((local_path_str, entry))
            continue
        if compute_md5(local_path) == entry.local_md5:
            up_to_date.append((local_path_str, entry))
        else:
            local_newer.append((local_path_str, entry))
    return up_to_date, local_newer, missing_locally


def _print_missing_locally(manifest: Manifest, missing_locally: list) -> None:
    click.echo(f"\nMissing locally ({len(missing_locally)}):")
    for path, entry in missing_locally:
        remote_ref = f"{entry.remote}:{entry.remote_path}"
        click.echo(f"  ! {_short_path(path)}  (was {remote_ref})")
        matches = manifest.find_by_md5(entry.local_md5)
        other_matches = [(p, e) for p, e in matches if p != path and Path(p).exists()]
        if other_matches:
            click.echo(f"    Possibly moved to: {_short_path(other_matches[0][0])}")


@click.command()
@click.option("--remote", "-r", help="Filter by remote name")
def status(remote: str | None):
    """Show sync status of tracked files.

    Compares local files against their last-synced state and optionally
    checks the remote for changes.
    """
    manifest = Manifest()
    entries = manifest.all_entries()

    if not entries:
        click.echo("No tracked files. Use 'gdrive pull' to download and track files.")
        return

    up_to_date, local_newer, missing_locally = _categorize_entries(entries, remote)

    if up_to_date:
        click.echo(f"\nUp to date ({len(up_to_date)}):")
        for path, entry in up_to_date:
            remote_ref = f"{entry.remote}:{entry.remote_path}"
            click.echo(f"  {_short_path(path)}  <->  {remote_ref}")

    if local_newer:
        click.echo(f"\nLocal changes ({len(local_newer)}):")
        for path, entry in local_newer:
            remote_ref = f"{entry.remote}:{entry.remote_path}"
            click.echo(f"  M {_short_path(path)}  ->  {remote_ref}")

    if missing_locally:
        _print_missing_locally(manifest, missing_locally)

    if not (local_newer or missing_locally):
        if up_to_date:
            click.echo(f"\nAll {len(up_to_date)} tracked file(s) up to date.")
        click.echo("\nTo check remote changes, use 'gdrive pull' on individual files.")


def _short_path(path: str) -> str:
    """Shorten path relative to cwd if possible."""
    try:
        return str(Path(path).relative_to(Path.cwd()))
    except ValueError:
        return path
