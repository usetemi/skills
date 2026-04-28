# ga4 Setup

Everything needed to go from a clean machine to `ga4 doctor` all-green.

## Why OAuth instead of ADC

`ga4` uses OAuth user credentials only. It intentionally does NOT support `gcloud auth application-default login`. Reason: Google has deprecated the analytics scopes (`analytics.readonly`, `analytics.edit`, `analytics.manage.users`) for gcloud's default OAuth client ID, and the "fix" is to bring your own client ID anyway — which is exactly what OAuth user flow does, just without the extra gcloud indirection. Keeping one path keeps the surface small.

## Prerequisites

- `uv` on `$PATH` — `curl -LsSf https://astral.sh/uv/install.sh | sh` if missing.
- A Google Cloud project you control (to create an OAuth client in).
- A GA4 account + property whose access you can grant to your Google account (or ask someone with Administrator on the GA side).

## 1. GCP project + enable the two GA4 APIs

Use any GCP project you control, or create a new one dedicated to analytics. Open the Google Cloud Console and confirm the target project is selected.

Enable both APIs:

- **Google Analytics Data API** — `analyticsdata.googleapis.com` — reporting
- **Google Analytics Admin API** — `analyticsadmin.googleapis.com` — configuration

Direct links (replace `YOUR_PROJECT`):

- https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com?project=YOUR_PROJECT
- https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com?project=YOUR_PROJECT

Click **Enable** on each. No billing required for the APIs themselves.

## 2. Create a Desktop OAuth client

1. In the Cloud Console, go to **APIs & Services → Credentials**.
2. **Create Credentials → OAuth client ID**.
3. If prompted, configure the OAuth consent screen. Choose **Internal** if only Workspace users in your own org need to auth, or **External** if any Google account needs to auth. Minimum fields are app name + support email.
4. Back on the Credentials page: **Create Credentials → OAuth client ID → Desktop app**. Name it anything (e.g., `ga4 CLI`).
5. **Download JSON** — save to a known path. Do NOT commit to git. Recommended path: `~/.config/ga4/client_secret.json`.

## 3. Log in

```bash
ga4 auth login --client-secret ~/.config/ga4/client_secret.json
```

Default scopes are `analytics.readonly`, `analytics.edit`, `analytics.manage.users`. Pass `--scope` (repeatable) to override. For advanced endpoints you need to include:

- `https://www.googleapis.com/auth/analytics.provision` for `ga4 admin accounts provision-ticket`
- `https://www.googleapis.com/auth/analytics.user.deletion` for `ga4 admin properties submit-user-deletion`

A browser opens for consent. On a headless machine, open an SSH tunnel before running auth so the OAuth callback can reach a local browser:

```bash
ssh -L 8086:localhost:8086 <this-host>
```

Then run the auth command on the remote host and open the printed URL on a machine with a browser.

Credentials land at `~/.config/ga4/credentials.json` and auto-refresh via the stored refresh token.

## 4. Grant GA access to the Google account you just authed with

1. Open https://analytics.google.com/ and pick the account.
2. Click the gear (Admin) at bottom-left.
3. Under the Account column: **Access Management** → **+** → **Add users**.
4. Enter the email of the Google account you used in step 3. Choose a role:
   - **Viewer** — run reports, read config. Enough for read-only usage.
   - **Analyst** — viewer + can edit some shared assets.
   - **Editor** — read + write all config. Required for any `admin … create/update/delete`.
   - **Administrator** — editor + user management. Required for `access-bindings *`.
5. Save.

Granting at the account level applies to all properties under it. Grant at property level for tighter scoping.

## 5. Verify

```bash
uv run --project /abs/path/to/skills/google-analytics ga4 doctor
```

Expected output shape:

```
  OK    config dir writable (~/.config/ga4)
  OK    OAuth credentials present (~/.config/ga4/credentials.json)
  OK    resolved credentials (Credentials)
  OK    Admin API reachable (N account(s) visible)
All checks passed.
```

If `Admin API reachable (0 account(s) visible)` — credentials work but your Google account has no GA access; revisit step 4.

If `resolved credentials` fails with "insufficient_scope" — the token you got in step 3 didn't include the scope this command needs. Re-run `ga4 auth login --client-secret … --scope <needed-scope>`.

## 6. (Optional) Set a default property

Skip the `-p/--property` flag on every command:

```bash
ga4 config set-property 123456789
```

Accepts both numeric (`123456789`) and resource-name (`properties/123456789`) forms; stored as canonical `properties/<id>`.

## Common setup errors

- **`The OAuth client was not found`** — The `client_secret.json` path is wrong, or the OAuth client was deleted from GCP. Re-download or re-create.
- **`Access blocked: <app> has not completed the Google verification process`** — Your OAuth consent screen is in "testing" mode and your Google account isn't on the test-users list. In Cloud Console → OAuth consent screen → add yourself as a test user, OR publish the app (if external).
- **`403 Request had insufficient authentication scopes`** — The stored token doesn't have the scope this command needs. `ga4 auth login --client-secret … --scope <missing-scope>` (repeatable) and re-try.
- **`404 Method not found`** on an alpha endpoint — Your `google-analytics-admin` / `google-analytics-data` version may be too old. `uv sync` to pin to the lockfile, or bump the dep floor in `pyproject.toml`.
- **`User is not authorized to access this resource`** — You authed correctly but GA hasn't granted your account access. Revisit step 4.

## Rotating credentials

- **Revoke a single token**: `ga4 auth logout` removes the local file. The refresh token remains valid on Google's side — revoke it explicitly at https://myaccount.google.com/permissions if you want to kill it everywhere.
- **Move to a new machine**: copy `~/.config/ga4/credentials.json` to the new box (and the `client_secret.json` if you want to be able to re-auth without re-creating the client). Refresh tokens work cross-machine.
- **Rotate the OAuth client**: create a new Desktop client, `ga4 auth logout`, `ga4 auth login --client-secret <new.json>`. Delete the old client in GCP afterwards.
