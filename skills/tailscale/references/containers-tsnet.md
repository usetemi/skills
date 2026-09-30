# Tailscale Containers, tailscaled, And tsnet

Kubernetes: [kubernetes.md](kubernetes.md). No `/dev/net/tun` (Cloud Run,
Heroku, Lambda, Actions, unprivileged LXC): use userspace networking.

## Docker Image (containerboot)

Images: `docker.io/tailscale/tailscale` and `ghcr.io/tailscale/tailscale`, with
tags `latest`, `stable`, `vX.Y.Z`, `unstable-vX.Y.Z`. Pin an explicit version
in production.

`TS_USERSPACE` defaults to `true`. Kernel networking needs
`TS_USERSPACE=false`, `/dev/net/tun`, and `NET_ADMIN`. The current standalone
guide adds `net_admin` and `net_raw` and does not use `SYS_MODULE`; older
compose files listing `sys_module` are stale.

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
    volumes: [tailscale-state:/var/lib/tailscale]
    devices: [/dev/net/tun:/dev/net/tun]
    cap_add: [net_admin, net_raw]
volumes: {tailscale-state: {}}
```

Sidecar: one `tailscale/tailscale` container per service (avoids port
conflicts); give the app `network_mode: service:<tailscale-service>` to share
its network namespace with no host port mapping.

Variable gotchas ([params](https://tailscale.com/docs/features/containers/docker/docker-params)):

- `TS_EXTRA_ARGS` is appended to `tailscale up` (`--advertise-tags`,
  `--accept-routes`, `--ssh`, `--advertise-exit-node`); set-only flags fail
  there. `TS_TAILSCALED_EXTRA_ARGS` goes to `tailscaled`.
- `TS_ROUTES` only advertises routes. Accepting routes is a separate
  `--accept-routes` in `TS_EXTRA_ARGS`. Advertised, approved, and accepted
  are three separate steps; see
  [routing-connectors.md](routing-connectors.md#route-injection).
- `TS_HOSTNAME` defaults to Docker's random hostname; set it (or compose
  `hostname:`). `TS_ACCEPT_DNS` defaults to off, so MagicDNS names do not
  resolve in the container unless `TS_ACCEPT_DNS=true`.
- `TS_DEST_IP`, `TS_EXPERIMENTAL_DEST_DNS_NAME`, `TS_TAILNET_TARGET_IP`, and
  `TS_TAILNET_TARGET_FQDN` fail at startup in userspace mode
  ("... is not supported with TS_USERSPACE"); use kernel mode.
- `TS_SOCKET`: docs say `/var/run/tailscale/tailscaled.sock`, but
  containerboot defaults to `/tmp/tailscaled.sock`; use
  `docker exec <c> tailscale --socket=/tmp/tailscaled.sock status` or set
  `TS_SOCKET`.
- `TS_ENABLE_HEALTH_CHECK=true` serves `/healthz`, `TS_ENABLE_METRICS=true`
  serves `/metrics` (client 1.78+), both on `TS_LOCAL_ADDR_PORT` (default
  `[::]:9002`, all interfaces, unauthenticated; restrict it).
  `TS_HEALTHCHECK_ADDR_PORT` is deprecated. `TS_BOOT_TIMEOUT` (default 60s,
  images 1.102.3+) bounds the first control-plane connection wait.

### State

If neither `TS_STATE_DIR` nor a Kubernetes secret is set, containerboot runs
`tailscaled --state=mem: --statedir=/tmp`: the container registers as a new
node on every start. Persist `TS_STATE_DIR` on a volume. Since container
1.90.8, a missing `TS_STATE_DIR` no longer disables Tailnet Lock signing
checks (TS-2025-008); set it anyway on Tailnet Lock tailnets.

Never bake a state directory into an image or clone a VM/file system holding
`/var/lib/tailscale`: clones share a node key and `100.x` address (admin
console shows "Duplicate node key"). Fix by removing Tailscale config and state
on one copy and re-registering
([troubleshooting](https://tailscale.com/docs/reference/troubleshooting/network-configuration/multiple-devices-same-100-x-ip-address)).
For identical containers, give each a reusable auth key at first start.

`TS_AUTH_ONCE` defaults to `false`, so the auth key is used on every start
even with persisted state; `true` logs in only when state needs login. Lead
(issue #20728, open): with it, flags passed only through `TS_EXTRA_ARGS` may
apply on first boot only; if a change seems ignored, use `tailscale set` or
drop `TS_AUTH_ONCE`.

### Credentials

- `TS_AUTHKEY`: auth key.
- `TS_CLIENT_ID` + `TS_CLIENT_SECRET`: OAuth client.
- `TS_CLIENT_ID` + `TS_ID_TOKEN` or `TS_AUDIENCE`: WIF (image 1.94.1+).
- `TS_CLIENT_ID`, `TS_CLIENT_SECRET`, `TS_ID_TOKEN`, and `TS_AUTHKEY` accept a
  `file:` prefix naming a path (containerboot source comment; the params page
  omits it for `TS_AUTHKEY`). No `TS_AUTHKEY_FILE` variable exists. containerboot
  rejects `TS_AUTHKEY` combined with any OAuth/WIF variable.
- An OAuth client secret passed as `TS_AUTHKEY` needs the `auth_keys` scope and
  the tag via `--advertise-tags` in `TS_EXTRA_ARGS`. It registers an ephemeral
  node unless suffixed `?ephemeral=false`; see
  [automation-api.md](automation-api.md#ephemeral-defaults-for-oauth-and-wif-registration)
  ([OAuth clients](https://tailscale.com/docs/features/oauth-clients)).

Auth key expiry and revocation do not remove enrolled devices
([automation-api.md](automation-api.md#auth-keys)). Keep keys out of
Dockerfiles and committed compose files.

### Serve Config In A Container

`TS_SERVE_CONFIG` points to an `ipn.ServeConfig` JSON file (export with
`tailscale serve status --json`). containerboot watches it, reapplies on
change, and replaces the literal `${TS_CERT_DOMAIN}` with the node FQDN.

- Bind-mount the containing directory, not the single file, or edits are not
  detected. `TS_SERVE_CONFIG` cannot be combined with `TS_DEST_IP`.
- Funnel is public and needs the `funnel` node attribute for the container's
  tag: [expose-services.md](expose-services.md#funnel-public).
- Since container 1.96.5, containerboot auto-advertises Tailscale Services
  defined in that file (`TS_EXPERIMENTAL_SERVICE_AUTO_ADVERTISEMENT`, default
  `true`, non-Kubernetes only; advertisement is turned off on shutdown).
  Before 1.96.5, run `tailscale serve advertise svc:<name>` in the container.
  Advertising is not approval: the host must be a tagged node and the Service
  approved by an admin or `autoApprovers.services`. Access policy still gates
  clients.
- Lead (issue #21455, open): with `TS_STATE_DIR` + `TS_AUTH_ONCE=true`,
  Services may stop being advertised after a restart (`tailscale debug prefs`
  shows `AdvertiseServices` null); workaround `tailscale serve advertise
  svc:<name>`.

### Docker On A Tailscale Linux Host

A Linux host running both can log "Stateful filtering is enabled and Docker
was detected", and containers may fail to resolve DNS or reach tailnet nodes.
Documented fixes: `tailscale set --stateful-filtering=false`,
`dockerd --iptables=false`, `tailscale up --netfilter-mode=off` (then manage
rules yourself), Serve/Funnel instead of Docker port mappings, or iptables
rules allowing `ESTABLISHED,RELATED`
([message](https://tailscale.com/docs/reference/messages/client/docker-stateful-filtering)).

## Userspace Networking

`tailscaled --tun=userspace-networking` (also the image default) creates no
`tailscale0` interface; apps reach the tailnet only through a proxy
([docs](https://tailscale.com/docs/concepts/userspace-networking)).

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

- A userspace subnet router or exit node terminates TCP/UDP and originates new
  connections (not end-to-end), supports TCP, UDP, and reconstructed ICMP ping
  only (no SCTP), and is for light use; use kernel mode for heavy load
  ([comparison](https://tailscale.com/docs/reference/kernel-vs-userspace-routers)).
- Lead (issue #21511, open): a userspace Service host may source outbound
  proxy connections from the Service VIP, so destinations drop them. Prefer
  kernel mode for Service hosts that originate connections.
- The `tailscale ssh` wrapper works in userspace mode via a ProxyCommand
  through tailscaled; plain `ssh` cannot reach tailnet IPs there.
- `tailscale wait` ([automation-api.md](automation-api.md#non-interactive-cli))
  waits only for tailscaled in userspace mode. `tailscale up --timeout`
  (default 0, blocks forever) makes a bad key or unreachable control plane
  fail instead of hang.

## Serverless And PaaS

Prefer ephemeral, tagged keys or OAuth/WIF and explicit teardown
([automation-api.md](automation-api.md#ephemeral-nodes)). A shutdown logout can
hit its 5s timeout, leaving the node until garbage collection (about an hour;
issue #14805); a restarted `--state=mem:` node may register as `hostname-1`.

Lambda ([docs](https://tailscale.com/docs/install/cloud/aws/aws-lambda)): copy
`/usr/local/bin/tailscaled` and `tailscale` from
`docker.io/tailscale/tailscale:stable`, symlink the `tailscale` directories
under `/var/run`, `/var/cache`, `/var/lib`, `/var/task` to `/tmp/tailscale`
(read-only outside `/tmp`), then in the bootstrap run `tailscaled
--tun=userspace-networking --socks5-server=localhost:1055 &`, `tailscale up
--auth-key=...`, and the app with `ALL_PROXY=socks5://localhost:1055/`. Fly.io's
[guide](https://tailscale.com/docs/install/cloud/flydotio) runs kernel-mode
`tailscaled` with `--state=/var/lib/tailscale/tailscaled.state` and
`apk add iptables ip6tables`.

## tailscaled On Linux Servers

Set flags with `FLAGS=` in `/etc/default/tailscaled`; logs via
`journalctl -u tailscaled` or `tailscale debug daemon-logs`.
[Flags](https://tailscale.com/docs/reference/tailscaled): `--statedir` holds
config state, TLS certs, and Taildrop files. `--state` takes a file path
(default `<statedir>/tailscaled.state`), `kube:<secret>`, `arn:aws:ssm:...`, or
`mem:` for an ephemeral node. `--no-logs-no-support` also disables technical
support. `--syspolicy-file` defaults to `/etc/tailscale/syspolicy.json`.

`--state=arn:aws:ssm:<region>:<acct>:parameter/<name>` suits hosts with no
persistent disk. Append `?kmsKey=<key id|alias|ARN>` to encrypt; otherwise
state is unencrypted. State holds the node private key: restrict IAM access.

`--encrypt-state` (TPM 2.0), version-dependent defaults, and failed-unseal
recovery: [production-diagnostics.md](production-diagnostics.md#node-state-encryption).
Set the flag explicitly.

### Declarative Config File (alpha)

`tailscaled --config=/path/config.json` (also `vm:user-data` on EC2; prefix
`optional:` to boot unconfigured when the source is absent). Only `"version":
"alpha0"` is required. Not auto-discovered; read once at startup (apply edits
with `tailscale debug reload-config` or a restart). `"locked"` defaults to
`true` and blocks `tailscale set`. `authKey` supports `file:` and is re-read at
each control-plane authentication. `acceptRoutes` defaults to `false` on Linux
([docs](https://tailscale.com/docs/reference/tailscaled/tailscaled-config-file)).

## tsnet (Go)

`tsnet.Server` embeds a node in a Go program
([API](https://tailscale.com/docs/reference/tsnet-server-api)). Authentication
order: `Server.AuthKey`, `TS_AUTHKEY`, `TS_AUTH_KEY`, OAuth
client secret (`Server.ClientSecret` or `TS_CLIENT_SECRET`), workload identity
federation (`ClientID` + `IDToken` or `Audience`), then an interactive login
URL.

- OAuth and WIF require at least one tag in `AdvertiseTags`.
- WIF needs `import _ "tailscale.com/feature/identityfederation"` or the
  fields are ignored.
- If the node is already enrolled in `Dir`/`Store`, the auth key is ignored
  ("Authkey is set; but state is ... Ignoring authkey") unless
  `TSNET_FORCE_LOGIN=1`. A stale state dir silently keeps the old identity.

State and lifecycle:

- Set `Dir` to a persistent path. The default is a per-binary directory under
  `os.UserConfigDir`, which is ephemeral in most containers and unresolvable
  when neither `$XDG_CONFIG_HOME` nor `$HOME` is set. Current source creates
  `Dir` (mode 0700) although the docs page says it must already exist.
- Multiple Servers per process need distinct `Dir` and `Hostname`.
- An in-memory `Store` is accepted only with `Ephemeral: true` (registers an
  ephemeral node).
- Backend logs are discarded unless `Logf` is set; client logs upload to
  `log.tailscale.com` by default. `Up(ctx)` blocks until connected; `Start`
  does not.

Listeners:

- `Listen` is tailnet-private. `ListenTLS` and `ListenFunnel` need MagicDNS
  and HTTPS. Funnel is public, supports TCP on 443, 8443, and 10000, and needs
  the `funnel` node attribute.
- `ListenService` requires a tagged node (`ErrUntaggedServiceHost`) plus
  Service approval. `ListenSSH` requires
  `import _ "tailscale.com/feature/ssh"`.
- Identify callers with `srv.LocalClient().WhoIs`.
