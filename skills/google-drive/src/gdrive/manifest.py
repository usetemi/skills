"""Manifest for tracking synced files between local and Google Drive."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


def get_config_dir() -> Path:
    """Resolve the gdrive config directory, honoring GDRIVE_CONFIG_DIR override."""
    override = os.environ.get("GDRIVE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "skills" / "gdrive"


def legacy_config_dir() -> Path | None:
    """Return the pre-migration `~/.config/gdrive/` path if it exists and differs from the current dir."""
    legacy = Path.home() / ".config" / "gdrive"
    if legacy != get_config_dir() and legacy.exists():
        return legacy
    return None


CONFIG_DIR = get_config_dir()
MANIFEST_PATH = CONFIG_DIR / "manifest.json"

# Google Workspace MIME types and their export extensions
GOOGLE_MIME_TYPES = {
    "application/vnd.google-apps.document": ".docx",
    "application/vnd.google-apps.spreadsheet": ".xlsx",
    "application/vnd.google-apps.presentation": ".pptx",
}

# Reverse: extension -> import MIME type format string for rclone
IMPORT_FORMATS = {
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
}

# Reverse: export MIME type -> native Google MIME type
# rclone lsjson reports native Google docs with their *export* MIME type,
# not their native type. Use Size == -1 to detect native docs, then map back.
_OOXML_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_OOXML_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_OOXML_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
EXPORT_TO_NATIVE_MIME = {
    _OOXML_DOCX: "application/vnd.google-apps.document",
    _OOXML_XLSX: "application/vnd.google-apps.spreadsheet",
    _OOXML_PPTX: "application/vnd.google-apps.presentation",
}


@dataclass
class ManifestEntry:
    """A tracked file in the manifest."""

    drive_id: str  # Google Drive file ID
    remote: str  # rclone remote name (e.g. "mydrive")
    remote_path: str  # path on remote (e.g. "folder/doc.docx")
    original_mime_type: str  # MIME type from Google Drive
    local_md5: str  # MD5 hash of local file at last sync
    remote_md5: str  # MD5 hash from remote at last sync
    last_synced: str  # ISO timestamp of last sync
    local_mtime_at_sync: str  # ISO timestamp of local file mtime at sync
    remote_mtime_at_sync: str  # ISO timestamp of remote file mtime at sync


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def compute_md5(path: Path) -> str:
    """Compute MD5 hash of a local file.

    Used for content fingerprinting to compare with rclone's md5 — not security.
    """
    hasher = hashlib.md5()  # noqa: S324
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _local_mtime_iso(path: Path) -> str:
    """Get local file mtime as ISO string."""
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=UTC).isoformat()


class Manifest:
    """Manages the manifest file. Keys are absolute local paths."""

    def __init__(self, path: Path = MANIFEST_PATH):
        self.path = path
        self._entries: dict[str, ManifestEntry] = {}
        self.load()

    def load(self) -> None:
        """Load manifest from disk."""
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self._entries = {key: ManifestEntry(**val) for key, val in data.items()}
        else:
            self._entries = {}

    def save(self) -> None:
        """Write manifest to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {key: asdict(entry) for key, entry in self._entries.items()}
        self.path.write_text(json.dumps(data, indent=2) + "\n")

    def get(self, local_path: Path) -> ManifestEntry | None:
        """Look up a manifest entry by local path."""
        key = str(local_path.resolve())
        return self._entries.get(key)

    def upsert(self, local_path: Path, entry: ManifestEntry) -> None:
        """Add or update a manifest entry."""
        key = str(local_path.resolve())
        self._entries[key] = entry
        self.save()

    def remove(self, local_path: Path) -> None:
        """Remove a manifest entry."""
        key = str(local_path.resolve())
        self._entries.pop(key, None)
        self.save()

    def all_entries(self) -> dict[str, ManifestEntry]:
        """Return all entries as {absolute_path_str: entry}."""
        return dict(self._entries)

    def find_by_md5(self, md5: str) -> list[tuple[str, ManifestEntry]]:
        """Find entries matching a local MD5 hash (for moved file detection)."""
        return [
            (key, entry)
            for key, entry in self._entries.items()
            if entry.local_md5 == md5
        ]

    def find_by_remote(
        self, remote: str, remote_path: str
    ) -> list[tuple[str, ManifestEntry]]:
        """Find entries matching a remote + path."""
        return [
            (key, entry)
            for key, entry in self._entries.items()
            if entry.remote == remote and entry.remote_path == remote_path
        ]
