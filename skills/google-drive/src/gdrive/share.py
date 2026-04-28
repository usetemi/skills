"""Set permissions on Google Drive files via the Drive API."""

from __future__ import annotations

import contextlib
import json
import urllib.error
import urllib.request

import click

from gdrive import rclone
from gdrive.auth import _get_token
from gdrive.pull import _get_remote_metadata, _parse_remote_path


def _get_access_token(remote: str) -> str:
    """Get a fresh access token for a remote.

    Forces a token refresh via rclone about, then extracts the token
    from rclone config.
    """
    with contextlib.suppress(rclone.RcloneError):
        rclone.about(remote)

    token_json = _get_token(remote)
    if not token_json:
        raise click.ClickException(
            f"No token found for remote '{remote}'. Run 'gdrive auth' first."
        )

    token_data = json.loads(token_json)
    access_token = token_data.get("access_token")
    if not access_token:
        raise click.ClickException(
            f"Token for remote '{remote}' has no access_token. Re-run 'gdrive auth'."
        )
    return access_token


def _create_permission(
    file_id: str,
    access_token: str,
    permission: dict,
) -> dict:
    """Create a permission on a Drive file via the REST API."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
    # sendNotificationEmail=false to avoid spamming for link shares
    params = "?supportsAllDrives=true"
    if permission.get("type") == "anyone":
        params += "&sendNotificationEmail=false"

    body = json.dumps(permission).encode()
    # URL is built from a hardcoded https:// prefix and a Drive file id; not user-controlled.
    req = urllib.request.Request(  # noqa: S310
        url + params,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode()
        try:
            detail = json.loads(error_body).get("error", {}).get("message", error_body)
        except (json.JSONDecodeError, AttributeError):
            detail = error_body
        raise click.ClickException(f"Drive API error: {detail}") from exc


@click.command()
@click.argument("remote_path")
@click.argument("email", required=False)
@click.option(
    "--role",
    type=click.Choice(["reader", "writer", "commenter"]),
    default="reader",
    help="Permission role (default: reader)",
)
@click.option(
    "--anyone",
    is_flag=True,
    help="Share with anyone who has the link",
)
def share(remote_path: str, email: str | None, role: str, anyone: bool):
    """Set sharing permissions on a Google Drive file.

    REMOTE_PATH is in the format remote:path/to/file.
    EMAIL is the email address to share with (not needed with --anyone).
    """
    if not anyone and not email:
        raise click.ClickException(
            "Provide an email address or use --anyone for link sharing."
        )

    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    remote, _ = _parse_remote_path(remote_path)

    # Get file ID from metadata
    click.echo(f"Looking up {remote_path}...")
    try:
        metadata = _get_remote_metadata(remote_path)
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Failed to get metadata: {exc.stderr}") from exc

    file_id = metadata.get("ID")
    if not file_id:
        raise click.ClickException(f"Could not get file ID for {remote_path}")

    # Get access token
    access_token = _get_access_token(remote)

    # Build permission
    if anyone:
        permission = {"type": "anyone", "role": role}
        target = "anyone with the link"
    else:
        permission = {"type": "user", "role": role, "emailAddress": email}
        target = email

    click.echo(f"Sharing with {target} as {role}...")
    _create_permission(file_id, access_token, permission)
    click.echo(f"Shared {remote_path} with {target} ({role}).")
