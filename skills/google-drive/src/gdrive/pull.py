"""Download files from Google Drive with manifest tracking."""

from __future__ import annotations

import fnmatch
from pathlib import Path

import click

from gdrive import rclone
from gdrive.manifest import (
    EXPORT_TO_NATIVE_MIME,
    GOOGLE_MIME_TYPES,
    Manifest,
    ManifestEntry,
    _local_mtime_iso,
    _now_iso,
    compute_md5,
)


def _parse_remote_path(remote_path: str) -> tuple[str, str]:
    """Split 'remote:path' into (remote, path)."""
    if ":" not in remote_path:
        raise click.ClickException(
            f"Invalid remote path: {remote_path}. Expected format: remote:path/to/file"
        )
    remote, _, path = remote_path.partition(":")
    return remote, path


def _get_remote_metadata(remote_path: str) -> dict:
    """Fetch metadata for a single remote file via lsjson."""
    remote, path = _parse_remote_path(remote_path)
    parent = str(Path(path).parent)
    filename = Path(path).name

    # lsjson on the parent directory, then filter
    search_path = f"{remote}:{parent}" if parent != "." else f"{remote}:"
    items = rclone.lsjson(search_path, with_hash=True)

    # For Google native docs, the remote name won't have an extension
    # but lsjson returns the name as-is
    for item in items:
        if item.get("Name") == filename or item.get("Path") == Path(path).name:
            return item

    # Try the exact path (for cases where the file is at root or name matches)
    items = rclone.lsjson(remote_path, with_hash=True)
    if items:
        return items[0]

    raise click.ClickException(f"File not found: {remote_path}")


def _pull_single_file(
    remote: str,
    path: str,
    metadata: dict,
    local_dest: Path,
    manifest: Manifest,
    force: bool,
) -> Path:
    """Download a single file and update manifest. Returns the local path."""
    remote_path = f"{remote}:{path}"
    mime_type = metadata.get("MimeType", "")
    drive_id = metadata.get("ID", "")
    remote_md5 = metadata.get("Hashes", {}).get("MD5", "")
    remote_mtime = metadata.get("ModTime", "")
    filename = metadata.get("Name", Path(path).name)

    # Determine if this is a Google native document.
    # rclone lsjson reports native docs with their export MIME type (e.g.
    # application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
    # but Size == -1 reliably identifies them as native Google docs.
    is_native = metadata.get("Size", 0) == -1 and mime_type in EXPORT_TO_NATIVE_MIME
    if is_native:
        mime_type = EXPORT_TO_NATIVE_MIME[mime_type]
    export_ext = GOOGLE_MIME_TYPES.get(mime_type, "")

    if is_native:
        if not filename.endswith(export_ext):
            filename = filename + export_ext
        click.echo(f"Google native document detected ({mime_type})")
        click.echo(f"Will export as: {filename}")

    # Determine local destination
    dest = local_dest / filename if local_dest.is_dir() else local_dest

    # Check if file already tracked and local is newer
    existing = manifest.get(dest)
    if existing and dest.exists() and not force:
        local_md5 = compute_md5(dest)
        if local_md5 != existing.local_md5 and not click.confirm(
            f"Local file {dest.name} modified since last sync. Overwrite?",
            default=False,
        ):
            click.echo(f"Skipped {dest.name}.")
            return dest

    # Download
    click.echo(f"Downloading to {dest}...")
    extra_args = []
    if is_native:
        extra_args = ["--drive-export-formats", export_ext.lstrip(".")]

    try:
        rclone.copyto(remote_path, str(dest), extra_args=extra_args)
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Download failed: {exc.stderr}") from exc

    if not dest.exists():
        possible = list(dest.parent.glob(f"{dest.stem}.*"))
        if possible:
            dest = possible[0]
        else:
            raise click.ClickException(
                f"Download completed but file not found at {dest}",
            )

    # Update manifest
    local_md5 = compute_md5(dest)
    entry = ManifestEntry(
        drive_id=drive_id,
        remote=remote,
        remote_path=path,
        original_mime_type=mime_type,
        local_md5=local_md5,
        remote_md5=remote_md5,
        last_synced=_now_iso(),
        local_mtime_at_sync=_local_mtime_iso(dest),
        remote_mtime_at_sync=remote_mtime,
    )
    manifest.upsert(dest, entry)
    click.echo(f"Saved to {dest} (tracked in manifest)")
    return dest


@click.command()
@click.argument("remote_path")
@click.argument("local_dest", required=False)
@click.option("--force", "-f", is_flag=True, help="Overwrite without warning")
@click.option(
    "--include",
    "-i",
    "include_pattern",
    help="Glob pattern filter (e.g. '*.docx')",
)
@click.option("--recursive", "-R", is_flag=True, help="Pull subdirectories recursively")
def pull(
    remote_path: str,
    local_dest: str | None,
    force: bool,
    include_pattern: str | None,
    recursive: bool,
):
    """Download files from Google Drive.

    REMOTE_PATH is remote:path/to/file or remote:folder/ for batch.
    LOCAL_DEST is the local destination (defaults to current directory).
    """
    try:
        rclone.check_installed()
    except rclone.RcloneError as exc:
        raise click.ClickException(str(exc)) from exc

    remote, path = _parse_remote_path(remote_path)
    manifest = Manifest()

    # Batch mode: path ends with /
    if path.endswith("/") or include_pattern or recursive:
        _pull_batch(
            remote,
            path,
            local_dest,
            manifest,
            force,
            include_pattern,
            recursive,
        )
        return

    # Single file mode
    click.echo(f"Fetching metadata for {remote_path}...")
    try:
        metadata = _get_remote_metadata(remote_path)
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Failed to get metadata: {exc.stderr}") from exc

    dest_dir = Path(local_dest) if local_dest else Path.cwd()
    _pull_single_file(remote, path, metadata, dest_dir, manifest, force)


def _pull_batch(
    remote: str,
    path: str,
    local_dest: str | None,
    manifest: Manifest,
    force: bool,
    include_pattern: str | None,
    recursive: bool,
) -> None:
    """Pull multiple files from a remote folder."""
    remote_path = f"{remote}:{path}"
    click.echo(f"Listing files in {remote_path}...")

    try:
        items = rclone.lsjson(remote_path, with_hash=True, recursive=recursive)
    except rclone.RcloneError as exc:
        raise click.ClickException(f"Failed to list files: {exc.stderr}") from exc

    # Filter out directories
    files = [item for item in items if not item.get("IsDir", False)]

    if not files:
        click.echo("No files found.")
        return

    # Apply include filter
    if include_pattern:
        files = [f for f in files if fnmatch.fnmatch(f["Name"], include_pattern)]
        if not files:
            click.echo(f"No files matching '{include_pattern}'.")
            return

    click.echo(f"Found {len(files)} file(s) to pull.")
    dest_base = Path(local_dest) if local_dest else Path.cwd()
    dest_base.mkdir(parents=True, exist_ok=True)

    pulled = 0
    for item in files:
        item_path = item.get("Path", item["Name"])
        full_path = f"{path}{item_path}" if path else item_path

        # Mirror subdirectory structure
        relative = Path(item_path)
        if relative.parent != Path():
            file_dest = dest_base / relative.parent
            file_dest.mkdir(parents=True, exist_ok=True)
        else:
            file_dest = dest_base

        try:
            _pull_single_file(remote, full_path, item, file_dest, manifest, force)
            pulled += 1
        except click.ClickException as exc:
            click.echo(f"Error pulling {item_path}: {exc.message}")

    click.echo(f"\nPulled {pulled}/{len(files)} file(s).")
