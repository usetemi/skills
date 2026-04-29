"""Health check for the ga4 CLI — diagnoses auth, config, and reachability."""

from __future__ import annotations

import sys

import click
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
from google.api_core import exceptions as gax

from ga4.auth import CREDENTIALS_PATH, SCOPE_READONLY, get_credentials
from ga4.config import CONFIG_DIR, CONFIG_PATH, get_config_value
from ga4.doctor_helpers import _fail, _pass, _warn


@click.command()
def doctor() -> None:  # noqa: C901, PLR0912, PLR0915
    """Check ga4 setup and diagnose problems."""
    ok = True

    # 1. Config directory writable
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _pass(f"config dir writable ({CONFIG_DIR})")
    except OSError as exc:
        _fail(f"config dir not writable ({CONFIG_DIR}): {exc}")
        ok = False

    # 2. Config file
    if CONFIG_PATH.exists():
        _pass(f"config file exists ({CONFIG_PATH})")
    else:
        _warn("no config file (will be created on first `ga4 config set-property`)")

    # 3. Default property
    default_property = get_config_value("default-property")
    if default_property:
        _pass(f"default property set ({default_property})")
    else:
        _warn("no default property set (use --property / -p or `ga4 config set-property`)")

    # 4. OAuth credentials
    if CREDENTIALS_PATH.exists():
        _pass(f"OAuth credentials present ({CREDENTIALS_PATH})")
    else:
        _fail("no OAuth credentials — run `ga4 auth login --client-secret <path>`")
        _summary(ok=False)
        return

    # 5. Resolve credentials
    try:
        creds = get_credentials([SCOPE_READONLY])
    except click.ClickException as exc:
        _fail(f"credential resolution failed: {exc.message}")
        _summary(ok=False)
        return
    _pass(f"resolved credentials ({type(creds).__name__})")

    # 6. Ping the Admin API with the resolved credentials
    try:
        client = AnalyticsAdminServiceClient(credentials=creds)
        account_count = sum(1 for _ in client.list_accounts())
    except gax.PermissionDenied as exc:
        if "has not been used in project" in str(exc) or "SERVICE_DISABLED" in str(exc):
            _fail(
                "Admin API is not enabled in the OAuth client's GCP project. "
                "Enable it: "
                "https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com",
            )
            ok = False
        else:
            _fail("Admin API reachable but caller has no account access — grant in GA Admin")
            ok = False
    except gax.GoogleAPIError as exc:
        _fail(f"Admin API error: {exc}")
        ok = False
    except Exception as exc:
        _fail(f"Admin API call crashed: {exc}")
        ok = False
    else:
        if account_count == 0:
            _fail("Admin API reachable but 0 accounts visible — grant GA access in GA Admin")
            ok = False
        else:
            _pass(f"Admin API reachable ({account_count} account(s) visible)")

    _summary(ok=ok)


def _summary(*, ok: bool) -> None:
    click.echo()
    if ok:
        click.echo("All checks passed.")
    else:
        click.echo("Some checks failed. See above for details.")
        sys.exit(1)
