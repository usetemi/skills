# Tailscale Service Exposure

Official docs:

- Serve: https://tailscale.com/docs/features/tailscale-serve
- Serve CLI: https://tailscale.com/docs/reference/tailscale-cli/serve
- Funnel: https://tailscale.com/docs/features/tailscale-funnel
- Funnel and Serve examples: https://tailscale.com/docs/reference/examples/funnel
- Services: https://tailscale.com/docs/features/tailscale-services
- Services config file: https://tailscale.com/docs/reference/tailscale-services-configuration-file
- HTTPS certificates: https://tailscale.com/docs/how-to/set-up-https-certificates
- CLI reference (includes `cert`): https://tailscale.com/docs/reference/tailscale-cli
- tsidp: https://tailscale.com/docs/features/tsidp
- Security bulletins: https://tailscale.com/security-bulletins

## Decision Path

1. Decide who reaches the service:
   - tailnet identities only, subject to access policy: Serve
   - the public internet: Funnel
   - a stable tailnet name and virtual IP that survives node replacement or
     spans several hosts: Tailscale Services
2. Confirm hostname, port, protocol, target process, and auth layer.
3. Read current config before adding exposure (below).
4. For public exposure, add app-layer auth, logs, and a removal step first.

Read-only checks:

```bash
tailscale serve status --json
tailscale serve get-config --all      # complete list of Services this node hosts
tailscale funnel status --json
tailscale service list --json         # Services this node can reach (1.102.1+)
```

`serve status` and `serve status --json` return different information; use
`get-config --all` for the complete Services listing
([Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve)).

Service advertisement (the host declares it), admin approval (or
`autoApprovers`), client acceptance, and access policy (grants) are separate
gates, as for routes
([routing-connectors.md](routing-connectors.md#route-injection)). Serve or
Funnel working on a node says nothing about Services or policy.

## Serve (private)

Serve exposes files, directories, text, local ports, TCP, TLS-terminated TCP,
or Unix sockets to tailnet identities.

- Foreground by default; `--bg` persists across reboots. `--yes` skips
  interactive prompts (needed for unattended automation).
- Targets: a port (`3000`), `localhost:3000`, a full URL with path,
  `https+insecure://host:port` for self-signed upstreams, `unix:/path.sock`
  (Linux, macOS, BSD), a file, a directory, or text.
- Modes: `--https=<port>` (default), `--http`, `--tcp`, `--tls-terminated-tcp`;
  `--set-path` for path routing; `--proxy-protocol=1|2` for TCP forwarding
  (1.92.1+).
- Disable one handler by repeating the original command with `off` appended.
  The target becomes optional; all original flags stay required.
  `tailscale serve reset` removes everything, including unrelated handlers.

```bash
tailscale serve --bg --https=443 http://127.0.0.1:3000
tailscale serve --bg --https=443 --set-path=/api http://127.0.0.1:4000
tailscale serve --bg --tcp=5432 tcp://127.0.0.1:5432
tailscale serve --https=443 off
```

## Funnel (public)

Funnel routes public internet traffic through Tailscale relays to a local
service ([Funnel](https://tailscale.com/docs/features/tailscale-funnel)).

- Listens only on ports 443, 8443, and 10000; TLS only, so no UDP.
- Uses only the node's `<host>.<tailnet>.ts.net` name; no custom domains.
- Bandwidth limits are not configurable. Public DNS can take up to 10 minutes
  to appear.
- Needs MagicDNS, HTTPS certificates enabled, and a `funnel` node attribute:

```hujson
{
  "nodeAttrs": [
    {"target": ["tag:funnel"], "attr": ["funnel"]},
  ],
}
```

Enabling Funnel through the CLI adds `{"target":["autogroup:member"],
"attr":["funnel"]}`. For tagged hosts, target the tag explicitly, as in the
example above. The Funnel and Serve pages disagree
on whether Funnel is on by default; treat the policy entry as truth and scope it
to a tag or group to limit who can publish.

- Serve and Funnel cannot share a port. The most recent `serve` or `funnel`
  command decides whether that port is private or public, so running
  `tailscale serve` on a funneled port makes it private again.
- Funnel flags are a subset of Serve's: `--bg`, `--https`, `--tcp`,
  `--tls-terminated-tcp`, `--set-path`, `--proxy-protocol`, `--yes`. There is
  no `--http`, `--accept-app-caps`, or `--service` on `funnel`.
- Funnel cannot be enabled while `shields-up` is set (tailscaled rejects it with
  "Unable to turn on Funnel while shields-up is enabled"); any serve config
  change is rejected with "config file is locked" when tailscaled runs from a
  config file. Check `tailscale debug prefs` before debugging further.

### Public exposure hygiene

- Serve and Funnel HTTPS names get public certificates, and every public
  certificate is recorded in Certificate Transparency logs, so the URL is
  discoverable by scanners even if the tailnet name looks random
  ([HTTPS guide](https://tailscale.com/docs/how-to/set-up-https-certificates)).
  Your app auth is the only defence.
- Rule: if getting past the password would be a disaster (admin panels, home
  automation, self-hosted assistants and agent frameworks), use Serve or
  sharing, not Funnel. Funnel fits small sites with no sensitive data
  ([Funnel blog](https://tailscale.com/blog/funnel-fridge)).
- Keep hosts at the [version floor](#version-floor-for-exposure-hosts) below.
- Funnel requests carry no identity headers. The local proxy sets
  `Tailscale-Funnel-Request: ?1` and deletes any client-supplied copy (from
  Tailscale's `ipn/ipnlocal/serve.go`, not the docs pages). Use it to tell
  public from tailnet traffic when one backend serves both.

## Identity Headers

For proxied HTTP, Serve injects `Tailscale-User-Login`, `Tailscale-User-Name`,
and `Tailscale-User-Profile-Pic`
([Serve](https://tailscale.com/docs/features/tailscale-serve)).

- Non-ASCII values are RFC 2047 Q-encoded. Inbound copies of these headers are
  deleted before proxying.
- Not set for tagged source devices, traffic from outside the tailnet, Funnel,
  or TCP and TLS-terminated-TCP forwarding. An empty `Tailscale-User-Login`
  means unauthenticated caller, never anonymous-OK.
- A backend that trusts these headers must listen on localhost only. Otherwise
  direct callers can forge them.

## App Capabilities Header

`tailscale serve --accept-app-caps=example.com/cap/monitoring,... <target>`
(1.92+, Serve only) adds `Tailscale-App-Capabilities`: JSON
`{"cap": [values]}` limited to the listed capabilities the caller holds through
a grant's `app` block. Unlike the identity headers, it is also set for tagged
callers
([Serve examples](https://tailscale.com/docs/reference/examples/serve)).

```bash
tailscale serve --bg --accept-app-caps=example.com/cap/read 3000
```

## Tailscale Services

A Service is a stable name (`svc:<name>`) with a virtual IP (TailVIP), hosted
by one or more tagged nodes. GA since 2026-01-27
([Services](https://tailscale.com/docs/features/tailscale-services)).

Requirements and limits:

- Host must use a tag identity; a user-authenticated device cannot host.
  Community report
  ([issue 17692](https://github.com/tailscale/tailscale/issues/17692)): clients
  1.92.0+ error on an untagged host; older clients silently never showed it in
  the console.
- Hosts need 1.86.0+. An Admin, Network admin, or Owner approves each host
  unless `autoApprovers.services` covers it.
- Only TCP as transport. TailVIPs accept inbound connections only.
- Client acceptance: 1.94+ accepts Service VIPs on all platforms regardless of
  `--accept-routes`; Linux 1.93 and earlier still need
  `sudo tailscale set --accept-routes`.
- Containers 1.96.5+ auto-advertise Services from the Serve config; see
  [containers-tsnet.md](containers-tsnet.md#serve-config-in-a-container).
- With several hosts, in-region load balancing needs regional routing enabled
  for the tailnet.

### Host a Service

`--service` implies `--bg` and advertises in the same step, so it persists
across restarts. HTTPS provisions the cert for the Service DNS name.

```bash
tailscale serve --service=svc:web-server --https=443 127.0.0.1:8080
tailscale serve status --json
tailscale status --json | jq '.Self.CapMap."service-host"'
```

Endpoint layers: L7 (`--http`/`--https`, `--set-path`), L4 (`--tcp`,
`--tls-terminated-tcp`; `--set-path` empty), and L3 (`--tun`, Linux only,
unmodified packets, the only way to get UDP).

### Policy

```hujson
{
  "grants": [
    {"src": ["autogroup:member"], "dst": ["svc:web-server"], "ip": ["443"]},
  ],
  "autoApprovers": {
    "services": {
      "svc:web-server": ["tag:server"],
      "tag:prod-service": ["tag:prod-infra"],
    },
  },
}
```

- The grant destination is the Service; a tag on the Service lets one rule
  cover a group. The `autoApprovers.services` key is a Service name or a tag on
  Services; the value is the host tags allowed to advertise.
- Services are valid `accept` and `deny` destinations in policy `tests`.
- Console states: Pending approval, Needs configuration, Connected, Offline,
  Pre-approved, Draining.

### Drain and remove

1. `tailscale serve drain svc:<name>` stops new connections; existing ones
   continue until they close.
2. Wait for connections to finish.
3. Only then remove or change config. Removing config first ends connections
   abruptly.

```bash
tailscale serve drain svc:web-server
tailscale serve --service=svc:web-server --https=443 off   # one endpoint
tailscale serve clear svc:web-server                        # all handlers
tailscale serve advertise svc:web-server                    # bring back
```

Changing the protocol on an existing port means removing that endpoint, then
re-adding it. Modify a host's config only after draining.

Diagnostic lead (single user report, open and unconfirmed by Tailscale as of
2026-09-28,
[issue 21513](https://github.com/tailscale/tailscale/issues/21513)): with two
hosts, a client may move the whole Service VIP to the other host as soon as it
learns of the drain, so established flows get a RST. Do not promise
zero-reset drains for multi-host Services.

### Declarative config

`get-config` and `set-config` require a scope flag and manage Services config,
not plain node-level Serve or Funnel config. `set-config --service` overwrites
all handlers of that Service; `--all` overwrites all handlers of all Services on
the node
([config file](https://tailscale.com/docs/reference/tailscale-services-configuration-file)).

```bash
tailscale serve get-config --all > serveconfig.json
tailscale serve set-config --all serveconfig.json
tailscale serve advertise svc:web-server
```

```json
{
  "version": "0.0.1",
  "services": {
    "svc:web-server": {
      "endpoints": {"tcp:443": "https://localhost:443"},
      "advertised": true
    }
  }
}
```

- `version` must be exactly `"0.0.1"`. Endpoint keys are `tcp:<port>` or
  `tcp:<start>-<end>`; target schemes are `http`, `https`, `tcp`. `advertised`
  is optional (defaults to true); the docs still show a separate `advertise`
  step, so verify with `get-config --all`.
- The config file page calls the format huJSON, and the client parses it unless
  built with `ts_omit_hujsonconf`; strict JSON works everywhere. `text:` and
  `file:` destinations are CLI-only.
- Diagnostic lead
  ([issue 18381](https://github.com/tailscale/tailscale/issues/18381), open,
  acknowledged by a Tailscale contributor): `set-config` infers the serve type
  from the target scheme, so an HTTPS-terminated Service with an `http://`
  backend is re-imported as plain HTTP. For HTTPS-terminated Services use the
  imperative command, and check `serve status --json` after any `set-config`.
  Do not treat get-config then set-config as a lossless round trip.
- Diagnostic lead
  ([issue 18821](https://github.com/tailscale/tailscale/issues/18821), open,
  reported on 1.94.2, corroborated on 1.98.2 and 1.98.9): after approval the daemon can keep printing
  "approval from an admin is required". Re-running the same `serve --service`
  does not refresh it; `tailscale serve clear svc:<name>`, a short pause, then
  re-applying does. The API endpoint
  `/services/{svc}/device/{nodeId}/approved` is the reliable approval signal.

### Version floor for exposure hosts

Use 1.98.9 or newer on Serve, Funnel, and Services hosts
([bulletins](https://tailscale.com/security-bulletins)).

- TS-2026-008: one malformed HTTP request could pin a CPU core indefinitely on a
  Serve or Funnel node, and for Funnel it could come from any unauthenticated
  internet host.
- TS-2026-007: older Service hosts accepted traffic to Service IPs on
  non-advertised ports and forwarded it to loopback listeners, so loopback-only
  processes were reachable by anyone with a grant to the Service. Do not use
  loopback binding as the access control on an older Service host.

## HTTPS Certificates

Enable under the DNS page ("HTTPS Certificates")
([guide](https://tailscale.com/docs/how-to/set-up-https-certificates)).

- Every `machine.tailnet.ts.net` name that gets a certificate is published to
  public Certificate Transparency logs (only machines that request one, such as
  through `tailscale cert`, Serve, or Funnel). Do not enable if machine names
  are sensitive; rename a machine before it obtains a certificate. Disabling
  does not revoke issued certs.
- Only the full DNS name gets a cert, not a bare hostname.
- Serve, Funnel, tsnet, and integrations fetch and renew certs automatically.
- Files written by `tailscale cert` are not renewed: tailscaled does not know
  where you put them. Rerun on a timer and reload the service. Certs are Let's
  Encrypt, 90 days, DNS-01.
- Do not loop fresh requests; Let's Encrypt rate limits can force a wait of
  about 34 hours. Reuse cached certs.

```bash
tailscale cert --cert-file=host.crt --key-file=host.key \
  --min-validity=720h host.tailnet.ts.net
```

`--cert-file` and `--key-file` each accept `-` for stdout (default
`DOMAIN.crt`/`DOMAIN.key` when both unset); `--min-validity` guarantees the
returned cert lasts at least that long, capped by the CA maximum.

Non-root reverse proxies cannot fetch certs from tailscaled by default. Set the
user in `/etc/default/tailscaled` and restart
([Caddy](https://tailscale.com/docs/integrations/web-servers/caddy/caddy-certificates)):

```bash
TS_PERMIT_CERT_UID=caddy   # name or numeric ID
```

Caddy 2.5+ then obtains and renews `*.ts.net` certs with no config.

## tsidp (OIDC provider)

tsidp is an OIDC/OAuth identity provider running as a tsnet node, for SSO to
self-hosted apps and authenticated MCP servers
([docs](https://tailscale.com/docs/features/tsidp),
[repo](https://github.com/tailscale/tsidp)).

- Experimental community project, pre-1.0, breaking changes possible; needs
  `TAILSCALE_USE_WIP_CODE=1` while below 1.0. Development moved to
  `tailscale/tsidp`; `cmd/tsidp` in `tailscale/tailscale` is no longer
  maintained. Image: `ghcr.io/tailscale/tsidp:latest`. Needs MagicDNS and
  HTTPS.
- Persistent state is mandatory (`-dir` / `TS_STATE_DIR`). Without it tsidp
  re-registers on every restart, loses dynamically registered OIDC clients, and
  invalidates sessions.
- With an OAuth client secret (`tskey-client-...`) as `TS_AUTHKEY`, also set
  `TS_ADVERTISE_TAGS` / `-advertise-tags` and define the tag in `tagOwners`.
  `TS_AUTHKEY_FILE` must not be set alongside `TS_AUTHKEY` or tsidp refuses to
  start.
- Reachable only inside the tailnet by default. `-funnel`
  (`TSIDP_USE_FUNNEL=1`) exposes the IdP publicly; use it only when a SaaS app
  outside the tailnet must reach it. Its hostname is then in CT logs.
- Authorization is the `tailscale.com/cap/tsidp` app capability in a grant. The
  admin UI and dynamic client registration are denied by default; enable with
  `allow_admin_ui: true` and `allow_dcr: true`. `users` and `resources` gate
  token requests (STS token exchange also needs `-enable-sts` /
  `TSIDP_ENABLE_STS=1`), `extraClaims` adds claims, `includeInUserInfo` returns them
  from `/userinfo`. The schema may change at any time.
