# Tailscale Automation And API

Docs: [trust credentials](https://tailscale.com/docs/reference/trust-credentials) (scope-to-endpoint source of truth).

## Credential Decision Path

1. Prefer workload identity federation (WIF) when the platform issues OIDC
   tokens (GitHub Actions, AWS, GCP, Terraform Cloud): no long-lived secret.
2. Otherwise an OAuth client secret: mints scoped tokens and auth keys on
   demand; does not expire until revoked.
3. A plain auth key only where neither works; keys last at most 90 days, so
   mint one at deploy time.
4. Tag every automation node and write policy against tags, not users.

## Auth Keys

- Expiry 1 to 90 days (default and maximum 90). One-off keys are revoked after
  first use; reusable keys are not. Keys are case-sensitive; you can revoke
  only your own.
- Revoking or expiring a key does not deauthorize nodes it registered; they
  stay until their node key expires or you delete them.
- `--auth-key`, `--id-token` and `--client-secret` accept a `file:` prefix
  (`--auth-key=file:/run/secrets/k`), keeping secrets out of shell history.
- Node-key expiry:
  [policy-security.md](policy-security.md#approval-key-expiry-and-identity-lifecycle).
  `--advertise-tags` (comma-separated, `tag:` optional) cannot remove tags from
  an auth-key device; mint a new key ([tags](policy-security.md#tags)).

## Ephemeral Nodes

- Removed automatically about 30 to 60 minutes after last activity; do not
  rely on that for teardown. `tailscale logout` removes one immediately; make
  it the last deploy or job step.
- `tailscaled --state=mem:` (1.22+) makes an ephemeral node; on exit (1.30+) it
  logs itself out.
- For many container replicas, use one reusable, ephemeral, tagged auth key;
  a node key baked into an image creates duplicate devices.

## OAuth Clients

- Token endpoint: `POST https://api.tailscale.com/api/v2/oauth/token`
  (client-credentials grant), optional space-delimited `scope` and `tags`
  params; `tags` applies only to tokens with `devices:core`, `auth_keys` or
  `all`. Send `Authorization: Bearer <token>`. Tokens last 1 hour, fixed.
- Clients must be owned by the tailnet, not a user. Use OAuth or WIF tokens,
  not user API keys, for automation.
- In `{tailnet}` API paths (base `https://api.tailscale.com/api/v2/`), `-`
  means the token's own tailnet. Prefer the Tailnet ID (Settings > General)
  over the legacy ID.
- Services API ([expose-services.md](expose-services.md)): `GET|PUT|DELETE
  /tailnet/{tailnet}/services/{name}`, list `.../services`, hosts
  `.../services/{name}/devices`, approval
  `.../services/{name}/device/{deviceId}/approved` (separate from advertising).
- An `auth_keys` client must have tags; every key it mints carries exactly
  those tags or tags they own. For several tags with one client, make an owner
  tag (`"tag:terraform-tag-owner": ["autogroup:admin"]`) the `tagOwners` owner
  of the others (`"tag:server": ["tag:terraform-tag-owner"]`) and give the
  client only the owner tag.
- `POST /api/v2/tailnet/-/keys` mints auth keys (`capabilities.devices.create`
  with `reusable`, `ephemeral`, `preauthorized`, `tags`; `expirySeconds`) and
  creates OAuth clients (`keyType:"client"`) and federated identities
  (`keyType:"federated"`).

### Scopes

- Granular scopes, each with a `:read` variant: `devices:core`,
  `devices:routes`, `devices:posture_attributes`, `auth_keys`, `policy_file`,
  `dns`, `users`, `webhooks`, `log_streaming`, `logs:configuration:read`,
  `logs:network`, `account_settings`, `feature_settings`, `api_access_tokens`,
  `oauth_keys`, `federated_keys`. Prefer them over `all`/`all:read`, which also
  cover future APIs. Legacy scopes (`acl`, `devices`, ...) still work.
- `policy_file:read` also needs `devices:core:read` and
  `devices:posture_attributes:read`; `policy_file` needs `devices:core:read`
  and `devices:posture_attributes`. `log_streaming` to a private endpoint also
  needs the device-invites scope (copy its name from the console's scope
  picker; the docs spell it inconsistently) and `policy_file`. `devices:core`
  and `auth_keys` require tags at creation.
- Revoking a credential revokes API tokens it minted, not nodes already
  registered with it; delete those. Token creation is logged in configuration
  audit logs with the Client ID as actor.

## Ephemeral Defaults For OAuth And WIF Registration

Nodes registered with an OAuth client secret (`--auth-key=<oauth-secret>`) or
WIF (`--client-id=...`) are ephemeral by default (`ephemeral=true`,
`preauthorized=false`) and tag-owned, so a long-lived tagged service (subnet
router, connector, Service host) is removed after going offline unless you
override. Quote the value so the shell keeps `&`:

```bash
tailscale up --auth-key='<oauth-secret>?ephemeral=false&preauthorized=true' \
  --advertise-tags=tag:router     # WIF: --client-id='<id>?ephemeral=false&...'
```

In containers, an OAuth secret in `TS_AUTHKEY` is ephemeral unless suffixed
`?ephemeral=false`. `--advertise-tags` is required with an OAuth client secret.

## Workload Identity Federation

Create federated identities on the Trust credentials page, via
`POST /api/v2/tailnet/-/keys` (`keyType:"federated"`, `issuer`, `subject`,
`customClaimRules`, `scopes`, `tags`), or with Terraform. The credential needs
`auth_keys`; `--advertise-tags` must match tags on the identity. Client ID and
Audience are not secrets. Source: tailscale.com/docs/features/workload-identity-federation

Two CLI shapes; do not combine `--audience` with `--id-token`.

```bash
# (a) You hold an OIDC JWT (not a Tailscale API token). Client 1.90.1+.
tailscale up --client-id=<id> --id-token=file:/run/secrets/oidc_jwt \
  --advertise-tags=tag:ci
# (b) The client discovers the platform token. Client 1.94.0+.
tailscale up --client-id=<id> --audience=<aud> --advertise-tags=tag:ci
```

- (b) works on AWS (IAM role must allow `sts:GetWebIdentityToken`; EC2, ECS,
  EKS), GCP (metadata server; GCE, GKE) and GitHub Actions
  (`permissions: id-token: write`). Elsewhere use (a).
- Container env vars are in [containers-tsnet.md](containers-tsnet.md).
  `TS_AUDIENCE` cannot combine with `TS_CLIENT_SECRET` or `TS_ID_TOKEN`;
  `TS_CLIENT_ID` alone works where the token auto-generates (GitHub Actions).
- Raw API: `POST https://api.tailscale.com/api/v2/oauth/token-exchange` with
  form fields `client_id` and `jwt`; the token is short-lived.
- Matching: `sub` and optional `customClaimRules` are the authorization
  boundary; any matching workload obtains the credential's scopes and tags, so
  use precise patterns (for GitHub, a specific repo and ref or environment).
  `*` matches any characters; everything else must match exactly. Nested
  claims use dots (`user.name`); keys with a period are double-quoted
  (`"open.id".username`).
- Debugging: the API error is generic (`Unauthorized. Visit ... for details`);
  the reason appears only on the federated identity's Trust credentials page,
  until a later exchange succeeds.

## GitHub Action (v4)

`tailscale/github-action@v4` (`node24`) caches binaries (`use-cache: 'false'`
to opt out) and runs `tailscale logout` in a post step so the ephemeral node is
removed at job end. Source:
https://tailscale.com/docs/integrations/github/github-action

```yaml
permissions: {id-token: write, contents: read}
steps:
  - uses: tailscale/github-action@v4
    with:
      oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}   # also the WIF client ID
      audience: ${{ secrets.TS_OIDC_AUDIENCE }}  # WIF; v4.1.0+, client 1.90.1+
      tags: tag:ci
```

- OAuth secret instead of WIF: `oauth-client-id` + `oauth-secret` + `tags`.
  With an OAuth client, `tags` is required (4.0.3+ errors without it) and the
  tags must already exist in the tailnet. `authkey` is deprecated. The default
  client `version` is pinned; `version: latest` is a deliberate opt-in.
- Peers reject the new ephemeral node until they learn of it. `ping:`
  (comma-separated Tailscale IPs or MagicDNS names, e.g. `app.example.ts.net`)
  waits up to 3 minutes for a path; or run `tailscale ping <host>` later.
- Error `requested tags [tag:x] are invalid or not permitted`: the credential
  needs the writable `auth_keys` scope with tags, and `tags:` must match all
  of the credential's tags or be tags they own via `tagOwners`.
- Tailnet Lock: use an ephemeral, reusable auth key pre-signed with `tailscale
  lock sign` (`authkey:`) instead of an OAuth client, and set `statedir:` so
  Tailnet Key Authority data persists (federated identities: undocumented).

## Non-Interactive CLI

- Since 1.88.1 the CLI prompts y/n before significant actions, hanging
  scripts. Bypass with `--accept-risk=<lose-ssh|mac-app-connector|all>`
  (comma-separated) on `tailscale up`, `set` and `down`; `tailscale update
  --yes` skips the update prompt. `lose-ssh` guards `up --force-reauth` and
  `--ssh` toggles while connected over Tailscale, and `down` while connected
  over Tailscale SSH; `mac-app-connector` guards `--advertise-connector` on
  macOS. Accept only risks you have reasoned about. The web reference lags the
  binary; trust `--help`.
- `tailscale wait` (1.96.2+) blocks until tailscaled is up, the backend is
  Running and the interface has a Tailscale IP (userspace mode waits only for
  Running). Non-zero exit on failure or timeout; `--timeout <duration>` bounds
  it (0 = forever). `tailscale ip --assert=<ip>` is also 1.96.2+. On systemd
  Linux, order units `After=tailscale-online.target` (see
  [production-diagnostics.md](production-diagnostics.md#platform-notes)).
- `tailscale set` changes only the flags you name. It has no `--advertise-tags`,
  `--auth-key`, `--login-server`, `--force-reauth`, `--reset` or `--qr`, so
  those changes need `tailscale up` (full desired flag set, or `--reset`);
  `--auth-key`, `--force-reauth` and `--qr` are exempt from `up`'s
  restate-all-non-default-flags rule.

## Terraform Provider

Source `tailscale/tailscale`. Pin 0.29.2 or later: 0.29.0 could clear
`tailscale_tailnet_key.key` on refresh (fixed in 0.29.1; recreate cleared keys);
0.29.2 fixes `recreate_if_invalid` not being checked when the key is not found.

- Auth: prefer a trust credential over `api_key` (cannot be scoped):
  `oauth_client_id` + `oauth_client_secret`, or `oauth_client_id` +
  `identity_token`. In GitHub Actions, AWS or GCP, set only `oauth_client_id`
  and `audience` and the provider fetches the token (0.29+).
  `identity_token_environment_variable_name` covers externally supplied
  tokens (Terraform Cloud). Credential arguments accept `file:` and
  `TAILSCALE_*` env vars; `scopes` narrows OAuth client tokens.
- `tailscale_federated_identity`: from 0.29.0, `audience = ""` is rejected;
  omit it or set null so Tailscale generates it.
- `tailscale_acl` replaces the entire policy file, accepts JSON or HuJSON
  (comments preserved), and validates at plan time including `tests`.
  `overwrite_existing_content` skips the import-first requirement (dangerous);
  `reset_acl_on_destroy` resets to the default policy.
- `tailscale_tailnet_key`: `expiry` is seconds (default 7776000, 90 days);
  `key` is set only at creation (empty after import) and lives in state, so
  use an encrypted remote backend and short expiry, or mint keys outside state
  with an OAuth client.

## GitOps

`tailscale/gitops-acl-action@v1`: inputs `action: test|apply`, `tailnet`,
`policy-file` (default `policy.hujson`), and exactly one credential style
(conflicts fail): `oauth-client-id` + `audience` (WIF, needs `permissions:
id-token: write`), `oauth-client-id` + `oauth-secret`, or `api-key`. Source:
https://tailscale.com/docs/integrations/github/gitops

- Run `test` on pull requests and `apply` on push to main. Prefer the
  federated style over an OAuth secret or a 90-day `api-key`. The credential
  needs `policy_file:read` for test or `policy_file` for apply, plus the
  companion scopes above; a credential with only `policy_file` fails.
- Keep the repository private; policies contain user emails. The docs'
  federated apply example is missing a colon after `audience`; do not copy it.
- Lock the console editor with Settings > Policy file management ("Prevent
  edits in the admin console"); the old code-comment technique stopped working.
- Standalone `gitops-pusher` keeps an ETag in `version-cache.json`
  (`--cache-file`; cache between CI runs); console edits only warn unless
  `--fail-on-manual-edits`, and the next apply overwrites them.
- One owner per policy: the GitOps action or Terraform `tailscale_acl`, not
  both (each overwrites the whole file; inferred from replace semantics).

## Alpha APIs

Endpoints may change; the Tailnets API is absent from the Go client, Terraform
and Pulumi. Docs under tailscale.com/docs/features/: `tailnets-api`,
`oauth-apps/device-provisioning`.

- Tailnets API: API-only tailnets holding tagged devices only, hidden from the
  admin console. Authenticate only with an OAuth client that has the `tailnets`
  scope. The create response includes an OAuth client for the new tailnet; if
  lost, an `all`-scope client in the creating tailnet can get a token for it
  via `tailnet=<ID>` in the token request. Organizations have a tailnet limit.
- OAuth apps device provisioning: authorization-code flow creating user-owned
  (not tag-owned) devices, for per-user tools, not CI. Admin creates the app
  with `POST /api/v2/tailnet/-/oauth-apps` (`redirectUris`, optional
  `allowedNodeAttributes` with `custom:` prefix); users consent at
  `https://login.tailscale.com/a/oauth_authorize`. The exchange returns a
  single-use, 1-hour access token that is itself an auth key. No refresh
  token; single tailnet; ACLs and device quotas attach to the consenting user.
