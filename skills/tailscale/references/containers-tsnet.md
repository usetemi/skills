# Tailscale Containers, tailscaled, And tsnet

Official docs:

- Docker image parameters: https://tailscale.com/docs/features/containers/docker/docker-params
- Standalone Docker guide: https://tailscale.com/docs/features/containers/docker/how-to/connect-docker-standalone
- Userspace networking: https://tailscale.com/docs/concepts/userspace-networking
- tailscaled reference: https://tailscale.com/docs/reference/tailscaled
- tailscaled config file: https://tailscale.com/docs/reference/tailscaled/tailscaled-config-file
- Node state encryption: https://tailscale.com/docs/features/secure-node-state-storage
- Ephemeral nodes: https://tailscale.com/docs/features/ephemeral-nodes
- tsnet server API: https://tailscale.com/docs/reference/tsnet-server-api
- Lambda: https://tailscale.com/docs/install/cloud/aws/aws-lambda
- Fly.io: https://tailscale.com/docs/install/cloud/flydotio
- Kubernetes (operator, proxies): see [kubernetes.md](kubernetes.md).

## Choose A Shape

| Situation | Use |
| --- | --- |
| Container should be a node, app sees the tailnet | Sidecar (`tailscale/tailscale`) sharing a network namespace |
| No `/dev/net/tun` (Cloud Run, Heroku, Lambda, Actions, unprivileged LXC) | Userspace networking plus SOCKS5/HTTP proxy |
| Go app that should be its own node | `tsnet` |
| Non-Go app | Sidecar, or userspace `tailscaled` with the proxy |
| Server or VM you administer | `tailscaled` under systemd |

## Docker Image (containerboot)

Images: `docker.io/tailscale/tailscale` and `ghcr.io/tailscale/tailscale`, with
tags `latest`, `stable`, `vX.Y.Z`, `unstable-vX.Y.Z`. Pin an explicit version
in production; a community report says an image bump can change behavior on
restart with preserved state (issue #12307, 2024).

`TS_USERSPACE` defaults to `true`. Kernel networking needs
`TS_USERSPACE=false`, `/dev/net/tun`, and `NET_ADMIN`. The current standalone
guide adds `net_admin` and `net_raw` and does not use `SYS_MODULE`; older blog
compose files that list `sys_module` are stale.

```yaml
services:
  tailscale:
    image: tailscale/tailscale:stable   # pin a version in production
    hostname: my-app
    environment:
      TS_AUTHKEY: ${TS_AUTHKEY}
      TS_EXTRA_ARGS: --advertise-tags=tag:container
      TS_STATE_DIR: /var/lib/tailscale
      TS_USERSPACE: "false"
    volumes:
      - tailscale-state:/var/lib/tailscale
    devices:
      - /dev/net/tun:/dev/net/tun
    cap_add:
      - net_admin
      - net_raw
volumes:
  tailscale-state:
```

Variable gotchas ([params](https://tailscale.com/docs/features/containers/docker/docker-params)):

- `TS_EXTRA_ARGS` is appended to `tailscale up` (`--advertise-tags`,
  `--accept-routes`, `--ssh`, `--advertise-exit-node`); set-only flags fail
  there. `TS_TAILSCALED_EXTRA_ARGS` goes to `tailscaled` (for example
  `--verbose=2`).
- `TS_ROUTES` only advertises routes. Accepting routes is a separate
  `--accept-routes` in `TS_EXTRA_ARGS`. Advertised, approved, and accepted
  are three separate steps; see
  [routing-connectors.md](routing-connectors.md#route-injection).
- `TS_HOSTNAME` defaults to Docker's random hostname; set it (or compose
  `hostname:`).
- `TS_ACCEPT_DNS` defaults to not accepting tailnet DNS, so MagicDNS names do
  not resolve inside the container unless `TS_ACCEPT_DNS=true`.
- `TS_DEST_IP`, `TS_EXPERIMENTAL_DEST_DNS_NAME`, `TS_TAILNET_TARGET_IP`, and
  `TS_TAILNET_TARGET_FQDN` fail at startup in userspace mode
  ("... is not supported with TS_USERSPACE"). Use kernel mode for them.
- `TS_SOCKET`: docs say `/var/run/tailscale/tailscaled.sock`, but
  containerboot defaults to `/tmp/tailscaled.sock`. Inspect a running
  container with `docker exec <c> tailscale --socket=/tmp/tailscaled.sock status`
  or set `TS_SOCKET`.
- `TS_ENABLE_HEALTH_CHECK=true` serves `/healthz`, `TS_ENABLE_METRICS=true`
  serves `/metrics` (client 1.78+), both on `TS_LOCAL_ADDR_PORT` (default
  `[::]:9002`, all interfaces, unauthenticated; restrict it).
  `TS_HEALTHCHECK_ADDR_PORT` is deprecated. `TS_BOOT_TIMEOUT` (default 60s,
  images 1.102.3+) waits longer for the first coordination-server connection.

### State

If neither `TS_STATE_DIR` nor a Kubernetes secret is set, containerboot runs
`tailscaled --state=mem: --statedir=/tmp`: no persisted identity, and the
container registers as a new node on every start. Persist `TS_STATE_DIR` on a
volume. Since container 1.90.8, a missing `TS_STATE_DIR` no longer disables
Tailnet Lock signing checks (TS-2025-008), but set it anyway on Tailnet Lock
tailnets ([changelog](https://tailscale.com/changelog)).

Never bake a state directory into an image or clone a VM/file system holding
`/var/lib/tailscale`: clones share a node key, get the same `100.x` address,
and the admin console shows a "Duplicate node key" badge. Fix by removing
Tailscale config and state on one copy and re-registering
([troubleshooting](https://tailscale.com/docs/reference/troubleshooting/network-configuration/multiple-devices-same-100-x-ip-address)).
For fleets of identical containers, give each a reusable auth key at first
start instead.

`TS_AUTH_ONCE` defaults to `false`, so the auth key is used on every start
even with persisted state. Set `TS_AUTH_ONCE=true` to log in only when state
needs login.

Diagnostic lead (community, issue #20728, 2026-08, open, no staff reply): with
`TS_AUTH_ONCE=true`, flags passed only through `TS_EXTRA_ARGS` (for example
`--accept-routes`) may apply on first boot only. If a flag change seems
ignored, use `tailscale set` in the container or drop `TS_AUTH_ONCE`.

### Credentials

- `TS_AUTHKEY`: auth key.
- `TS_CLIENT_ID` + `TS_CLIENT_SECRET`: OAuth client.
- `TS_CLIENT_ID` + `TS_ID_TOKEN` or `TS_AUDIENCE`: workload identity
  federation (container image 1.94.1+).
- `TS_CLIENT_ID`, `TS_CLIENT_SECRET`, `TS_ID_TOKEN` accept a `file:` prefix
  naming a path, as does `TS_AUTHKEY` (containerboot source comment; the
  params page does not list it for `TS_AUTHKEY`). containerboot rejects
  `TS_AUTHKEY` combined with any of the OAuth/WIF variables.
- An OAuth client secret passed as `TS_AUTHKEY` needs the `auth_keys` scope and
  the tag via `--advertise-tags` in `TS_EXTRA_ARGS`. It registers an ephemeral
  node unless suffixed `?ephemeral=false`; see
  [automation-api.md](automation-api.md#ephemeral-defaults-for-oauth-and-wif-registration)
  ([OAuth clients](https://tailscale.com/docs/features/oauth-clients)).
- No `TS_AUTHKEY_FILE` variable exists (issue #14210 open); use the `file:`
  prefix above.

Auth key expiry and revocation do not remove enrolled devices; see
[automation-api.md](automation-api.md#auth-keys). Keep keys out of Dockerfiles
and committed compose files.

### Serve Config In A Container

`TS_SERVE_CONFIG` points to an `ipn.ServeConfig` JSON file (export with
`tailscale serve status --json`). containerboot watches it, reapplies on
change, and replaces the literal `${TS_CERT_DOMAIN}` with the node FQDN.

- Bind-mount the containing directory, not the single file, or edits are not
  detected.
- It cannot be combined with `TS_DEST_IP`.
- Serve is tailnet-private; Funnel is public and needs the `funnel` node
  attribute for the container's tag. See
  [expose-services.md](expose-services.md#funnel-public).
- Since container 1.96.5, containerboot auto-advertises Tailscale Services
  defined in that file (`TS_EXPERIMENTAL_SERVICE_AUTO_ADVERTISEMENT`, default
  `true`, non-Kubernetes only; advertisement is turned off on shutdown).
  Before 1.96.5, run `tailscale serve advertise svc:<name>` in the container.
  Advertising is not approval: the host must be a tagged node and the Service
  approved by an admin or `autoApprovers.services`. Access policy still gates
  clients.

Diagnostic lead (community, issue #21455, 2026-09, open with fix PR #21462):
with `TS_STATE_DIR` + `TS_AUTH_ONCE=true`, Services may stop being advertised
after the first restart; clients get connection refused and
`tailscale debug prefs` shows `AdvertiseServices` null. Verify advertisement
after a restart; workaround is `tailscale serve advertise svc:<name>` in the
container.

### Sidecar Pattern

Run one `tailscale/tailscale` container per service and give the app
`network_mode: service:<tailscale-service>` so both share a network namespace
and the app needs no host port mapping. Tailscale recommends one sidecar per
service to avoid port conflicts
([Docker guide](https://tailscale.com/blog/docker-tailscale-guide), 2024).

Docker DNS lead (community, issue #14467, open): Docker's
`options edns0 trust-ad ndots:0` in a container's `resolv.conf` can break
short MagicDNS names. Use FQDNs or set a high `ndots` through `dns_opt`.

### Docker On A Tailscale Linux Host

Running Tailscale on a Linux host that also runs Docker can log "Stateful
filtering is enabled and Docker was detected", and containers may fail to
resolve DNS or reach tailnet nodes. Documented fixes: `tailscale set
--stateful-filtering=false`, `dockerd --iptables=false`, `tailscale up
--netfilter-mode=off` (then manage rules yourself), expose services through
Serve/Funnel instead of Docker port mappings, or add iptables rules allowing
`ESTABLISHED,RELATED`
([message](https://tailscale.com/docs/reference/messages/client/docker-stateful-filtering)).

## Userspace Networking

`tailscaled --tun=userspace-networking` (also the image default) creates no
`tailscale0` interface. Apps reach the tailnet only through a proxy
([docs](https://tailscale.com/docs/concepts/userspace-networking)).
`tailscaled --help` labels the flag value beta; the docs page carries no stage
note.

```bash
tailscaled --tun=userspace-networking \
  --socks5-server=localhost:1055 \
  --outbound-http-proxy-listen=localhost:1055 &
tailscale up --auth-key=file:/run/secrets/ts_authkey
ALL_PROXY=socks5://localhost:1055/ ./app
```

SOCKS5 needs client 1.8+, the HTTP proxy 1.16+. On Ubuntu/RHEL set
`FLAGS="--tun=userspace-networking"` in `/etc/default/tailscaled`.

Limits:

- A subnet router or exit node in userspace mode terminates TCP/UDP and
  originates new connections (not end-to-end), supports TCP, UDP, and
  reconstructed ICMP ping only (no SCTP), and is meant for light use. Use
  kernel mode for heavily used routers
  ([comparison](https://tailscale.com/docs/reference/kernel-vs-userspace-routers)).
- Leads (community, open issues): proxy egress does not resolve split-DNS
  domains (#4677); a userspace node hosting a Tailscale Service may source
  outbound proxy connections from the Service VIP so the destination drops
  them (#21511, 2026-09). Prefer kernel mode for Service hosts that also
  originate connections.
- `tailscale ssh` (the wrapper, not Tailscale SSH itself) works in userspace
  mode by supplying a ProxyCommand through tailscaled; plain `ssh` cannot reach
  tailnet IPs there.
- `tailscale wait` ([automation-api.md](automation-api.md#non-interactive-cli))
  waits only for tailscaled in userspace mode. `tailscale up --timeout`
  (default 0, blocks forever) makes a bad key or unreachable control plane fail
  instead of hang.

## Serverless And PaaS

- Prefer ephemeral, tagged keys or OAuth/WIF and explicit teardown.
- Lambda: copy `/usr/local/bin/tailscaled` and `tailscale` from
  `docker.io/tailscale/tailscale:stable`, symlink the `tailscale` directories
  under `/var/run`, `/var/cache`, `/var/lib`, `/var/task` to `/tmp/tailscale`
  (read-only outside `/tmp`), then in the bootstrap run `tailscaled
  --tun=userspace-networking --socks5-server=localhost:1055 &`, `tailscale up
  --auth-key=...`, and the app with `ALL_PROXY=socks5://localhost:1055/`.
- Fly.io's guide runs `tailscaled` in kernel mode (no
  `--tun=userspace-networking`) with
  `--state=/var/lib/tailscale/tailscaled.state` and `apk add iptables
  ip6tables`. Community report: Alpine on an existing Fly machine may need a
  machine update for nftables support (issue #10540).

### Ephemeral Nodes

Lifecycle, removal timing, and teardown are in
[automation-api.md](automation-api.md#ephemeral-nodes).

Diagnostic lead (issue #14805, open): a Tailscale engineer reproduced the
shutdown logout hitting its 5s timeout, leaving the node until garbage
collection (roughly an hour). Community reporters also see a restarted
`--state=mem:` node register as `hostname-1`.

## tailscaled On Linux Servers

Set flags with `FLAGS=` in `/etc/default/tailscaled` (as in userspace mode
above); logs via
`journalctl -u tailscaled` or `tailscale debug daemon-logs`.

```bash
tailscaled --statedir=/var/lib/tailscale --tun=userspace-networking
```

Flags (local help, [reference](https://tailscale.com/docs/reference/tailscaled)):

- `--statedir`: config state, TLS certs, Taildrop files.
- `--state`: file path (default `<statedir>/tailscaled.state`),
  `kube:<secret>`, `arn:aws:ssm:...`, or `mem:` for an ephemeral node.
- `--config`: declarative config file.
- `--encrypt-state`, `--hardware-attestation`, `--no-logs-no-support` (also
  disables technical support), `--cleanup`, `--port`, `--debug=host:port`,
  `--syspolicy-file` (default `/etc/tailscale/syspolicy.json`).

### State In AWS SSM

`--state=arn:aws:ssm:<region>:<acct>:parameter/<name>` stores state in
Systems Manager Parameter Store for hosts with no persistent disk. Append
`?kmsKey=<key id|alias|ARN>` to encrypt with KMS; without it the state is not
encrypted. State holds the node private key: treat the parameter as a secret
and restrict IAM access to it.

### State Encryption

`--encrypt-state` (TPM 2.0), its version-dependent defaults, and recovery from a
failed unseal are in
[production-diagnostics.md](production-diagnostics.md#node-state-encryption).
Set the flag explicitly.

### Declarative Config File (alpha)

`tailscaled --config=/path/config.json` (also `vm:user-data` on EC2; prefix
`optional:` to boot unconfigured when the source is absent). Only `"version":
"alpha0"` is required. It is not auto-discovered and is read once at startup;
apply edits with `tailscale debug reload-config` or a restart. `"locked"`
defaults to `true` and blocks `tailscale set`. `authKey` supports a `file:`
prefix and is re-read at each control-plane authentication. `acceptRoutes`
defaults to `false` on Linux
([docs](https://tailscale.com/docs/reference/tailscaled/tailscaled-config-file)).

## tsnet (Go)

`tsnet.Server` embeds a node in a Go program
([API](https://tailscale.com/docs/reference/tsnet-server-api)).

Authentication order: `Server.AuthKey`, `TS_AUTHKEY`, `TS_AUTH_KEY`, OAuth
client secret (`Server.ClientSecret` or `TS_CLIENT_SECRET`), workload identity
federation (`ClientID` + `IDToken` or `Audience`), then an interactive login
URL.

- OAuth and WIF require at least one tag in `AdvertiseTags`.
- WIF is not linked in by default: add
  `import _ "tailscale.com/feature/identityfederation"` or the fields are
  ignored.
- If the node is already enrolled in `Dir`/`Store`, the auth key is ignored
  ("Authkey is set; but state is ... Ignoring authkey") unless
  `TSNET_FORCE_LOGIN=1`. A stale state dir silently keeps the old identity.

State and lifecycle:

- Set `Dir` to a persistent path. The default is a per-binary directory under
  `os.UserConfigDir`, which is ephemeral in most containers and unresolvable
  when neither `$XDG_CONFIG_HOME` nor `$HOME` is set. The docs page says `Dir`
  must already exist and its example calls `os.MkdirAll`; current source also
  creates it (mode 0700).
- Multiple Servers in one process need distinct `Dir` values; give each its
  own `Hostname` too.
- `Ephemeral: true` registers an ephemeral node; an in-memory `Store` is
  accepted only with `Ephemeral: true`.
- Backend logs are discarded unless `Logf` is set; set it when debugging.
  Client logs upload to `log.tailscale.com` by default.
- `Up(ctx)` blocks until connected; `Start` does not.

Listeners:

- `Listen` is tailnet-private.
- `ListenTLS` and `ListenFunnel` need MagicDNS and HTTPS. Funnel is public
  and supports TCP on 443, 8443, and 10000; it also needs the `funnel` node
  attribute.
- `ListenService` requires a tagged node (`ErrUntaggedServiceHost`) plus
  Service approval.
- `ListenSSH` requires `import _ "tailscale.com/feature/ssh"`.
- Identify callers with `srv.LocalClient().WhoIs`.

Non-Go apps: use a sidecar or userspace `tailscaled` with the proxy.
