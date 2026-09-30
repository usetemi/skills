# Tailscale Automation And API

Official docs:

- Trust credentials: https://tailscale.com/docs/reference/trust-credentials
- OAuth clients: https://tailscale.com/docs/features/oauth-clients
- Workload identity federation: https://tailscale.com/docs/features/workload-identity-federation
- Auth keys: https://tailscale.com/docs/features/access-control/auth-keys
- Ephemeral nodes: https://tailscale.com/docs/features/ephemeral-nodes
- Tags: https://tailscale.com/docs/features/tags
- GitHub Action: https://tailscale.com/docs/integrations/github/github-action
- GitOps: https://tailscale.com/docs/integrations/github/gitops
- CLI reference: https://tailscale.com/docs/reference/tailscale-cli
- Tailnets API (alpha): https://tailscale.com/docs/features/tailnets-api
- OAuth apps device provisioning (alpha): https://tailscale.com/docs/features/oauth-apps/device-provisioning

## Credential Decision Path

1. Prefer workload identity federation (WIF) when the platform can issue OIDC
   tokens (GitHub Actions, AWS, GCP, Terraform Cloud). No long-lived Tailscale
   secret is stored.
2. Otherwise use an OAuth client secret. It mints scoped tokens and auth keys
   on demand and does not expire until revoked.
3. Use a plain auth key only where neither works. Keys expire in at most 90
   days, so a long-lived key cannot exist; mint one at deploy time.
4. Tag every automation node and write policy against tags, not users.

"Trust credentials" (Settings > Trust credentials) is the admin console page
and umbrella term for OAuth clients and federated identities. Both mint
short-lived API tokens limited by scopes.

## Auth Keys

- Expiry is 1 to 90 days (default and maximum 90). One-off keys are revoked
  after first use; reusable keys are not.
- Revoking or expiring a key does not deauthorize nodes it registered. They
  stay until their node key expires or you delete them from Machines (or via
  the API).
- Keys are case-sensitive; you can revoke only your own.
- `--auth-key`, `--id-token` and `--client-secret` accept a `file:` prefix,
  which keeps secrets out of shell history and process listings.

```bash
sudo tailscale up \
  --auth-key=file:/run/secrets/ts_authkey \
  --advertise-tags=tag:ci \
  --hostname=ci-${GITHUB_RUN_ID}
```

- Tagged devices have node-key expiry disabled on first tagged authentication,
  so expiry risk on tagged infrastructure is mostly the auth key used to
  register new nodes; node-key expiry is in
  [policy-security.md](policy-security.md#approval-key-expiry-and-identity-lifecycle).
- Tag identity rules (a device is user-owned or tagged, never both; tag
  ownership; `--advertise-tags` cannot remove tags from an auth-key device, so
  mint a new key) are in [policy-security.md](policy-security.md#tags).
  `--advertise-tags` takes comma-separated values with or without the `tag:`
  prefix.

## Ephemeral Nodes

- Removed automatically about 30 to 60 minutes after last activity.
  `tailscale logout` removes one immediately; make it the last deploy or job
  step.
- `tailscaled --state=mem:` (1.22+) makes an ephemeral node; on exit (1.30+)
  tailscaled logs out itself.
- Per the docs, a node present 4+ hours is accounted as a standard tagged device
  rather than under the plan's ephemeral allowance (check current plan terms).
  Do not rely on the 30-60 minute sweep for teardown.
- For many container replicas, use one reusable, ephemeral, tagged auth key.
  Baking a node key into an image creates duplicate devices.

Source: https://tailscale.com/docs/features/ephemeral-nodes

## OAuth Clients

- Token endpoint: `POST https://api.tailscale.com/api/v2/oauth/token`
  (client-credentials grant), optional space-delimited `scope` and `tags`
  params. `tags` applies only to tokens with `devices:core`, `auth_keys` or
  `all`. Send `Authorization: Bearer <token>`. Tokens last 1 hour; this cannot
  be changed.
- OAuth clients must be owned by the tailnet, not a user.
- In `{tailnet}` API paths, `-` means the token's own tailnet. Prefer the
  Tailnet ID (Settings > General) over the legacy ID.
- An `auth_keys` client must have one or more tags chosen, and every key it
  mints carries exactly those tags or tags they own. To let one client mint
  keys for several tags, create an owner tag and make it the `tagOwners`
  owner of the others:

```json
"tagOwners": {
  "tag:terraform-tag-owner": ["autogroup:admin"],
  "tag:server":   ["tag:terraform-tag-owner"],
  "tag:database": ["tag:terraform-tag-owner"]
}
```

  Give the client only `tag:terraform-tag-owner`.
- Mint keys with `POST /api/v2/tailnet/-/keys`:
  `{"capabilities":{"devices":{"create":{"reusable":false,"ephemeral":true,
  "preauthorized":true,"tags":["tag:ci"]}}},"expirySeconds":3600}`. The same
  endpoint creates OAuth clients (`keyType:"client"`) and federated identities
  (`keyType:"federated"`).

### Scopes

- Scopes are granular resource scopes with `:read` variants: `devices:core`,
  `devices:routes`, `devices:posture_attributes`, `auth_keys`, `policy_file`,
  `dns`, `users`, `webhooks`, `log_streaming`, `logs:configuration:read`,
  `logs:network`, `account_settings`, `feature_settings`, and the credential
  scopes `api_access_tokens`, `oauth_keys`, `federated_keys`. Legacy scopes
  (`acl`, `devices`, `dns`, `routes`, ...) still work for existing clients.
- `all` and `all:read` also cover future APIs. Prefer resource scopes.
- Dependencies: `policy_file:read` also needs `devices:core:read` and
  `devices:posture_attributes:read`; `policy_file` needs `devices:core:read`
  and `devices:posture_attributes`. `log_streaming` to a private
  endpoint also needs the device-invites scope and `policy_file`. The docs
  spell the invites scope inconsistently; copy the name from the console's
  scope picker. `devices:core` and `auth_keys` require tags at creation.
- Use the trust-credentials page as the source of truth for scope-to-endpoint
  mapping: https://tailscale.com/docs/reference/trust-credentials

### Revocation

Revoking a credential revokes API tokens it minted but not nodes already
registered with it; delete those nodes separately. Token creation is recorded
in configuration audit logs with the credential's Client ID as actor; review
them after suspected compromise.

## Ephemeral Defaults For OAuth And WIF Registration

Nodes registered with an OAuth client secret (`--auth-key=<oauth-secret>`) or
WIF (`--client-id=...`) are ephemeral by default (`ephemeral=true`,
`preauthorized=false`), and are tag-owned. A long-lived tagged service (subnet
router, connector, Service host) registered this way is removed after going
offline unless you override. Quote the value so the shell keeps `&`:

```bash
tailscale up --auth-key='<oauth-secret>?ephemeral=false&preauthorized=true' \
  --advertise-tags=tag:router
tailscale up --client-id='<id>?ephemeral=false&preauthorized=true' ...
```

OAuth secrets also accept `baseURL` (default `https://api.tailscale.com`). In
containers, an OAuth secret in `TS_AUTHKEY` is ephemeral unless suffixed
`?ephemeral=false`. `--advertise-tags` is required with an OAuth client
secret.

## Workload Identity Federation

Federated identities are created on the Trust credentials page, with
`POST /api/v2/tailnet/-/keys` (`keyType:"federated"`, `issuer`, `subject`,
`customClaimRules`, `scopes`, `tags`), or with the Terraform
`tailscale_federated_identity` resource. The credential needs the `auth_keys`
scope, and `--advertise-tags` must match tags on the identity. The Client ID
and Audience are not secrets. Source:
https://tailscale.com/docs/features/workload-identity-federation

There are two CLI shapes. Do not combine `--audience` with `--id-token`.

```bash
# (a) You hold an OIDC JWT (not a Tailscale API token). Client 1.90.1+.
tailscale up --client-id=<id> --id-token=file:/run/secrets/oidc_jwt \
  --advertise-tags=tag:ci

# (b) The client discovers the platform token. Client 1.94.0+.
tailscale up --client-id=<id> --audience=<aud> --advertise-tags=tag:ci
```

- Discovery for (b) works on AWS (IAM role must allow
  `sts:GetWebIdentityToken`; EC2, ECS, EKS), GCP (metadata server; GCE, GKE)
  and GitHub Actions (`permissions: id-token: write`). Elsewhere use (a).
- Container equivalents: `TS_CLIENT_ID` + `TS_ID_TOKEN`, or `TS_CLIENT_ID` +
  `TS_AUDIENCE`. `TS_AUDIENCE` cannot be combined with `TS_CLIENT_SECRET` or
  `TS_ID_TOKEN`. `TS_CLIENT_ID` alone works where the token auto-generates
  (GitHub Actions). Source:
  https://tailscale.com/docs/features/containers/docker/docker-params
- For raw API use, exchange the JWT: `POST
  https://api.tailscale.com/api/v2/oauth/token-exchange` with form fields
  `client_id` and `jwt`. The returned token is short-lived; repeat the
  exchange on expiry.
- Matching: `sub` and optional `customClaimRules` are the authorization
  boundary. `*` matches any characters; everything else must match exactly.
  Nested claims use dots (`user.name`); keys containing a period are
  double-quoted (`"open.id".username`). Use precise patterns (for GitHub, a
  specific repo and ref or environment): any matching workload obtains the
  credential's scopes and tags.
- Debugging: the API error is deliberately generic (`Unauthorized. Visit
  [admin console link] for details`). The specific reason appears only on the
  federated identity's page under Trust credentials, and persists until a later
  exchange succeeds. Read it there rather than guessing.

## GitHub Action (v4)

Use `tailscale/github-action@v4`. It is a `node24` JavaScript action, caches
Tailscale binaries (`use-cache: 'false'` to opt out), and runs `tailscale
logout` in a post step so the ephemeral node is removed at job end. Sources:
https://tailscale.com/docs/integrations/github/github-action and the
action's README and `action.yml` at https://github.com/tailscale/github-action

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: actions/checkout@v4
  - uses: tailscale/github-action@v4
    with:
      oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}   # also the WIF client ID
      audience: ${{ secrets.TS_OIDC_AUDIENCE }}            # WIF; v4.1.0+, client 1.90.1+
      tags: tag:ci
      ping: 100.64.0.10,app.example.ts.net
  - run: ./scripts/smoke-test-tailnet-service
```

- OAuth secret instead of WIF: `oauth-client-id` + `oauth-secret` + `tags`.
  With an OAuth client, `tags` is required (4.0.3+ errors without it) and the
  tags must already exist in the tailnet. `authkey` is deprecated in favor of
  OAuth or WIF.
- Other inputs: `version`, `args`, `tailscaled-args`, `hostname` (valid DNS
  label), `timeout` (default 2m), `retry` (default 5), `statedir` (empty =
  in-memory), `sha256sum`, `ping`, `log-mode` (`grouped` default, `normal`,
  `quiet`). The default client `version` is pinned and changes rarely; set
  `version: latest` deliberately if you need a newer client.
- Verify connectivity before using tailnet hosts. The new ephemeral node
  propagates across the tailnet with a delay, and peers reject it until they
  learn of it. The `ping:` input (Tailscale IPs or MagicDNS names,
  comma-separated) waits up to 3 minutes for a direct or relayed path; or run
  `tailscale ping <host>` in a later step.
- Error `requested tags [tag:x] are invalid or not permitted`: the credential
  needs the writable `auth_keys` scope with tags, and `tags:` must match all
  of the credential's tags or be tags they own via `tagOwners`. Make the
  credential's tag an owner of the requested tags.
- Tailnet Lock: the action's README says to use an ephemeral, reusable,
  pre-signed auth key (`authkey:`, signed with `tailscale lock sign`) instead
  of an OAuth client, and set `statedir:` so Tailnet Key Authority data
  persists. (Whether federated identities work is undocumented.)

## Non-Interactive CLI

- Since 1.88.1 the CLI asks y/n before significant actions, which hangs
  scripts. Bypass with `--accept-risk=<lose-ssh|mac-app-connector|all>`
  (comma-separated) on `tailscale up`, `set` and `down`; `tailscale update
  --yes` skips the update prompt. `lose-ssh` guards `up --force-reauth` and
  `--ssh` toggles while connected over Tailscale, and `tailscale down` while
  connected over Tailscale SSH.
  `mac-app-connector` guards `--advertise-connector` on macOS. Accept only
  risks you have reasoned about. The web reference lags the binary; trust
  `--help`.
- `tailscale wait` (1.96.2+) blocks until tailscaled is up, the backend is
  Running and the interface has a Tailscale IP (userspace mode waits only for
  Running). Exit 0 on success, non-zero on failure or timeout; `--timeout
  <duration>` bounds it (0 = forever).

```bash
tailscale wait --timeout 60s && /path/to/service
tailscale wait && tailscale ip --assert=100.64.0.10   # ip --assert: 1.96.2+
```

  On systemd Linux, order units `After=tailscale-online.target` (see
  [production-diagnostics.md](production-diagnostics.md#platform-notes)).
- `tailscale set` changes only the flags you name; there are no defaults. It
  has no `--advertise-tags`, `--auth-key`, `--login-server`, `--force-reauth`,
  `--reset` or `--qr`, so tag, credential and login-server changes need
  `tailscale up` (full desired flag set, or `--reset`). `--auth-key`,
  `--force-reauth` and `--qr` are exempt from `up`'s rule that all non-default
  flags be restated. `tailscale get [setting|all]` reads preferences; `get
  --set-flags` prints them as `tailscale set` arguments.

## Tailscale API

- Base: `https://api.tailscale.com/api/v2/`, `Authorization: Bearer <token>`.
  Use an OAuth or WIF token, not a user API key, for automation.
- Services (see [expose-services.md](expose-services.md)): `GET|PUT|DELETE
  /tailnet/{tailnet}/services/{serviceName}`, list at
  `/tailnet/{tailnet}/services`, hosts at `.../services/{serviceName}/devices`,
  approval at `.../services/{serviceName}/device/{deviceId}/approved`.
  Advertising and approval are separate steps.
  Source: https://tailscale.com/docs/features/tailscale-services

## Terraform Provider

Source `tailscale/tailscale`. Pin 0.29.2 or later: 0.29.0 could clear
`tailscale_tailnet_key.key` on refresh (0.29.1 fixes it; already-cleared keys
must be recreated), and 0.29.2 fixes `recreate_if_invalid` not being checked
when the key is not found. 0.29 added the `tailscale_service` resource and OIDC
token discovery from the runtime via `audience`.

- Auth: prefer a trust credential over `api_key` (API keys cannot be scoped).
  Use `oauth_client_id` + `oauth_client_secret`, or `oauth_client_id` +
  `identity_token`. In GitHub Actions, AWS (EC2 instance profile or ECS task
  role) or GCP (metadata server), set only `oauth_client_id` and `audience` and
  the provider fetches the token.
  `identity_token_environment_variable_name` covers externally supplied
  tokens (Terraform Cloud). Credential arguments accept `file:` and
  `TAILSCALE_*` env vars. `scopes` narrows the token (OAuth client credentials
  only); `tailnet` prefers the Tailnet ID.
- `tailscale_federated_identity`: `scopes`, `tags`, `issuer`, `subject`,
  `custom_claim_rules`. From 0.29.0, `audience = ""` is rejected; omit it or
  set null so Tailscale generates it.
- `tailscale_acl` replaces the entire policy file (not just ACLs), accepts
  JSON or HuJSON (comments preserved), and validates at plan time including
  the top-level `tests`. `overwrite_existing_content` skips the
  import-first requirement (dangerous); `reset_acl_on_destroy` resets to the
  default policy on destroy.
- `tailscale_tailnet_key`: `expiry` is seconds (default 7776000, 90 days);
  `key` is populated only at creation and empty after import; the key lives in
  state, so use an encrypted remote backend and short expiry, or mint keys
  outside state with an OAuth client.

## GitOps

`tailscale/gitops-acl-action@v1`: inputs `action: test|apply`, `tailnet`,
`policy-file` (default `policy.hujson`), and exactly one credential style
(conflicting credentials fail): `oauth-client-id` + `audience` (WIF, needs
`permissions: id-token: write`), `oauth-client-id` + `oauth-secret`, or
`api-key`. Sources: https://tailscale.com/docs/integrations/github/gitops and
the action's `action.yml` at https://github.com/tailscale/gitops-acl-action

- Run `test` on pull requests and `apply` on push to main. Prefer the federated
  style over an OAuth client secret or a 90-day `api-key`. The credential needs
  `policy_file:read` for test or `policy_file` for apply, plus the companion
  scopes above; a credential with only `policy_file` fails.
- Keep the repository private; policies contain user emails.
- Lock the admin console editor with Settings > Policy file management
  ("Prevent edits in the admin console"). The older code-comment technique
  stopped working 2025-06-03.
- Standalone `gitops-pusher` keeps an ETag in `version-cache.json`
  (`--cache-file`; cache between CI runs) and only warns on console edits unless
  `--fail-on-manual-edits` is set; the next apply overwrites them.
- Validate or preview a change with POST `/api/v2/tailnet/{tailnet}/acl/validate`
  and `/acl/preview`.
- The docs' federated apply example is missing a colon after `audience`;
  do not copy it verbatim.
- One owner per policy: the GitOps action or Terraform `tailscale_acl`, not
  both (each overwrites the whole file; inferred from replace semantics).

## Alpha APIs

Alpha: endpoints may change, and the Tailnets API endpoints are absent from the
Go client, Terraform and Pulumi. Do not build durable tooling on them without
pinning expectations.

- Tailnets API: create, list (paginated) and delete API-only tailnets. They
  hold tagged devices only (no human users) and do not appear in the admin
  console. Authenticate only with an OAuth client that has the
  `tailnets` scope, created in an existing tailnet. The create response
  includes an OAuth client for the new tailnet; if lost, an `all`-scope OAuth
  client in the creating tailnet can get a token for it by passing
  `tailnet=<ID>` in the OAuth token request. The organization has a
  tailnet limit that includes the original (check the docs for the current
  number). Documented uses: ephemeral CI tailnets, sandbox tailnets for AI
  agents, private connectivity built into an application.
- OAuth apps device provisioning: authorization-code flow that creates
  user-owned devices, not tag-owned ones. Admin creates the app with
  `POST /api/v2/tailnet/-/oauth-apps` (`redirectUris`, optional
  `allowedNodeAttributes` with `custom:` prefix); users consent at
  `https://login.tailscale.com/a/oauth_authorize`. The exchange returns a
  single-use access token, valid 1 hour, that is itself an auth key
  (`tailscale up --auth-key=<token>`). No refresh token; single tailnet; ACLs
  and device quotas attach to the consenting user. For per-user provisioning
  tools, not CI: use OAuth client credentials or WIF for tag-owned CI nodes.
