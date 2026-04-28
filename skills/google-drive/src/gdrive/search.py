"""Search for files on Google Drive."""

from __future__ import annotations

import click

from gdrive import rclone
from gdrive.auth import import_rclone_remotes, load_config


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

    # Parse: if first arg contains ':', it's a remote scope
    if args[0].endswith(":"):
        remotes_to_search = [args[0].rstrip(":")]
        query_parts = args[1:]
    else:
        config = load_config()
        if not config.get("remotes"):
            config = import_rclone_remotes()
        remotes_to_search = list(config.get("remotes", {}).keys())
        query_parts = args

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
    return labels.get(mime, mime.split("/")[-1] if "/" in mime else "file")
