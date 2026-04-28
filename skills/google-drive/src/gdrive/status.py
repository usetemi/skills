"""Compare local vs remote state for tracked files."""

from __future__ import annotations

from pathlib import Path

import click

from gdrive.manifest import Manifest, compute_md5


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

    # Categorize entries
    up_to_date = []
    local_newer = []
    missing_locally = []

    for local_path_str, entry in entries.items():
        if remote and entry.remote != remote:
            continue

        local_path = Path(local_path_str)

        if not local_path.exists():
            # Check if file was moved (search by MD5 in common locations)
            missing_locally.append((local_path_str, entry))
            continue

        # Compare local MD5 with what we had at sync time
        current_md5 = compute_md5(local_path)
        if current_md5 == entry.local_md5:
            up_to_date.append((local_path_str, entry))
        else:
            local_newer.append((local_path_str, entry))

    # Display results
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
        click.echo(f"\nMissing locally ({len(missing_locally)}):")
        for path, entry in missing_locally:
            remote_ref = f"{entry.remote}:{entry.remote_path}"
            click.echo(f"  ! {_short_path(path)}  (was {remote_ref})")
            # Try to find by MD5
            matches = manifest.find_by_md5(entry.local_md5)
            other_matches = [
                (p, e) for p, e in matches if p != path and Path(p).exists()
            ]
            if other_matches:
                click.echo(f"    Possibly moved to: {_short_path(other_matches[0][0])}")

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
