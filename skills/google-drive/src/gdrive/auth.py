"""Auth setup: configure rclone remotes for Google Drive shared drives."""

from __future__ import annotations

import json
import os

import click

from gdrive import rclone
from gdrive.manifest import CONFIG_DIR

CONFIG_PATH = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load gdrive config."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"remotes": {}}


def save_config(config: dict) -> None:
    """Save gdrive config."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def _validate_remote(name: str) -> bool:
    """Check if a remote has a working token."""
    try:
        rclone.about(name)
        return True
    except rclone.RcloneError:
        return False


def _find_all_drive_remotes() -> list[str]:
    """Find all rclone remotes of type 'drive' (no team_drive)."""
    try:
        config = rclone.config_dump()
    except rclone.RcloneError:
        return []
    return [
        name
        for name, settings in config.items()
        if settings.get("type") == "drive" and not settings.get("team_drive")
    ]


def _is_headless() -> bool:
    """Detect if running on a headless machine (no display/browser)."""
    return not os.environ.get("DISPLAY") and not os.environ.get("BROWSER")


def _get_token(remote_name: str) -> str | None:
    """Extract the token JSON string from an existing remote's config."""
    try:
        config = rclone.config_dump()
    except rclone.RcloneError:
        return None
    remote_config = config.get(remote_name, {})
    token = remote_config.get("token")
    if token:
        return token if isinstance(token, str) else json.dumps(token)
    return None


def import_rclone_remotes() -> dict:
    """Scan rclone config for drive remotes not in config.json.

    Imports any found remotes into config.json and returns the config.
    """
    config = load_config()
    try:
        rclone_config = rclone.config_dump()
    except rclone.RcloneError:
        return config

    changed = False
    for name, settings in rclone_config.items():
        if settings.get("type") != "drive":
            continue
        if name in config.get("remotes", {}):
            continue

        team_drive = settings.get("team_drive", "")
        if team_drive:
            config.setdefault("remotes", {})[name] = {
                "drive_name": name,
                "drive_id": team_drive,
                "type": "shared",
            }
        else:
            config.setdefault("remotes", {})[name] = {
                "drive_name": "My Drive",
                "drive_id": "",
                "type": "personal",
            }
        changed = True

    if changed:
        save_config(config)
    return config


@click.command()
@click.option(
    "--personal-only",
    is_flag=True,
    help="Only set up personal My Drive, skip shared drives.",
)
def auth(personal_only: bool):
    """Set up Google Drive remotes for shared drives."""
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo("Setting up Google Drive access via rclone.\n")

    # Step 1: Find existing base remotes, validate, clean up broken ones
    base_remote = None
    existing = _find_all_drive_remotes()

    for name in existing:
        click.echo(f"Found drive remote: {name} ... ", nl=False)
        if _validate_remote(name):
            click.echo("OK")
            use_it = click.confirm(
                f"Use '{name}' as the base remote?",
                default=True,
            )
            if use_it:
                base_remote = name
                break
        else:
            click.echo("broken (invalid token)")
            if click.confirm(f"Delete broken remote '{name}'?", default=True):
                try:
                    rclone.config_delete(name)
                    click.echo(f"  Deleted {name}")
                except rclone.RcloneError as exc:
                    click.echo(f"  Failed to delete: {exc.stderr}")

    # Step 2: Create a new base remote if needed
    if not base_remote:
        click.echo("\nCreating a new base drive remote.")

        if _is_headless():
            click.echo(
                "\nHeadless environment detected. Before proceeding:\n"
                "  Set up an SSH tunnel from a machine with a browser:\n"
                "  ssh -L 53682:localhost:53682 <this-host>\n"
            )

        base_remote = click.prompt(
            "Name for the base remote",
            default="gdrive",
        )

        # Create config entry non-interactively (no OAuth yet)
        click.echo(f"\nCreating remote '{base_remote}'...")
        try:
            rclone.config_create(base_remote, "drive", scope="drive")
        except rclone.RcloneError as exc:
            raise click.ClickException(
                f"Failed to create remote: {exc.stderr}",
            ) from exc

        # Now do OAuth separately via interactive reconnect
        click.echo(
            "\nStarting OAuth. A browser window should open.\n"
            "Complete the Google sign-in, then answer 'n' to\n"
            "'Configure this as a Shared Drive?' (we handle that separately).\n"
        )
        exit_code = rclone.config_reconnect_interactive(base_remote)
        if exit_code != 0:
            click.echo(
                "\nrclone reconnect exited with an error, but the token "
                "may have been saved. Checking..."
            )

        # Verify the remote actually works
        if not _validate_remote(base_remote):
            raise click.ClickException(
                f"Remote '{base_remote}' not working after auth. "
                "Check rclone config and try again."
            )
        click.echo(f"Remote '{base_remote}' authenticated successfully.")

    # Step 3: List shared drives (unless --personal-only)
    config = load_config()
    token = _get_token(base_remote)

    if not personal_only:
        click.echo(f"\nFetching shared drives via '{base_remote}'...")
        try:
            drives = rclone.backend_drives(base_remote)
        except rclone.RcloneError as exc:
            click.echo(f"Could not list shared drives: {exc.stderr}")
            drives = []

        if drives:
            click.echo(f"\nFound {len(drives)} shared drive(s):\n")
            for i, drive in enumerate(drives, 1):
                click.echo(f"  {i}. {drive['name']} ({drive['id']})")

            click.echo("\n  0. Skip shared drives")
            selection = click.prompt(
                "\nSelect drives to enable (comma-separated, e.g. 1,2,3)",
                default="0",
            )

            if selection.strip() != "0":
                indices = [
                    int(s.strip()) for s in selection.split(",") if s.strip().isdigit()
                ]
                for idx in indices:
                    if 1 <= idx <= len(drives):
                        _create_shared_drive_remote(
                            drives[idx - 1],
                            token,
                            config,
                        )
        else:
            click.echo("No shared drives found.")

    # Step 4: Register the base remote in config
    if base_remote not in config.get("remotes", {}):
        config.setdefault("remotes", {})[base_remote] = {
            "drive_name": "My Drive",
            "drive_id": "",
            "type": "personal",
        }

    save_config(config)
    click.echo(f"\nConfig saved to {CONFIG_PATH}")
    count = len(config["remotes"])
    click.echo(f"Configured {count} remote(s). Run 'gdrive ls' to verify.")


def _create_shared_drive_remote(
    drive: dict,
    token: str | None,
    config: dict,
) -> None:
    """Create an rclone remote for a single shared drive."""
    safe_name = drive["name"].lower().replace(" ", "-")
    safe_name = "".join(c if c.isalnum() or c == "-" else "_" for c in safe_name)
    remote_name = click.prompt(
        f"  Remote name for '{drive['name']}'",
        default=safe_name,
    )

    create_params = {
        "scope": "drive",
        "team_drive": drive["id"],
    }
    if token:
        create_params["token"] = token

    try:
        rclone.config_create(remote_name, "drive", **create_params)
        config.setdefault("remotes", {})[remote_name] = {
            "drive_name": drive["name"],
            "drive_id": drive["id"],
            "type": "shared",
        }
        click.echo(f"  Created remote: {remote_name}")
    except rclone.RcloneError as exc:
        click.echo(f"  Failed to create {remote_name}: {exc.stderr}")
