# Tailscale Service Exposure

Docs: [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve), [Services](https://tailscale.com/docs/features/tailscale-services).

## Decision Path

1. Who reaches the service? Tailnet identities only, subject to access policy:
   Serve. The public internet: Funnel. A stable tailnet name and virtual IP
   that survives node replacement or spans several hosts: Tailscale Services.
2. Confirm hostname, port, protocol, target process, and auth layer; read
   current config first. For public exposure, add app-layer auth, logs, and a
   removal step first.

```bash
tailscale serve status --json
tailscale serve get-config --all      # complete list of Services this node hosts
tailscale funnel status --json
tailscale service list --json         # Services this node can reach (1.102.1+)
```

Service advertisement, admin approval (or `autoApprovers`), client acceptance,
and access policy (grants) are separate gates, as for routes
([routing-connectors.md](routing-connectors.md#route-injection)). Serve or
Funnel working says nothing about Services or policy.

## Serve (private)

Serve exposes files, directories, text, local ports, TCP, TLS-terminated TCP,
or Unix sockets to tailnet identities.
- Foreground by default; `--bg` persists across reboots. `--yes` skips prompts
  (needed for automation).
- Targets: a port, `localhost:3000`, a URL with path,
  `https+insecure://host:port` for self-signed upstreams, `unix:/path.sock`
  (Linux, macOS, BSD), a file, a directory, or text.
- Modes: `--https=<port>` (default), `--http`, `--tcp`, `--tls-terminated-tcp`;
  `--set-path` for path routing; `--proxy-protocol=1|2` for TCP forwarding
  (1.92.1+).
- Disable one handler by repeating the original command with `off` appended.
  The target becomes optional; all original flags stay required.
  `tailscale serve reset` removes everything, including unrelated handlers.
- `--accept-app-caps=example.com/cap/monitoring,...` (1.92+, Serve only) adds
  `Tailscale-App-Capabilities`: JSON `{"cap": [values]}` limited to the listed
  capabilities the caller holds through a grant's `app` block. Unlike the
  identity headers, it is also set for tagged callers.

```bash
tailscale serve --bg --https=443 --set-path=/api http://127.0.0.1:4000
tailscale serve --bg --tcp=5432 tcp://127.0.0.1:5432
```

### Identity Headers

For proxied HTTP, Serve injects `Tailscale-User-Login`, `Tailscale-User-Name`,
and `Tailscale-User-Profile-Pic`; non-ASCII values are RFC 2047 Q-encoded and
inbound copies are deleted before proxying.

- Not set for tagged source devices, traffic from outside the tailnet, Funnel,
  or TCP and TLS-terminated-TCP forwarding. An empty `Tailscale-User-Login`
  means unauthenticated caller, never anonymous-OK.
- A backend that trusts these headers must listen on localhost only. Otherwise
  direct callers can forge them.

## Funnel (public)

Funnel routes public internet traffic through Tailscale relays to a local
service.

- Listens only on ports 443, 8443, and 10000; TLS only, so no UDP.
- Only the node's `<host>.<tailnet>.ts.net` name (no custom domains); bandwidth
  limits are not configurable; public DNS can take 10 minutes.
- Needs MagicDNS, HTTPS certificates enabled, and a `funnel` node attribute,
  e.g. `"nodeAttrs": [{"target": ["tag:funnel"], "attr": ["funnel"]}]`.
  Enabling Funnel through the CLI adds `{"target":["autogroup:member"],
  "attr":["funnel"]}`. For tagged hosts, target the tag explicitly. Treat the
  policy entry as truth and scope it to a tag or group to limit who can publish.
- Serve and Funnel cannot share a port. The most recent `serve` or `funnel`
  command decides whether that port is private or public, so running
  `tailscale serve` on a funneled port makes it private again.
- Funnel flags are a subset of Serve's: `--bg`, `--https`, `--tcp`,
  `--tls-terminated-tcp`, `--set-path`, `--proxy-protocol`, `--yes`. There is
  no `--http`, `--accept-app-caps`, or `--service` on `funnel`.
- Funnel is rejected while `shields-up` is set, and any serve config change
  fails with "config file is locked" when tailscaled runs from a config file.
  Check `tailscale debug prefs` first.

### Public exposure hygiene

- Certificates land in Certificate Transparency logs, so scanners find the URL
  even if the tailnet name looks random. Your app auth is the only defence.
- Rule: if getting past the password would be a disaster (admin panels, home
  automation, self-hosted assistants and agent frameworks), use Serve or
  sharing, not Funnel ([blog](https://tailscale.com/blog/funnel-fridge)).
- Keep hosts at the [version floor](#version-floor-for-exposure-hosts).
- Funnel requests carry no identity headers. The local proxy sets
  `Tailscale-Funnel-Request: ?1` and deletes any client-supplied copy (from
  Tailscale's `ipn/ipnlocal/serve.go`, not the docs pages). Use it to tell
  public from tailnet traffic on a shared backend.

## Tailscale Services

A Service is a stable name (`svc:<name>`) with a virtual IP (TailVIP), hosted
by one or more tagged nodes. GA since 2026-01-27.

- Host must use a tag identity; a user-authenticated device cannot host.
  Community report ([issue 17692](https://github.com/tailscale/tailscale/issues/17692)):
  clients 1.92.0+ error on an untagged host; older ones silently never showed
  it in the console.
- Hosts need 1.86.0+. An Admin, Network admin, or Owner approves each host
  unless `autoApprovers.services` covers it.
- Only TCP as transport. TailVIPs accept inbound connections only.
- Client acceptance: 1.94+ accepts Service VIPs on all platforms regardless of
  `--accept-routes`; Linux 1.93 and earlier need `tailscale set --accept-routes`.
- Containers 1.96.5+ auto-advertise Services from the Serve config; see
  [containers-tsnet.md](containers-tsnet.md#serve-config-in-a-container).
- Several hosts need regional routing enabled for in-region load balancing.

### Host a Service

`--service` implies `--bg` and advertises in the same step, so it persists
across restarts. HTTPS provisions the cert for the Service DNS name.

```bash
tailscale serve --service=svc:web-server --https=443 127.0.0.1:8080
tailscale status --json | jq '.Self.CapMap."service-host"'
```

Layers: L7 (`--http`/`--https`, `--set-path`), L4 (`--tcp`,
`--tls-terminated-tcp`; no `--set-path`), and L3 (`--tun`, Linux only,
unmodified packets, the only way to get UDP).

### Policy

```hujson
{
  "grants": [{"src": ["autogroup:member"], "dst": ["svc:web-server"], "ip": ["443"]}],
  "autoApprovers": {"services": {"svc:web-server": ["tag:server"]}},
}
```

- The grant destination is the Service (or a tag on Services). The
  `autoApprovers.services` key is a Service name or tag; the value is the host
  tags allowed to advertise. Services are valid `tests` destinations.

### Drain and remove

`tailscale serve drain svc:<name>` stops new connections while existing ones
continue until they close. Modify or remove a host's config only after they
finish; removing first ends connections abruptly. Remove one endpoint with
`tailscale serve --service=svc:web-server --https=443 off`, all handlers with
`tailscale serve clear svc:web-server`, and bring a Service back with
`tailscale serve advertise svc:web-server`. Changing the protocol on an
existing port means removing that endpoint, then re-adding it.

Diagnostic lead (single user report, open and unconfirmed by Tailscale,
[issue 21513](https://github.com/tailscale/tailscale/issues/21513)): with two
hosts, a client may move the whole Service VIP to the other host on learning of
the drain, resetting established flows. Do not promise zero-reset drains for
multi-host Services.

### Declarative config

`get-config` and `set-config` require a scope flag and manage Services config,
not plain node-level Serve or Funnel config. `set-config --service` overwrites
all handlers of that Service; `--all` overwrites all handlers of all Services on
the node.

```json
{"version": "0.0.1", "services": {"svc:web-server": {
  "endpoints": {"tcp:443": "https://localhost:443"}, "advertised": true}}}
```

- `version` must be exactly `"0.0.1"`. Endpoint keys are `tcp:<port>` or
  `tcp:<start>-<end>`; target schemes are `http`, `https`, `tcp`. `advertised`
  is optional (defaults to true); the docs still show a separate `advertise`
  step, so verify with `get-config --all`.
- The client parses huJSON unless built with `ts_omit_hujsonconf`; strict JSON
  works everywhere. `text:`/`file:` destinations are CLI-only.
- Diagnostic lead
  ([issue 18381](https://github.com/tailscale/tailscale/issues/18381), open,
  acknowledged by a Tailscale contributor): `set-config` infers the serve type
  from the target scheme, so an HTTPS-terminated Service with an `http://`
  backend is re-imported as plain HTTP. Use the imperative command for
  HTTPS-terminated Services, and check `serve status --json` after any
  `set-config`. get-config then set-config is not a lossless round trip.
- Diagnostic lead
  ([issue 18821](https://github.com/tailscale/tailscale/issues/18821), open,
  reported on 1.94.2, corroborated on 1.98.2 and 1.98.9): after approval the
  daemon can keep printing "approval from an admin is required". Re-running
  `serve --service` does not refresh it; `tailscale serve clear svc:<name>`, a
  short pause, then re-applying does. The API endpoint
  `/services/{svc}/device/{nodeId}/approved` is the reliable approval signal.

### Version floor for exposure hosts

Use 1.98.9 or newer on Serve, Funnel, and Services hosts
([bulletins](https://tailscale.com/security-bulletins)).

- TS-2026-008: one malformed HTTP request could pin a CPU core indefinitely on
  a Serve or Funnel node, from any unauthenticated internet host for Funnel.
- TS-2026-007: older Service hosts forwarded traffic on non-advertised Service
  IP ports to loopback listeners, exposing loopback-only processes to anyone
  with a grant to the Service. Loopback binding is not access control there.

## HTTPS Certificates

Enable under the DNS page
([guide](https://tailscale.com/docs/how-to/set-up-https-certificates)).
- Every `machine.tailnet.ts.net` name that requests a certificate (through
  `tailscale cert`, Serve, or Funnel) is published to public Certificate
  Transparency logs. Do not enable if machine names are sensitive; rename a
  machine before it obtains a certificate. Disabling does not revoke issued
  certs.
- Only the full DNS name gets a cert. Serve, Funnel, tsnet, and integrations
  renew certs automatically; files written by `tailscale cert` are not: rerun
  on a timer and reload the service. Certs are Let's Encrypt, 90 days, DNS-01.
- Do not loop fresh requests; Let's Encrypt rate limits can force a wait of
  about 34 hours. Reuse cached certs.
- `tailscale cert --cert-file=host.crt --key-file=host.key --min-validity=720h
  host.tailnet.ts.net`: `-` sends either file to stdout (default
  `DOMAIN.crt`/`DOMAIN.key` when both unset); `--min-validity` guarantees the
  cert lasts at least that long, capped by the CA maximum.
- Non-root reverse proxies cannot fetch certs from tailscaled by default. Set
  `TS_PERMIT_CERT_UID=caddy` (name or numeric ID) in `/etc/default/tailscaled`
  and restart; Caddy 2.5+ then obtains and renews `*.ts.net` certs with no
  config ([Caddy](https://tailscale.com/docs/integrations/web-servers/caddy/caddy-certificates)).

## tsidp (OIDC provider)

tsidp is an OIDC/OAuth identity provider running as a tsnet node, for SSO to
self-hosted apps and authenticated MCP servers
([docs](https://tailscale.com/docs/features/tsidp),
[repo](https://github.com/tailscale/tsidp)).

- Experimental community project, pre-1.0, breaking changes possible; needs
  `TAILSCALE_USE_WIP_CODE=1`. Development moved to `tailscale/tsidp` (image
  `ghcr.io/tailscale/tsidp:latest`); `cmd/tsidp` in `tailscale/tailscale` is
  unmaintained. Needs MagicDNS and HTTPS.
- Persistent state is mandatory (`-dir` / `TS_STATE_DIR`); without it tsidp
  re-registers on every restart, losing dynamic OIDC clients and sessions.
- With an OAuth client secret (`tskey-client-...`) as `TS_AUTHKEY`, also set
  `TS_ADVERTISE_TAGS` / `-advertise-tags` and define the tag in `tagOwners`.
  `TS_AUTHKEY_FILE` alongside `TS_AUTHKEY` prevents startup.
- Tailnet-only by default. `-funnel` (`TSIDP_USE_FUNNEL=1`) exposes it publicly
  (hostname in CT logs); use only when a SaaS app outside must reach it.
- Authorization is the `tailscale.com/cap/tsidp` app capability in a grant. The
  admin UI and dynamic client registration are denied by default; enable with
  `allow_admin_ui: true` and `allow_dcr: true`. `users` and `resources` gate
  token requests (STS also needs `-enable-sts` / `TSIDP_ENABLE_STS=1`);
  `extraClaims` adds claims, `includeInUserInfo` returns them from `/userinfo`.
  The schema may change.
