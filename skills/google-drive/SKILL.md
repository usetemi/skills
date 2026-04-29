---
name: google-drive
description: Manage Google Drive files with manifest-tracked push/pull workflows via rclone. Use when the user needs to download, upload, list, or manage files on Google Drive shared drives.
---

# Google Drive

## Architecture

`gdrive` is a Python orchestrator CLI that uses **rclone** as its transport layer. rclone handles all Google Drive API communication -- OAuth, file transfers, format conversion, retry/rate-limiting. `gdrive` adds the intelligence on top: a manifest that tracks synced files, format-aware push/pull that re-imports Google Docs as native format, conflict detection, and multi-remote management. Think of rclone as the engine and gdrive as the driver.

Designed for a pull-edit-push cycle, especially paired with Anthropic's official document skills for reading and editing office files: `docx`, `xlsx`, `pptx`, and `pdf` (from `https://github.com/anthropics/skills`).

## Before First Use

Before running any gdrive command, ensure dependencies are available. Check and install silently -- don't ask the user for permission to install these.

1. **rclone**: Run `which rclone`. If missing, install it:
   - Linux: `sudo apt install -y rclone` (or `curl https://rclone.org/install.sh | sudo bash`)
   - macOS: `brew install rclone`
2. **uv**: Run `which uv`. If missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **Project sync**: Run `uv sync --project <skill-dir>` to ensure the venv and deps are ready.
4. **Auth**: Run `gdrive ls`. If it shows "No remotes configured", the user needs to run `gdrive auth setup` (interactive -- tell the user what's about to happen and that they'll need to complete OAuth in a browser).

For headless machines (no `$DISPLAY`), instruct the user to set up an SSH tunnel first:
```
ssh -L 53682:localhost:53682 <remote-host>
```
Then run `gdrive auth setup` on the remote host and open the printed URL on their local machine.

See `references/setup.md` for the full setup guide.

## Invocation

All commands use this pattern:

```bash
uv run --project /path/to/skills/google-drive gdrive <command> [args]
```

For brevity, examples below use `gdrive` directly.

## Commands

### auth -- Manage remotes

```bash
gdrive auth setup     # interactive: configure rclone remotes (run once per machine)
gdrive auth status    # report which remotes are configured and authenticate
gdrive auth logout    # forget gdrive's remote registrations (rclone state stays)
```

### ls -- List drives or files

```bash
# List configured remotes
gdrive ls

# List files at a remote path
gdrive ls mydrive:
gdrive ls mydrive:Projects/2025/

# Detailed listing
gdrive ls -l mydrive:Reports/

# Recursive listing
gdrive ls -R mydrive:Templates/
```

### cp -- Copy files on remote

```bash
gdrive cp mydrive:Reports/Q4-Summary.docx mydrive:Archive/Q4-Summary.docx
```

Server-side copy. Works across different remotes (unlike mv). Does not update the manifest.

### pull -- Download files

```bash
# Download to current directory
gdrive pull mydrive:Reports/Q4-Summary

# Download to specific location
gdrive pull mydrive:Reports/Q4-Summary ./reports/

# Force overwrite local changes
gdrive pull -f mydrive:Reports/Q4-Summary

# Pull all files in a folder
gdrive pull mydrive:Reports/

# Pull to a specific local directory
gdrive pull mydrive:Reports/ ./local-reports/

# Filter by glob pattern
gdrive pull mydrive:Reports/ --include "*.docx"

# Recursive pull (includes subdirectories)
gdrive pull -R mydrive:Projects/
```

Google Docs/Sheets/Slides are automatically exported:

| Google Format | Exported As |
|---|---|
| Google Doc | .docx |
| Google Sheet | .xlsx |
| Google Slides | .pptx |

The manifest tracks the original MIME type so push can re-import correctly.

### push -- Upload files

```bash
# Push a tracked file (uses manifest for destination)
gdrive push ./Q4-Summary.docx

# Push to explicit destination
gdrive push ./report.docx mydrive:Reports/Q4-Summary.docx

# Force overwrite
gdrive push -f ./Q4-Summary.docx

# Push all locally-modified tracked files
gdrive push --all

# Filter batch push by remote
gdrive push --all -r mydrive

# Force batch push (skip conflict checks)
gdrive push --all -f
```

Format-aware upload: if a file was originally a Google Doc (per manifest), it's automatically re-imported as a Google Doc on push. For new files, you'll be prompted.

Conflict detection: if the remote file changed since last sync, push prompts before overwriting. Use `-f` to skip.

### status -- Check sync state

```bash
# Show all tracked files
gdrive status

# Filter by remote
gdrive status -r mydrive
```

Categories:
- **Up to date** -- local matches last sync
- **Local changes** -- local file modified since last pull
- **Missing locally** -- tracked file deleted or moved locally

### mkdir -- Create directories

```bash
gdrive mkdir mydrive:Projects/2025/NewProject
```

### mv -- Move files on remote

```bash
gdrive mv mydrive:old/path.docx mydrive:new/path.docx
```

Updates manifest entries referencing the moved path.

### search -- Find files

```bash
# Search all configured remotes
gdrive search budget

# Search a specific remote
gdrive search mydrive: budget report
```

Uses Google Drive's name-contains query. Shows results with file type, date, and web link.

### rm -- Delete remote files

```bash
gdrive rm mydrive:path/to/old-file.docx
gdrive rm -f mydrive:path/to/old-file.docx  # skip confirmation
```

Deletes the remote file and cleans up any matching manifest entries.

### untrack -- Remove from manifest

```bash
gdrive untrack ./local-file.docx
```

Removes the file from manifest tracking without deleting anything locally or on the remote.

### doctor -- Health check

```bash
gdrive doctor
```

Validates: rclone installed, config file exists, all remotes have working tokens, no orphaned rclone remotes, all manifest entries have existing local files.

### open -- Get web URL

```bash
gdrive open mydrive:Reports/Q4-Summary
```

Prints the Google Drive web URL for the file.

### link -- Get shareable link

```bash
gdrive link mydrive:Reports/Q4-Summary
```

Prints a shareable Google Drive link for the file.

### share -- Set permissions

```bash
# Share with a user (default: reader)
gdrive share mydrive:Reports/Q4-Summary.docx user@example.com

# Share as writer
gdrive share mydrive:Reports/Q4-Summary.docx user@example.com --role writer

# Share as commenter
gdrive share mydrive:Reports/Q4-Summary.docx user@example.com --role commenter

# Share with anyone who has the link
gdrive share mydrive:Reports/Q4-Summary.docx --anyone
```

Calls the Google Drive API directly (rclone has no sharing support). Uses the OAuth token from rclone config.

## Workflow: Pull-Edit-Push

The primary workflow for editing Google Drive documents:

```bash
# 1. Pull the document (exports Google Doc as .docx)
gdrive pull mydrive:Proposals/Client-Brief

# 2. Edit with a document skill
# (use docx, xlsx, or pptx skill to read/modify the file)

# 3. Check what changed
gdrive status

# 4. Push back (re-imports as Google Doc)
gdrive push ./Client-Brief.docx
```

**Mixed editing (agent XML + user in Google Docs):**
If the user edited the doc directly in Google Docs between sessions, the pulled version may have different structure (reordered sections, removed content). Always re-inspect with `pandoc` before editing XML. Don't assume previous XML line numbers or structure.

## Manifest

The manifest at `~/.config/skills/gdrive/manifest.json` tracks:
- Remote location and Google Drive file ID
- Original MIME type (for format-aware re-import)
- MD5 hashes at last sync (local and remote)
- Timestamps for change detection

The manifest enables:
- Pushing tracked files without specifying the remote path
- Detecting local modifications via MD5 comparison
- Re-importing exported Google Docs as native format on push
- Detecting moved files by MD5 hash

## Remote Naming Convention

Shared drives are configured as separate rclone remotes. Pick a short prefix per drive so commands stay readable, e.g.:

- `mydrive` -- a personal My Drive
- `team-engineering` -- an engineering shared drive
- `team-design` -- a design shared drive

Lowercased, hyphenated names work best. The `auth` wizard suggests names based on each drive's title and lets you override.

## Troubleshooting

**"File not found" on pull** -- Check the path with `gdrive ls remote:path/` first. Google Docs don't have file extensions on the remote.

**Push doesn't re-import as Google Doc** -- Ensure the file was originally pulled (has manifest entry with Google MIME type). For new files, use `--drive-import-formats` flag.


**Manifest out of sync** -- Run `gdrive untrack` on stale entries, or delete `~/.config/skills/gdrive/manifest.json` to reset.

**General setup issues** -- Run `gdrive doctor` to diagnose problems with rclone, remotes, and manifest health.

## Configuration Files

- **Manifest**: `~/.config/skills/gdrive/manifest.json`
- **Config**: `~/.config/skills/gdrive/config.json`
- **rclone config**: `~/.config/rclone/rclone.conf` (managed by rclone)
- Override the gdrive config dir with `GDRIVE_CONFIG_DIR=/path/to/dir`

### Migrating from earlier versions

If upgrading from a build that stored config at `~/.config/gdrive/`, run `gdrive config migrate --apply` to move the manifest and config to the new location. `gdrive auth status` emits a `deprecation_warning` until the migration runs.

The interactive wizard previously invoked as `gdrive auth` is now `gdrive auth setup`. The bare `gdrive auth` is now a command group containing `setup`, `status`, and `logout`.

Add to `.gitignore` in any repo using this skill:
```
.gdrive-manifest.json
```
