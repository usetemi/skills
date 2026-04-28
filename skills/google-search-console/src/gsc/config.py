"""Configuration storage for gsc."""

from __future__ import annotations

import json
from pathlib import Path

import click

CONFIG_DIR = Path.home() / ".config" / "gsc"
CONFIG_PATH = CONFIG_DIR / "config.json"

VALID_KEYS = {"pagespeed-api-key"}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def get_config_value(key: str) -> str | None:
    return load_config().get(key)


def _mask_value(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return value[:4] + "*" * (len(value) - 4)


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
            f"Unknown key '{key}'. Valid keys: {', '.join(sorted(VALID_KEYS))}"
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
        raise click.ClickException(f"Key '{key}' is not set.")
    click.echo(json.dumps({"key": key, "value": _mask_value(value)}))


@config.command("show")
def config_show():
    """Show all configuration values (secrets masked)."""
    cfg = load_config()
    masked = {
        k: _mask_value(v) if "key" in k or "secret" in k else v for k, v in cfg.items()
    }
    click.echo(json.dumps(masked, indent=2))
