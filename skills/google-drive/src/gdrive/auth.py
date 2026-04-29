"""Auth setup: configure rclone remotes for Google Drive shared drives."""

from __future__ import annotations

import json
import os

import click

from gdrive import rclone
from gdrive.manifest import CONFIG_DIR, legacy_config_dir

CONFIG_PATH = CONFIG_DIR / "config.json"


def _deprecation_warning() -> str | None:
    """Build a one-line warning if legacy config dir exists; None otherwise."""
    legacy = legacy_config_dir()
    if legacy is None:
        return None
    return f"Legacy config at {legacy}. Run: gdrive config migrate --apply"


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
    except rclone.RcloneError:
        return False
    return True


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


def _pick_existing_base_remote(existing: list[str]) -> str | None:
    """Prompt the user to reuse an existing rclone drive remote, deleting broken ones."""
    for name in existing:
        click.echo(f"Found drive remote: {name} ... ", nl=False)
        if _validate_remote(name):
            click.echo("OK")
            if click.confirm(f"Use '{name}' as the base remote?", default=True):
                return name
        else:
            click.echo("broken (invalid token)")
            if click.confirm(f"Delete broken remote '{name}'?", default=True):
                try:
                    rclone.config_delete(name)
                    click.echo(f"  Deleted {name}")
                except rclone.RcloneError as exc:
                    click.echo(f"  Failed to delete: {exc.stderr}")
    return None


def _create_base_remote() -> str:
    """Prompt for a name, create the rclone drive remote, and run OAuth interactively."""
    click.echo("\nCreating a new base drive remote.")

    if _is_headless():
        click.echo(
            "\nHeadless environment detected. Before proceeding:\n"
            "  Set up an SSH tunnel from a machine with a browser:\n"
            "  ssh -L 53682:localhost:53682 <this-host>\n"
        )

    base_remote = click.prompt("Name for the base remote", default="gdrive")

    click.echo(f"\nCreating remote '{base_remote}'...")
    try:
        rclone.config_create(base_remote, "drive", scope="drive")
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Failed to create remote: {exc.stderr}") from exc

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

    if not _validate_remote(base_remote):
        raise click.ClickException(
            f"Remote '{base_remote}' not working after auth. "
            "Check rclone config and try again."
        )
    click.echo(f"Remote '{base_remote}' authenticated successfully.")
    return base_remote


def _enroll_shared_drives(base_remote: str, token: str | None, config: dict) -> None:
    """List shared drives accessible via base_remote and prompt to register them."""
    click.echo(f"\nFetching shared drives via '{base_remote}'...")
    try:
        drives = rclone.backend_drives(base_remote)
    except rclone.RcloneError as exc:
        click.echo(f"Could not list shared drives: {exc.stderr}")
        return

    if not drives:
        click.echo("No shared drives found.")
        return

    click.echo(f"\nFound {len(drives)} shared drive(s):\n")
    for index, drive in enumerate(drives, 1):
        click.echo(f"  {index}. {drive['name']} ({drive['id']})")

    click.echo("\n  0. Skip shared drives")
    selection = click.prompt(
        "\nSelect drives to enable (comma-separated, e.g. 1,2,3)",
        default="0",
    )
    if selection.strip() == "0":
        return

    indices = [int(s.strip()) for s in selection.split(",") if s.strip().isdigit()]
    for index in indices:
        if 1 <= index <= len(drives):
            _create_shared_drive_remote(drives[index - 1], token, config)


@click.group()
def auth() -> None:
    """Set up and inspect Google Drive remotes."""


@auth.command()
@click.option(
    "--personal-only",
    is_flag=True,
    help="Only set up personal My Drive, skip shared drives.",
)
def setup(personal_only: bool):
    """Run the interactive remote-configuration wizard."""
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo("Setting up Google Drive access via rclone.\n")

    base_remote = _pick_existing_base_remote(_find_all_drive_remotes())
    if not base_remote:
        base_remote = _create_base_remote()

    config = load_config()
    token = _get_token(base_remote)

    if not personal_only:
        _enroll_shared_drives(base_remote, token, config)

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


@auth.command()
def status() -> None:
    """Report which remotes are configured and whether they authenticate."""
    config = load_config()
    remotes = config.get("remotes", {})
    remote_status = []
    any_authenticated = False
    for name, info in remotes.items():
        ok = _validate_remote(name)
        if ok:
            any_authenticated = True
        remote_status.append({
            "name": name,
            "drive_name": info.get("drive_name", ""),
            "type": info.get("type", ""),
            "authenticated": ok,
        })
    info_dict: dict = {
        "authenticated": any_authenticated and bool(remotes),
        "remotes": remote_status,
    }
    if warning := _deprecation_warning():
        info_dict["deprecation_warning"] = warning
    click.echo(json.dumps(info_dict, indent=2))


@auth.command()
def logout() -> None:
    """Forget gdrive's remote registrations.

    Clears the `remotes` map in `~/.config/skills/gdrive/config.json`.
    Rclone remotes themselves remain intact — use `rclone config delete`
    to remove them.
    """
    config = load_config()
    had_remotes = bool(config.get("remotes"))
    config["remotes"] = {}
    save_config(config)
    click.echo(json.dumps({"status": "logged_out" if had_remotes else "already_logged_out"}))


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
