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

MISSING_FILES_PREVIEW = 5


def _check_rclone_installed() -> None:
    """Verify rclone is on PATH or exit."""
    try:
        rclone_path = rclone.check_installed()
        _pass(f"rclone installed ({rclone_path})")
    except rclone.RcloneError:
        _fail("rclone not installed")
        click.echo("  Install: apt install rclone  or  brew install rclone")
        sys.exit(1)


def _check_configured_remotes(remotes: dict) -> bool:
    """Verify each registered remote exists in rclone and authenticates. Returns ok status."""
    if not remotes:
        _warn("no remotes configured")
        return True
    try:
        rclone_config = rclone.config_dump()
    except rclone.RcloneError:
        rclone_config = {}

    ok = True
    for name, info in remotes.items():
        drive_name = info.get("drive_name", "")
        if name not in rclone_config:
            _fail(f"{name}: not in rclone config")
            ok = False
            continue
        if _validate_remote(name):
            _pass(f"{name}: authenticated ({drive_name})")
        else:
            _fail(f"{name}: authentication failed ({drive_name})")
            click.echo("  Run 'gdrive auth' to re-authenticate")
            ok = False
    return ok


def _check_orphaned_remotes(remotes: dict) -> None:
    """Warn about rclone drive remotes that gdrive doesn't know about."""
    try:
        rclone_config = rclone.config_dump()
    except rclone.RcloneError:
        rclone_config = {}

    orphaned = [
        name
        for name, settings in rclone_config.items()
        if settings.get("type") == "drive" and name not in remotes
    ]
    if not orphaned:
        return
    _warn(f"{len(orphaned)} rclone drive remote(s) not in gdrive config")
    for name in orphaned:
        click.echo(f"    {name}")
    if click.confirm("  Import them into gdrive config?", default=True):
        import_rclone_remotes()
        click.echo("  Imported.")


def _check_manifest_health() -> None:
    """Report on missing-but-tracked files."""
    manifest = Manifest()
    entries = manifest.all_entries()
    if not entries:
        click.echo("  No tracked files in manifest.")
        return
    missing = [p for p in entries if not Path(p).exists()]
    if not missing:
        _pass(f"{len(entries)} tracked file(s) all present")
        return
    _warn(f"{len(missing)} tracked file(s) missing locally")
    for path in missing[:MISSING_FILES_PREVIEW]:
        click.echo(f"    {path}")
    if len(missing) > MISSING_FILES_PREVIEW:
        click.echo(f"    ... and {len(missing) - MISSING_FILES_PREVIEW} more")
    click.echo("  Run 'gdrive untrack <path>' to clean up")


@click.command()
def doctor():
    """Check gdrive setup and diagnose problems."""
    _check_rclone_installed()

    if CONFIG_PATH.exists():
        _pass(f"config exists ({CONFIG_PATH})")
    else:
        _warn("no config file (will be created on first 'gdrive auth')")

    config = load_config()
    remotes = config.get("remotes", {})
    ok = _check_configured_remotes(remotes)
    _check_orphaned_remotes(remotes)
    _check_manifest_health()

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
