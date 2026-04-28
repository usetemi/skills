# Google Drive Skill Setup Guide

## 1. Install rclone

```bash
# Ubuntu/Debian
sudo apt install rclone

# macOS
brew install rclone

# Or from rclone.org
curl https://rclone.org/install.sh | sudo bash
```

Verify: `rclone version`

## 2. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 3. Run gdrive auth

```bash
uv run --project /path/to/skills/google-drive gdrive auth
```

### What happens during auth

1. **Base remote creation**: rclone creates a Google Drive remote with `scope=drive` (full access). This triggers Google OAuth in your browser.

2. **Shared drive enumeration**: The tool runs `rclone backend drives <base>:` to list all shared drives your account can access.

3. **Drive selection**: You pick which shared drives to enable. Each gets its own rclone remote with the `team_drive` parameter set.

4. **Config saved**: Remote metadata is written to `~/.config/gdrive/config.json`.

### Headless machines (SSH)

On a machine without a browser (like a remote VM):

**Option A: SSH tunnel (recommended)**

```bash
# On your local machine, open a tunnel:
ssh -L 53682:localhost:53682 user@remote-host

# Then on the remote host, run:
uv run --project /path/to/skills/google-drive gdrive auth
```

When rclone prints the auth URL, open it in your local browser. The tunnel forwards the OAuth callback.

**Option B: rclone authorize**

```bash
# On a machine WITH a browser:
rclone authorize drive

# This prints a token JSON blob. Copy it.
# Then on the remote machine, run rclone config manually:
rclone config
# When prompted for the token, paste it.
# Then run gdrive auth to set up shared drives.
```

## 4. Verify setup

```bash
# List configured remotes
uv run --project /path/to/skills/google-drive gdrive ls

# List files on a shared drive
uv run --project /path/to/skills/google-drive gdrive ls mydrive:
```

## 5. GCP Project (optional)

rclone includes built-in Google API credentials that work out of the box. For higher API quotas or organizational requirements, you can create your own:

1. Go to https://console.cloud.google.com/
2. Create a project or select an existing one
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials (Desktop application)
5. During `rclone config`, enter your client_id and client_secret when prompted

This is not required for normal use.

## Shared drive remote naming

The auth wizard suggests remote names based on the drive name (lowercased, hyphenated). You can customize during setup. Examples:

| Drive Name | Suggested Remote |
|---|---|
| Engineering | engineering |
| Marketing Drive | marketing-drive |
| Founder Drive | founder-drive |

## Troubleshooting

**"Token has been expired or revoked"** -- Re-run `gdrive auth` to refresh credentials.

**"Rate limit exceeded"** -- rclone handles retry automatically. For bulk operations, add `--tpslimit 2` to slow requests.

**Shared drive not listed** -- Verify you have access in the Google Drive web UI. The base remote needs `scope=drive` (not `drive.readonly`).

**Multiple Google accounts** -- Create separate base remotes for each account: run `rclone config` to add a second drive-type remote, then re-run `gdrive auth`.
