"""Upload local files to Google Drive with manifest tracking."""

from __future__ import annotations

from pathlib import Path

import click

from gdrive import rclone
from gdrive.manifest import (
    GOOGLE_MIME_TYPES,
    IMPORT_FORMATS,
    Manifest,
    ManifestEntry,
    _local_mtime_iso,
    _now_iso,
    compute_md5,
)
from gdrive.pull import _get_remote_metadata, _parse_remote_path


def _choose_upload_strategy(local: Path, entry: ManifestEntry | None) -> list[str]:
    """Pick rclone extra args for re-importing as a Google native doc, if applicable."""
    if entry and entry.original_mime_type in GOOGLE_MIME_TYPES:
        import_format = IMPORT_FORMATS.get(local.suffix.lower())
        if import_format:
            label = _mime_to_label(entry.original_mime_type)
            click.echo(f"Re-importing as Google {label}")
            return ["--drive-import-formats", import_format]
    elif not entry and local.suffix.lower() in IMPORT_FORMATS and click.confirm(
        f"Import {local.name} as a Google native document?",
        default=False,
    ):
        return ["--drive-import-formats", IMPORT_FORMATS[local.suffix.lower()]]
    return []


def _abort_on_remote_conflict(
    local: Path,
    full_remote: str,
    entry: ManifestEntry,
) -> bool:
    """Prompt user if the remote changed since last sync. Returns True if user chose abort."""
    try:
        current = _get_remote_metadata(full_remote)
    except (rclone.RcloneError, click.ClickException):
        return False
    current_mtime = current.get("ModTime", "")
    if not current_mtime or current_mtime == entry.remote_mtime_at_sync:
        return False
    click.echo(f"Remote file {local.name} changed since last sync.")
    click.echo(f"  Last synced:  {entry.remote_mtime_at_sync}")
    click.echo(f"  Remote now:   {current_mtime}")
    action = click.prompt(
        "Choose action",
        type=click.Choice(["push", "abort"]),
        default="abort",
    )
    if action == "abort":
        click.echo("Aborted. Run 'gdrive pull' to get the remote version first.")
        return True
    return False


def _push_single_file(
    local: Path,
    remote: str,
    path: str,
    manifest: Manifest,
    entry: ManifestEntry | None,
    force: bool,
) -> bool:
    """Upload a single file and update manifest. Returns True on success."""
    full_remote = f"{remote}:{path}"
    extra_args = _choose_upload_strategy(local, entry)

    if (
        entry
        and entry.remote_mtime_at_sync
        and not force
        and _abort_on_remote_conflict(local, full_remote, entry)
    ):
        return False

    # Upload
    click.echo(f"Uploading {local.name} to {full_remote}...")
    try:
        rclone.copyto(str(local), full_remote, extra_args=extra_args)
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Upload failed: {exc.stderr}") from exc

    # Fetch updated remote metadata
    click.echo("Verifying upload...")
    try:
        metadata = _get_remote_metadata(full_remote)
        remote_md5 = metadata.get("Hashes", {}).get("MD5", "")
        remote_mtime = metadata.get("ModTime", "")
        drive_id = metadata.get("ID", "")
    except (rclone.RcloneError, click.ClickException):
        remote_md5 = ""
        remote_mtime = _now_iso()
        drive_id = entry.drive_id if entry else ""

    # Preserve the original MIME type from the manifest entry.
    # rclone lsjson reports native Google docs with their export MIME type,
    # so re-fetching metadata after push would overwrite the correct native
    # type (e.g. application/vnd.google-apps.spreadsheet) with the export
    # type (e.g. application/vnd.openxmlformats-...).
    mime_type = entry.original_mime_type if entry else ""

    # Update manifest
    local_md5 = compute_md5(local)
    new_entry = ManifestEntry(
        drive_id=drive_id,
        remote=remote,
        remote_path=path,
        original_mime_type=mime_type,
        local_md5=local_md5,
        remote_md5=remote_md5,
        last_synced=_now_iso(),
        local_mtime_at_sync=_local_mtime_iso(local),
        remote_mtime_at_sync=remote_mtime,
    )
    manifest.upsert(local, new_entry)
    click.echo(f"Uploaded {local.name}. Manifest updated.")
    return True


@click.command()
@click.argument("local_path", required=False, type=click.Path())
@click.argument("remote_dest", required=False)
@click.option("--force", "-f", is_flag=True, help="Overwrite remote")
@click.option(
    "--all",
    "-a",
    "push_all",
    is_flag=True,
    help="Push all locally-modified tracked files",
)
@click.option(
    "--remote",
    "-r",
    "filter_remote",
    help="Filter by remote name (with --all)",
)
def push(
    local_path: str | None,
    remote_dest: str | None,
    force: bool,
    push_all: bool,
    filter_remote: str | None,
):
    """Upload local files to Google Drive.

    LOCAL_PATH is the file to upload.
    REMOTE_DEST is optional remote:path (uses manifest entry if omitted).
    Use --all to push all locally-modified tracked files.
    """
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    if push_all:
        _push_all(force, filter_remote)
        return

    if not local_path:
        raise click.ClickException(
            "Provide a file to push, or use --all to push all modified files."
        )

    local = Path(local_path).resolve()
    if not local.exists():
        raise click.ClickException(f"File not found: {local_path}")

    manifest = Manifest()
    entry = manifest.get(local)

    # Determine remote destination
    if remote_dest:
        remote, path = _parse_remote_path(remote_dest)
    elif entry:
        remote = entry.remote
        path = entry.remote_path
    else:
        raise click.ClickException(
            "No manifest entry for this file. Specify a remote destination:\n"
            "  gdrive push file.docx remote:path/to/file.docx"
        )

    _push_single_file(local, remote, path, manifest, entry, force)


def _find_modified_files(
    entries: dict[str, ManifestEntry],
    filter_remote: str | None,
) -> list[tuple[Path, ManifestEntry]]:
    """Return tracked files whose local content changed since last sync."""
    modified: list[tuple[Path, ManifestEntry]] = []
    for path_str, entry in entries.items():
        local = Path(path_str)
        if not local.exists():
            continue
        if filter_remote and entry.remote != filter_remote:
            continue
        if compute_md5(local) != entry.local_md5:
            modified.append((local, entry))
    return modified


def _push_all(force: bool, filter_remote: str | None) -> None:
    """Push all locally-modified tracked files."""
    manifest = Manifest()
    entries = manifest.all_entries()

    if not entries:
        click.echo("No tracked files in manifest.")
        return

    modified = _find_modified_files(entries, filter_remote)

    if not modified:
        scope = f" on {filter_remote}" if filter_remote else ""
        click.echo(f"No locally-modified tracked files{scope}.")
        return

    click.echo(f"Found {len(modified)} modified file(s):")
    for local, entry in modified:
        click.echo(f"  {local.name} -> {entry.remote}:{entry.remote_path}")

    if not force and not click.confirm("\nPush all?", default=True):
        click.echo("Aborted.")
        return

    pushed = 0
    for local, entry in modified:
        try:
            if _push_single_file(
                local,
                entry.remote,
                entry.remote_path,
                manifest,
                entry,
                force,
            ):
                pushed += 1
        except click.ClickException as exc:
            click.echo(f"Error pushing {local.name}: {exc.message}")

    click.echo(f"\nPushed {pushed}/{len(modified)} file(s).")


def _mime_to_label(mime_type: str) -> str:
    """Convert MIME type to human-readable label."""
    labels = {
        "application/vnd.google-apps.document": "Doc",
        "application/vnd.google-apps.spreadsheet": "Sheet",
        "application/vnd.google-apps.presentation": "Slides",
    }
    return labels.get(mime_type, "document")
