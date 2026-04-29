"""Configuration storage for gsc."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click


def get_config_dir() -> Path:
    """Resolve the gsc config directory, honoring GSC_CONFIG_DIR override."""
    override = os.environ.get("GSC_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "skills" / "gsc"


def legacy_config_dir() -> Path | None:
    """Return the pre-migration `~/.config/gsc/` path if it exists and differs from the current dir."""
    legacy = Path.home() / ".config" / "gsc"
    if legacy != get_config_dir() and legacy.exists():
        return legacy
    return None


CONFIG_DIR = get_config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"

VALID_KEYS = {"pagespeed-api-key"}

MASK_PREFIX_CHARS = 4


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def get_config_value(key: str) -> str | None:
    return load_config().get(key)


def _mask_value(value: str) -> str:
    if len(value) <= MASK_PREFIX_CHARS:
        return "****"
    return value[:MASK_PREFIX_CHARS] + "*" * (len(value) - MASK_PREFIX_CHARS)


@click.group()
def config():
    """Manage configuration."""


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value."""
    if key not in VALID_KEYS:
        raise click.ClickException(
            f"Unknown key {key!r}. Valid keys: {', '.join(sorted(VALID_KEYS))}",
        )
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    click.echo(json.dumps({"status": "saved", "key": key}))


@config.command("get")
@click.argument("key")
def config_get(key: str):
    """Get a configuration value."""
    cfg = load_config()
    value = cfg.get(key)
    if value is None:
        raise click.ClickException(f"Key {key!r} is not set.")
    click.echo(json.dumps({"key": key, "value": _mask_value(value)}))


@config.command("show")
def config_show():
    """Show all configuration values (secrets masked)."""
    cfg = load_config()
    masked = {
        k: _mask_value(v) if "key" in k or "secret" in k else v for k, v in cfg.items()
    }
    click.echo(json.dumps(masked, indent=2))


@config.command("migrate")
@click.option("--apply", is_flag=True, help="Move files (default is dry-run).")
def config_migrate(apply: bool) -> None:
    """Move config from the legacy `~/.config/gsc/` to `~/.config/skills/gsc/`."""
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
    click.echo(json.dumps({"status": "migrated", "old": str(old), "new": str(new), "files": files}))
