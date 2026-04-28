"""OAuth2 authentication for Google Search Console."""

from __future__ import annotations

import json
import os

import click
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from gsc.config import CONFIG_DIR

SCOPES = ["https://www.googleapis.com/auth/webmasters"]
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"


def load_credentials() -> Credentials | None:
    """Load stored credentials, refreshing if expired. Returns None if unavailable."""
    if not CREDENTIALS_PATH.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(CREDENTIALS_PATH), SCOPES)
    except (json.JSONDecodeError, ValueError, KeyError):
        return None
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
        except Exception:
            return None
    if not creds.valid:
        return None
    return creds


def require_credentials() -> Credentials:
    """Load credentials or raise ClickException with instructions."""
    creds = load_credentials()
    if creds is None:
        raise click.ClickException(
            "Not authenticated. Run: gsc auth login "
            "--client-secret <path-to-client_secret.json>"
        )
    return creds


def _save_credentials(creds: Credentials) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(creds.to_json())


def _is_headless() -> bool:
    return not os.environ.get("DISPLAY") and not os.environ.get("BROWSER")


@click.group()
def auth():
    """Manage authentication."""


@auth.command()
@click.option(
    "--client-secret",
    required=True,
    type=click.Path(exists=True),
    help="Path to OAuth client_secret.json from GCP.",
)
@click.option("--port", default=8085, help="Local port for OAuth callback.")
def login(client_secret: str, port: int):
    """Authenticate with Google Search Console via OAuth."""
    if _is_headless():
        click.echo(
            "Headless environment detected. Open an SSH tunnel before continuing:\n"
            f"  ssh -L {port}:localhost:{port} <this-host>\n"
            "Then open the printed URL on a machine with a browser.",
            err=True,
        )

    flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
    creds = flow.run_local_server(port=port, open_browser=not _is_headless())
    _save_credentials(creds)
    click.echo(json.dumps({"status": "authenticated", "scopes": SCOPES}))


@auth.command()
def status():
    """Check authentication status."""
    creds = load_credentials()
    if creds is None:
        click.echo(json.dumps({"authenticated": False}))
    else:
        info: dict = {"authenticated": True, "scopes": list(creds.scopes or SCOPES)}
        if creds.expiry:
            info["expiry"] = creds.expiry.isoformat()
        click.echo(json.dumps(info))


@auth.command()
def logout():
    """Remove stored credentials."""
    if CREDENTIALS_PATH.exists():
        CREDENTIALS_PATH.unlink()
        click.echo(json.dumps({"status": "logged_out"}))
    else:
        click.echo(json.dumps({"status": "already_logged_out"}))
