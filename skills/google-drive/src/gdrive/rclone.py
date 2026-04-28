"""Subprocess wrapper for rclone CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal, overload


class RcloneError(Exception):
    """Error running rclone command."""

    def __init__(self, args: list[str], returncode: int, stderr: str):
        self.args_list = args
        self.returncode = returncode
        self.stderr = stderr
        cmd = " ".join(args)
        super().__init__(f"rclone failed (exit {returncode}): {cmd}\n{stderr}")


def check_installed() -> Path:
    """Verify rclone is on PATH. Returns path to binary."""
    path = shutil.which("rclone")
    if path is None:
        raise RcloneError(
            ["rclone"],
            127,
            "rclone not found on PATH. Install it: https://rclone.org/install/",
        )
    return Path(path)


@overload
def run(*args: str, json_output: Literal[True], check: bool = True) -> Any: ...
@overload
def run(*args: str, json_output: Literal[False] = ..., check: bool = True) -> str: ...


def run(
    *args: str,
    json_output: bool = False,
    check: bool = True,
) -> str | Any:
    """Run an rclone command and return output.

    If json_output=True, parses stdout as JSON and returns the parsed object.
    Otherwise returns raw stdout string.
    """
    check_installed()
    cmd = ["rclone", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RcloneError(cmd, result.returncode, result.stderr.strip())
    if json_output:
        return json.loads(result.stdout)
    return result.stdout


def run_interactive(*args: str) -> int:
    """Run rclone with inherited stdin/stdout for interactive commands.

    Returns the exit code.
    """
    check_installed()
    cmd = ["rclone", *args]
    result = subprocess.run(cmd)
    return result.returncode


# --- High-level helpers ---


def lsjson(
    remote_path: str,
    *,
    hash: bool = False,
    recursive: bool = False,
) -> list[dict[str, Any]]:
    """List files/dirs as JSON objects."""
    args = ["lsjson", remote_path]
    if hash:
        args.append("--hash")
    if recursive:
        args.append("-R")
    return run(*args, json_output=True)


def lsf(
    remote_path: str,
    *,
    recursive: bool = False,
    long: bool = False,
    dirs_only: bool = False,
    files_only: bool = False,
) -> str:
    """List files in parseable format."""
    args = ["lsf", remote_path]
    if recursive:
        args.append("-R")
    if long:
        args.append("--format=tsp")
        args.append("--separator=\t")
    if dirs_only:
        args.append("--dirs-only")
    if files_only:
        args.append("--files-only")
    return run(*args)


def backend_drives(remote: str) -> list[dict[str, Any]]:
    """List shared drives accessible via a drive-type remote.

    Returns list of dicts with 'id', 'kind', 'name' keys.
    """
    return run("backend", "drives", f"{remote}:", json_output=True)


def copyto(
    src: str,
    dst: str,
    *,
    extra_args: list[str] | None = None,
) -> None:
    """Copy a single file from src to dst."""
    args = ["copyto", src, dst]
    if extra_args:
        args.extend(extra_args)
    run(*args)


def moveto(src: str, dst: str) -> None:
    """Move a single file from src to dst."""
    run("moveto", src, dst)


def mkdir(remote_path: str) -> None:
    """Create a directory on remote."""
    run("mkdir", remote_path)


def config_create(name: str, remote_type: str, **params: str) -> None:
    """Create a new rclone remote non-interactively."""
    args = ["config", "create", name, remote_type]
    for key, value in params.items():
        args.append(f"{key}={value}")
    run(*args)


def config_dump() -> dict[str, Any]:
    """Dump entire rclone config as JSON."""
    return run("config", "dump", json_output=True)


def config_show(remote: str) -> str:
    """Show config for a specific remote."""
    return run("config", "show", remote)


def listremotes() -> list[str]:
    """List all configured rclone remotes.

    Returns remote names including the trailing colon.
    """
    output = run("listremotes")
    return [line.strip() for line in output.strip().splitlines() if line.strip()]


def config_delete(name: str) -> None:
    """Delete a remote from rclone config."""
    run("config", "delete", name)


def config_reconnect_interactive(name: str) -> int:
    """Re-authenticate an existing remote (interactive OAuth).

    Returns exit code. The user must complete OAuth in a browser.
    """
    return run_interactive("config", "reconnect", f"{name}:")


def about(remote: str) -> str:
    """Get info about a remote (quick health check)."""
    return run("about", f"{remote}:")


def backend_query(remote: str, query: str) -> list[dict[str, Any]]:
    """Search files using Google Drive query language.

    Returns list of dicts with id, name, mimeType, modifiedTime,
    webViewLink, md5Checksum, size, parents.
    """
    return run("backend", "query", f"{remote}:", query, json_output=True)


def delete_file(remote_path: str) -> None:
    """Delete a single file on remote."""
    run("deletefile", remote_path)
