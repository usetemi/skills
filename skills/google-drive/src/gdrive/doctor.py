"""Health check for gdrive setup."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from gdrive import rclone
from gdrive.auth import (
    CONFIG_PATH,
    _validate_remote,
    import_rclone_remotes,
    load_config,
)
from gdrive.manifest import Manifest


@click.command()
def doctor():
    """Check gdrive setup and diagnose problems."""
    ok = True

    # 1. rclone installed
    try:
        rclone_path = rclone.check_installed()
        _pass(f"rclone installed ({rclone_path})")
    except rclone.RcloneError:
        _fail("rclone not installed")
        click.echo("  Install: apt install rclone  or  brew install rclone")
        sys.exit(1)

    # 2. Config file
    if CONFIG_PATH.exists():
        _pass(f"config exists ({CONFIG_PATH})")
    else:
        _warn("no config file (will be created on first 'gdrive auth')")

    # 3. Check each configured remote
    config = load_config()
    remotes = config.get("remotes", {})

    if not remotes:
        _warn("no remotes configured")
    else:
        try:
            rclone_config = rclone.config_dump()
        except rclone.RcloneError:
            rclone_config = {}

        for name, info in remotes.items():
            drive_name = info.get("drive_name", "")

            # Exists in rclone?
            if name not in rclone_config:
                _fail(f"{name}: not in rclone config")
                ok = False
                continue

            # Token works?
            if _validate_remote(name):
                _pass(f"{name}: authenticated ({drive_name})")
            else:
                _fail(f"{name}: authentication failed ({drive_name})")
                click.echo("  Run 'gdrive auth' to re-authenticate")
                ok = False

    # 4. Orphaned rclone drive remotes
    try:
        rclone_config = rclone.config_dump()
    except rclone.RcloneError:
        rclone_config = {}

    orphaned = [
        name
        for name, settings in rclone_config.items()
        if settings.get("type") == "drive" and name not in remotes
    ]
    if orphaned:
        _warn(f"{len(orphaned)} rclone drive remote(s) not in gdrive config")
        for name in orphaned:
            click.echo(f"    {name}")
        if click.confirm("  Import them into gdrive config?", default=True):
            import_rclone_remotes()
            click.echo("  Imported.")

    # 5. Manifest health
    manifest = Manifest()
    entries = manifest.all_entries()
    if entries:
        missing = [p for p in entries if not Path(p).exists()]
        if missing:
            _warn(f"{len(missing)} tracked file(s) missing locally")
            for path in missing[:5]:
                click.echo(f"    {path}")
            if len(missing) > 5:
                click.echo(f"    ... and {len(missing) - 5} more")
            click.echo("  Run 'gdrive untrack <path>' to clean up")
        else:
            _pass(f"{len(entries)} tracked file(s) all present")
    else:
        click.echo("  No tracked files in manifest.")

    # Summary
    click.echo()
    if ok:
        click.echo("All checks passed.")
    else:
        click.echo("Some checks failed. See above for details.")
        sys.exit(1)


def _pass(msg: str) -> None:
    click.echo(f"  OK  {msg}")


def _fail(msg: str) -> None:
    click.echo(f"  FAIL  {msg}")


def _warn(msg: str) -> None:
    click.echo(f"  WARN  {msg}")
