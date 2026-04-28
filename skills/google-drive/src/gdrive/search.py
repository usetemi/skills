"""Search for files on Google Drive."""

from __future__ import annotations

import click

from gdrive import rclone
from gdrive.auth import import_rclone_remotes, load_config


def _resolve_search_scope(args: tuple[str, ...]) -> tuple[list[str], tuple[str, ...]]:
    """Split args into (remotes_to_search, query_parts) based on optional remote: prefix."""
    if args[0].endswith(":"):
        return [args[0].rstrip(":")], args[1:]
    config = load_config()
    if not config.get("remotes"):
        config = import_rclone_remotes()
    return list(config.get("remotes", {}).keys()), args


def _print_search_results(remote: str, results: list[dict]) -> None:
    """Print search results for a single remote."""
    click.echo(f"\n{remote}: ({len(results)} result(s))\n")
    for item in results:
        name = item.get("name", "?")
        mime = item.get("mimeType", "")
        modified = item.get("modifiedTime", "")[:10]
        link = item.get("webViewLink", "")
        kind = _mime_label(mime)
        click.echo(f"  {name}  [{kind}]  {modified}")
        if link:
            click.echo(f"    {link}")


@click.command()
@click.argument("args", nargs=-1, required=True)
def search(args: tuple[str, ...]):
    """Search for files on Google Drive.

    Search all configured remotes, or scope to one:

    \b
      gdrive search budget
      gdrive search mydrive: budget report
    """
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    remotes_to_search, query_parts = _resolve_search_scope(args)

    if not query_parts:
        raise click.ClickException("No search query provided.")

    if not remotes_to_search:
        raise click.ClickException("No remotes configured. Run 'gdrive auth' first.")

    query_text = " ".join(query_parts)
    drive_query = f"name contains '{query_text}'"

    total = 0
    for remote in remotes_to_search:
        try:
            results = rclone.backend_query(remote, drive_query)
        except rclone.RcloneError as exc:
            click.echo(f"\n{remote}: search failed ({exc.stderr})")
            continue

        if not results:
            continue

        _print_search_results(remote, results)
        total += len(results)

    if total == 0:
        click.echo(f"\nNo results for '{query_text}'.")
    else:
        click.echo(f"\n{total} result(s) total.")


def _mime_label(mime: str) -> str:
    """Short label from MIME type."""
    labels = {
        "application/vnd.google-apps.document": "doc",
        "application/vnd.google-apps.spreadsheet": "sheet",
        "application/vnd.google-apps.presentation": "slides",
        "application/vnd.google-apps.folder": "folder",
    }
    return labels.get(mime, mime.rsplit("/", maxsplit=1)[-1] if "/" in mime else "file")
