# Setup Guide

## Prerequisites

1. **uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Project sync**: `uv sync --project <path-to-skills/google-search-console>`

## Google Cloud Platform Setup

### 1. Create a GCP Project

1. Go to https://console.cloud.google.com/
2. Create a new project (or select an existing one)
3. Note the project ID

### 2. Enable APIs

Enable these APIs in your project:

- **Google Search Console API**: https://console.cloud.google.com/apis/library/searchconsole.googleapis.com
- **PageSpeed Insights API** (optional): https://console.cloud.google.com/apis/library/pagespeedonline.googleapis.com

### 3. Create OAuth 2.0 Credentials

1. Go to https://console.cloud.google.com/apis/credentials
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User type: External (or Internal for Workspace)
   - App name: "GSC CLI" (or any name)
   - Scopes: Add `https://www.googleapis.com/auth/webmasters`
   - Test users: Add your Google account email
4. Application type: **Desktop application**
5. Click "Create"
6. Download the JSON file (it will be named like `client_secret_XXXXX.json`)

### 4. Authenticate

```bash
uv run --project <path> gsc auth login --client-secret /path/to/client_secret.json
```

This opens a browser for OAuth consent. After authorizing, credentials are stored at:
`~/.config/gsc/credentials.json`

### 5. Headless Machine Setup

On a headless machine, the OAuth callback can't reach a local browser without help. Open a reverse SSH tunnel before running auth:

```bash
# On your local machine:
ssh -L 8085:localhost:8085 <remote-host>

# Then on the remote host, run gsc auth login
# and open the printed URL on your local machine
```

### 6. Verify

```bash
uv run --project <path> gsc auth status
uv run --project <path> gsc sites list
```

## PageSpeed Insights API Key

PageSpeed Insights uses an API key (not OAuth).

1. Go to https://console.cloud.google.com/apis/credentials
2. Click "Create Credentials" > "API key"
3. Restrict the key to "PageSpeed Insights API" under API restrictions
4. Store it:

```bash
uv run --project <path> gsc config set pagespeed-api-key <your-key>
```

5. Verify:

```bash
uv run --project <path> gsc pagespeed https://example.com
```

## API Quotas

| API | Default Quota | Unit |
|-----|--------------|------|
| Search Console API | 1,200 queries/min | Per project |
| Search Analytics query | 200 queries/min | Per site |
| URL Inspection | 600 inspections/day | Per property |
| PageSpeed Insights | 25,000 queries/day (with key) | Per project |
| PageSpeed Insights | 60 queries/min | Per project |
