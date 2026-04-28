"""Configuration storage for ga4."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click


def get_config_dir() -> Path:
    """Resolve the ga4 config directory, honoring GA4_CONFIG_DIR override."""
    override = os.environ.get("GA4_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "ga4"


CONFIG_DIR = get_config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"

VALID_KEYS = {"default-property"}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n")


def get_config_value(key: str) -> str | None:
    return load_config().get(key)


def normalize_property(value: str) -> str:
    """Normalize a property id to the canonical `properties/<id>` resource-name form.

    Accepts either `123456789` or `properties/123456789`. Raises ValueError on garbage.
    """
    value = value.strip()
    if value.startswith("properties/"):
        tail = value.removeprefix("properties/")
        if not tail.isdigit():
            msg = f"invalid property id {value!r} (expected numeric id)"
            raise ValueError(msg)
        return value
    if value.isdigit():
        return f"properties/{value}"
    msg = f"invalid property id {value!r} (expected `123…` or `properties/123…`)"
    raise ValueError(msg)


def resolve_property(flag_value: str | None) -> str:
    """Resolve a property id from --property flag, GA_PROPERTY_ID env, or config default.

    Returns the canonical `properties/<id>` resource-name form.
    """
    candidate = flag_value or os.environ.get("GA_PROPERTY_ID") or get_config_value("default-property")
    if not candidate:
        raise click.ClickException(
            "No property id. Pass --property / -p, or set GA_PROPERTY_ID, "
            "or run: ga4 config set-property <id>",
        )
    try:
        return normalize_property(candidate)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@click.group()
def config() -> None:
    """Manage configuration."""


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
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
def config_get(key: str) -> None:
    """Get a configuration value."""
    value = get_config_value(key)
    if value is None:
        raise click.ClickException(f"Key {key!r} is not set.")
    click.echo(json.dumps({"key": key, "value": value}))


@config.command("show")
def config_show() -> None:
    """Show all configuration values."""
    click.echo(json.dumps(load_config(), indent=2))


@config.command("set-property")
@click.argument("property_id")
def config_set_property(property_id: str) -> None:
    """Set the default property id (accepts `123…` or `properties/123…`)."""
    try:
        canonical = normalize_property(property_id)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    cfg = load_config()
    cfg["default-property"] = canonical
    save_config(cfg)
    click.echo(json.dumps({"status": "saved", "default-property": canonical}))
