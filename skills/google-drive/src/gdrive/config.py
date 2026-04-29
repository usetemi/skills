"""Configuration storage for gdrive.

Operates on the same `config.json` used by `gdrive.auth`, but only on top-level
keys — the `remotes` map is owned by `auth setup` / `auth logout` and is not
exposed via `gdrive config`.
"""

from __future__ import annotations

import json

import click

from gdrive.auth import CONFIG_PATH, load_config, save_config
from gdrive.manifest import get_config_dir, legacy_config_dir

VALID_KEYS: set[str] = set()


def get_config_value(key: str) -> str | None:
    return load_config().get(key)


@click.group()
def config() -> None:
    """Manage configuration."""


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    if key not in VALID_KEYS:
        valid = ", ".join(sorted(VALID_KEYS)) or "(none defined yet)"
        raise click.ClickException(f"Unknown key {key!r}. Valid keys: {valid}")
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    click.echo(json.dumps({"status": "saved", "key": key}))


@config.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """Get a configuration value."""
    value = get_config_value(key)
    if value is None:
        raise click.ClickException(f"Key {key!r} is not set.")
    click.echo(json.dumps({"key": key, "value": value}))


@config.command("show")
def config_show() -> None:
    """Show all configuration values (excluding the remotes map)."""
    cfg = load_config()
    click.echo(json.dumps({k: v for k, v in cfg.items() if k != "remotes"}, indent=2))


@config.command("migrate")
@click.option("--apply", is_flag=True, help="Move files (default is dry-run).")
def config_migrate(apply: bool) -> None:
    """Move config from the legacy `~/.config/gdrive/` to `~/.config/skills/gdrive/`."""
    old = legacy_config_dir()
    new = get_config_dir()
    if old is None:
        click.echo(json.dumps({"status": "no_migration_needed", "path": str(new)}))
        return
    files = sorted(str(p.relative_to(old)) for p in old.rglob("*") if p.is_file())
    if not apply:
        click.echo(
            json.dumps(
                {"status": "dry_run", "old": str(old), "new": str(new), "files": files},
                indent=2,
            ),
        )
        click.echo("Run with --apply to perform the move.", err=True)
        return
    if new.exists():
        raise click.ClickException(f"Target {new} already exists; refusing to overwrite.")
    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)
    click.echo(
        json.dumps(
            {"status": "migrated", "old": str(old), "new": str(new), "files": files},
            indent=2,
        ),
    )


# CONFIG_PATH re-exported for convenience; same file as auth.CONFIG_PATH
__all__ = ["CONFIG_PATH", "VALID_KEYS", "config"]
