---
name: pr-video-receipts
description: >
  Set up agentic video receipts on pull requests — Playwright `page.screencast`
  recordings of smoke tests, converted to mp4, uploaded as GitHub draft release
  assets, and embedded inline in PR comments. Use when the user says "set up
  agentic video receipts", "set up video recordings on PRs", "set up video
  receipts on PRs", or "use playwright to set up video recordings on PRs".
  Requires a Playwright MCP server (e.g. `@playwright/mcp`) with the `devtools`
  capability enabled, plus `ffmpeg` and an authenticated `gh` CLI.
---

# Agentic Video Receipts on PRs

Record a `.webm` of an agent-driven browser test via Playwright's `page.screencast` API, convert to `.mp4` for inline playback, upload as a GitHub draft release asset, embed the URL in a PR comment, and garbage-collect the draft on PR close. The result is a short video artifact that reviewers can watch instead of mentally simulating a diff.

Terminology: Playwright 1.59 coined **"agentic video receipts"**. Cursor Cloud Agents (Feb 2026) shipped the same idea under "Cloud Agents with Computer Use".

## Two phases

When the user invokes one of the trigger phrases, run the **Per-repo setup** below. When a smoke-test skill is actually recording, follow **Per-smoke-test usage**.

## Per-repo setup

Three changes. All idempotent.

### 1. `.mcp.json` — enable the `devtools` capability

Edit the repo's `.mcp.json` (or `~/.mcp.json`) and append `--caps=devtools` to the args of whichever Playwright MCP server the smoke test uses. Without this flag, `browser_start_video` / `browser_stop_video` are not registered as tools.

Example (headed under xvfb):

```json
"playwright-headed": {
  "command": "xvfb-run",
  "args": ["-a", "--server-args=-screen 0 1920x1080x24", "npx", "@playwright/mcp@latest", "--caps=devtools"]
}
```

Example (plain):

```json
"playwright": {
  "command": "npx",
  "args": ["@playwright/mcp@latest", "--caps=devtools"]
}
```

If multiple Playwright MCP servers are configured (e.g. `playwright-headed` and `playwright`), add the flag to each one the smoke test invokes.

### 2. `.github/workflows/playwright-pr-video-cleanup.yml` — cleanup workflow

Create this workflow verbatim. It runs on every PR close (merged or not) and deletes the PR's draft video release if one exists.

```yaml
name: Playwright PR video cleanup

on:
  pull_request:
    types: [closed]

permissions:
  contents: write

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Delete draft video release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR: ${{ github.event.pull_request.number }}
          REPO: ${{ github.repository }}
        run: |
          tag="pr-${PR}-videos"
          if gh release view "$tag" --repo "$REPO" >/dev/null 2>&1; then
            gh release delete "$tag" --repo "$REPO" --yes
            echo "Deleted $tag"
          else
            echo "No release $tag found"
          fi
```

The workflow uses the default `GITHUB_TOKEN`; `permissions: contents: write` is required for `gh release delete`.

### 3. Verify `ffmpeg`

Needed to convert `.webm` → `.mp4` (GitHub PR comments render `.mp4` inline; `.webm` shows up as a download link only). Check with `ffmpeg -version`. Install via `apt install ffmpeg` or `brew install ffmpeg` if missing.

## Per-smoke-test usage

Use this inside an agent-driven smoke test (for example, a `preview-smoke-test` style skill that runs against a deployed PR preview env). All MCP tool names below use the `playwright-headed` server as an example — substitute the server name actually configured in `.mcp.json`.

### Start recording

Right after the first `browser_navigate`, call:

```
mcp__playwright-headed__browser_start_video
  filename: smoke-pr-<N>.webm
```

A bare filename resolves relative to the MCP's output dir (default `.playwright-mcp/` in cwd). Pass an absolute path to write elsewhere.

Optional — add chapter markers so the reviewer can scrub:

```
mcp__playwright-headed__browser_run_code
  code: async page => { await page.screencast.showChapter("Selecting medication", { duration: 2000 }); }
```

Optional — annotate actions on-screen:

```
mcp__playwright-headed__browser_run_code
  code: async page => { await page.screencast.showActions({ position: "top-right" }); }
```

### Drive the test as normal

No changes to the rest of the smoke test. Click, fill, navigate, assert.

### Stop recording

After the last assertion:

```
mcp__playwright-headed__browser_stop_video
```

The tool response reports the output path.

### Convert, upload, comment

Only run this block if the smoke test **passed**. On failure, skip the upload entirely — no receipt means no false signal on the PR.

```bash
PR=<N>
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
WEBM=.playwright-mcp/smoke-pr-${PR}.webm
MP4=smoke-pr-${PR}.mp4
TAG="pr-${PR}-videos"

ffmpeg -y -i "$WEBM" -c:v libx264 -preset fast -crf 28 -movflags +faststart "$MP4"

gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1 \
  || gh release create "$TAG" --repo "$REPO" --draft --title "PR #${PR} video receipts" --notes ""

gh release upload "$TAG" --repo "$REPO" "$MP4" --clobber

gh api "repos/${REPO}/issues/${PR}/comments" \
  --method POST \
  -f body="Smoke test passed. Video receipt:

https://github.com/${REPO}/releases/download/${TAG}/${MP4}"
```

The draft release is invisible in the public Releases tab and gets deleted by the cleanup workflow when the PR closes.

## Fallback — `browser_run_code` + `page.screencast`

If `--caps=devtools` cannot be enabled (older MCP, no write access to `.mcp.json`), call `page.screencast` directly via `browser_run_code`. Same end artifact, different tool surface:

```
# start
mcp__playwright-headed__browser_run_code
  code: async page => { await page.screencast.start({ path: "/tmp/smoke-pr-<N>.webm", size: { width: 1280, height: 720 } }); }

# stop
mcp__playwright-headed__browser_run_code
  code: async page => { await page.screencast.stop(); }
```

Convert / upload / comment is identical.

## Requirements

| Component | Minimum version | Why |
|---|---|---|
| `@playwright/test` | 1.59 | `page.screencast` API |
| `@playwright/mcp` | 0.0.70 | `--caps=devtools` |
| `ffmpeg` | any | webm → mp4 conversion |
| `gh` CLI | authenticated, `contents: write` scope | release upload + PR comment |

## Why draft releases, not inline comment upload

GitHub's REST API does not support programmatic file upload to PR/issue comments. The web-UI drag-and-drop feature produces `user-images.githubusercontent.com` URLs via a session-cookie endpoint that isn't exposed by `gh` or the REST API. Draft releases are the supported automation path — invisible in the public Releases list, accessible at stable URLs, rendered inline in PR comments (for `.mp4` / `.gif`), and disposable via the cleanup workflow.
