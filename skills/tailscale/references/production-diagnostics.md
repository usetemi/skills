# Tailscale Production Diagnostics

Official docs:

- Troubleshooting index: https://tailscale.com/docs/reference/troubleshooting
- Health and error message IDs: https://tailscale.com/docs/reference/messages
- CLI reference: https://tailscale.com/docs/reference/tailscale-cli
- Connection types: https://tailscale.com/docs/reference/connection-types
- Device connectivity (NAT): https://tailscale.com/docs/reference/device-connectivity
- Logging: https://tailscale.com/docs/features/logging
- Client metrics: https://tailscale.com/docs/reference/tailscale-client-metrics
- Key expiry: https://tailscale.com/docs/features/access-control/key-expiry
- Coordination server outage: https://tailscale.com/docs/reference/coordination-server-down

CLI flags drift from docs. Confirm with `<subcommand> --help` on the installed
version before scripting. Example: the grants troubleshooting page cites
`tailscale status --routes`, which client 1.102.4 rejects; use
`tailscale status --json` (peers expose `.PrimaryRoutes`, self exposes
`.AllowedIPs`) or `tailscale get advertise-routes` for this node's own setting.

## Safe Read-Only Commands

Start here during incidents and reviews:

```bash
tailscale version --daemon --upstream   # client, daemon, newest release
tailscale status                        # add --active --peers=false --self=false --header to trim
tailscale status --json                 # schema is ipnstate.Status; it changes between releases
tailscale netcheck --format json
tailscale ip
tailscale whoami                        # 1.102.1+: whois for this node
tailscale whois --proto tcp <ip>:<port> # user, tags, caps a source resolves to
tailscale dns status
tailscale get --set-flags               # prints `tailscale set` args; snapshot before changing
tailscale service list                  # 1.102.1+: Services visible to this node
tailscale serve get-config --all
tailscale funnel status
tailscale syspolicy list                # managed clients only
```

`serve status` and `serve status --json` differ; `serve get-config --all` is the
complete Service inventory ([expose-services.md](expose-services.md)).

Hosts with systemd: `systemctl status tailscaled`,
`journalctl -u tailscaled --since '1 hour ago'`. Kubernetes:

```bash
kubectl get pods -n tailscale
kubectl logs -n tailscale deployment/operator --tail=200   # Helm default name; use your fullnameOverride if set
```

Other local log locations
([logging](https://tailscale.com/docs/features/logging)): Windows
`C:\ProgramData\Tailscale`; macOS Console.app filtered on `IPN`; Android
`logcat` for `com.tailscale.ipn`. Client operational logs are readable only on
the node. `tailscale debug daemon-logs [--verbose N] [--time]` live-tails on any
platform with the CLI.

## Layered Connectivity Triage

1. Is `tailscaled` running and logged in? Read health warnings in
   `tailscale status` first ([message IDs](#health-warnings)).
2. Does `tailscale status` show both peers? Path column: `direct <ip:port>`,
   `relay "<region>"` (DERP), `peer-relay <ip:port>:vni:<id>`. A naive
   `grep relay` also matches peer-relay.
3. Test with the right ping
   ([TCP between two devices](https://tailscale.com/docs/reference/troubleshooting/network-configuration/tcp-connection-two-devices)):
   - `ping 100.x` is OS ICMP over the tailnet.
   - `tailscale ping 100.x` tests whether the two tailscaled processes reach
     each other (disco) and by which path. It stops after 10 pings or the first
     direct path; tune with `--c N` (0 = infinite), `--until-direct=false`,
     `--timeout`, `--size`.
   - `tailscale ping --tsmp` goes through WireGuard and skips both host network
     stacks; `--icmp` skips only the local OS stack; `--peerapi` tests PeerAPI.
   - If `tailscale ping` works but ping/TCP does not, an OS firewall or an
     access rule on one side blocks the traffic.
4. A DERP reply on the first pings is normal: all connections start relayed and
   upgrade to direct after NAT traversal. Tailscale re-checks periodically and
   a connection can fall back to relayed
   ([connection types](https://tailscale.com/docs/reference/connection-types)).
5. Does the access policy allow source to destination and port? Use
   `tailscale whois` on the destination to see what identity the source
   resolves to.
6. Subnet routes or app connectors: check each route gate in turn
   ([routing-connectors.md](routing-connectors.md#route-injection)).
7. DNS: does `tailscale dns status` (or `tailscale dns query <name>`) show the
   expected MagicDNS or split DNS?
8. Serve, Funnel, Services: does `serve get-config --all` show the expected
   target and protocol? Serve is private to the tailnet; Funnel is public.
9. Large packets fail but small ones work: the Tailscale interface MTU is 1280
   and larger packets from other interfaces can be dropped silently. Confirm
   with tcpdump; fix with a lower LAN MTU or MSS clamping.

Peer-relay setup and verification are in
[routing-connectors.md](routing-connectors.md#peer-relays); `tailscale ping`
shows `via peer-relay(...)` on that path.

### Reading netcheck

([device connectivity](https://tailscale.com/docs/reference/device-connectivity))

- `UDP: false` means no outbound UDP; expect relay only.
- `MappingVariesByDestIP: true` means hard NAT, the main reason direct
  connections fail.
- `PortMapping` present (UPnP, NAT-PMP, PCP) makes the device generally easy
  NAT.
- `IPv4: No` means no IPv4 address or connectivity. `IPv6: No` means only that
  there is no IPv6 address; it does not imply broken connectivity.
- Direct if either side has no NAT or both are easy NAT. Relayed if both are
  hard NAT, or one hard and one easy. Relayed traffic uses a peer relay if one
  is available, otherwise DERP.
- Hard NAT on a subnet router, exit node, or app connector is worse than
  latency; see
  [routing-connectors.md](routing-connectors.md#connection-types-nat-traversal-derp).

## Firewall, UDP, and Ports

Tailscale needs no inbound ports. When direct connections fail, allow
([firewall ports](https://tailscale.com/docs/reference/faq/firewall-ports)):

- Outbound TCP 443 to `*:443` (control plane and DERP). Do not enumerate DERP
  hosts; partial blocks look like random peer failures.
- Outbound UDP from source port 41641 (default, configurable) to `*:*`.
- Outbound UDP to `*:3478` (STUN).
- Optional TCP 80 (control-plane connections and captive-portal detection;
  dropping it adds connection delays, falls back to 443, and breaks
  captive-portal detection).

Prefer domain rules. IP ranges are a snapshot; verify against the doc before
use (`login.tailscale.com` and `controlplane.tailscale.com` in
192.200.0.0/24 and 2606:B740:49::/48; `log.tailscale.com` in
199.165.136.0/24 and 2606:B740:1::/48). DERP servers are added and changed
often, so derive allowlists from the published DERP map
(`tailscale debug derp-map`). A public-IP host that blocks inbound UDP behaves
like easy NAT, not no-NAT.

When `not-in-map-poll` appears, test control-plane reachability with
`tailscale debug ts2021 --host controlplane.tailscale.com`. For `no-derp-home`
and `no-derp-connection`, check outbound TCP 443 to the DERP servers.

Linux firewall backend
([firewall mode](https://tailscale.com/docs/features/firewall-mode)):

- tailscaled uses iptables by default. `TS_DEBUG_FIREWALL_MODE=auto|iptables|nftables`
  in `/etc/default/tailscaled` is a temporary, unsupported debug knob.
  Confirm the chosen mode from the `router:` lines in `journalctl -ru tailscaled`.
- With neither backend available Tailscale runs degraded (more CPU); packet
  filtering still happens inside Tailscale, so security is unaffected.
- Related: `--netfilter-mode on|nodivert|off`, `--stateful-filtering`.
- Diagnostic lead, closed May 2025 (not a platform guarantee): kernels
  6.11.4-6.11.5 and 6.6.57-6.6.58 broke `ip6tables -j MARK`; a health error
  naming ip6tables MARK suggests the kernel. Staff recommended
  `TS_DEBUG_FIREWALL_MODE=nftables`
  ([issue 13863](https://github.com/tailscale/tailscale/issues/13863)).

## Health Warnings

Message pages live under `https://tailscale.com/docs/reference/messages/client/`.
The URL slug usually equals the reference ID but not always, so find the page
from the [messages index](https://tailscale.com/docs/reference/messages).
Warnings appear in `tailscale status` and in the `tailscaled_health_messages`
metric.

- `docker-stateful-filtering`: Docker iptables clashes with stateful filtering;
  remedies are in
  [containers-tsnet.md](containers-tsnet.md#docker-on-a-tailscale-linux-host).
- `resolv-conf-overwritten`: Linux DNS. Enable systemd-resolved; run tailscaled
  as root.
- `invalid-packet-filter`: the client rejects all packets for safety. Causes:
  invalid port, protocol, or CIDR in policy; the same policy tag assigned to
  both Funnel and an app connector; a host pf/iptables/nftables conflict.
- `no-derp-home` / `no-derp-connection`: cannot reach a relay; check TCP 443.
- `not-in-map-poll` ("Out of sync"): cannot reach the coordination server; peer
  reachability degrades over time.
- `ssh-unavailable-selinux-enabled`: tailscaled runs SSH in-process and SELinux
  can block it. Options: permissive mode, a custom SELinux policy, or OpenSSH
  over the tailnet. Ordinary networking is unaffected.
- IP forwarding: from 1.98.2 (1.98.1's Linux build was withdrawn) the Linux
  client reports missing forwarding on subnet routers and exit nodes as a
  health warning; the webhook events
  `subnetIPForwardingNotEnabled` and `exitNodeIPForwardingNotEnabled` cover it
  tailnet-wide. Treat router warnings about forwarding or reverse-path
  filtering as actionable.

CGNAT conflicts (`disable-ipv4` versus `disable-linux-cgnat-drop-rule`) are in
[routing-connectors.md](routing-connectors.md#ipv6-cgnat-and-addressing)
([CGNAT conflicts](https://tailscale.com/docs/reference/troubleshooting/network-configuration/cgnat-conflicts)).

## Debug, Bug Reports, and Metrics

`tailscale debug` is an unstable interface. Useful subcommands on 1.102.4:
`capture -o file.pcap` (decrypted tunnel traffic; needs the ts-dissector Lua
script in Wireshark), `derp-map`, `ts2021`, `netmap`, `prefs`, `hostinfo`,
`portmap`, `dial-types <host> <port>`, `resolve`,
`component-logs [magicsock|sockstats|syspolicy] --for 1h`, `daemon-logs`,
`peer-relay-servers`, `peer-relay-sessions`, `statedir`
([inspect packets](https://tailscale.com/docs/reference/troubleshooting/network-configuration/inspect-unencrypted-packets)).
Avoid in production: `derp-set-on-demand`, `break-tcp-conns`,
`break-derp-conns`, `pick-new-derp`, `force-netmap-update`, `set-expire`,
`rotate-disco-key`, `clear-netmap-cache`; `restun` and `rebind` also disrupt
magicsock.

`tailscale bugreport` is not read-only. It writes an identifier into the client
logs uploaded to Tailscale, together with health status and the coordination
server's netmap ([bug report](https://tailscale.com/docs/account/bug-report)).

- `--diagnose` adds system detail to those logs. `--record` writes one
  identifier, waits while you reproduce the issue, then writes a second on
  Enter; share both.
- It cannot be generated remotely; run it on the affected host.
- The identifier carries no PII; the logs it points to include the netmap.
  Those logs are readable on the node, so review them to see what support can
  see.
- With `--no-logs-no-support` no bug report is generated.

Client logging opt-out: `tailscaled --no-logs-no-support` or
`TS_NO_LOGS_NO_SUPPORT=true` (Linux `/etc/default/tailscaled`; Windows only the
env var in `%ProgramData%\Tailscale\tailscaled-env.txt`; macOS only the
open-source tailscaled variant). It disables support that needs the logs, and
the node reports no network flow logs (a blind spot in investigations).

Client metrics (1.78.0+)
([client metrics](https://tailscale.com/docs/reference/tailscale-client-metrics)):

- `tailscale metrics print` (Prometheus text) or `tailscale metrics write <path>`
  for node_exporter's textfile collector.
- HTTP `/metrics` at `http://100.100.100.100/metrics` on the host, or over the
  tailnet on port 5252 after `tailscale set --webclient` plus a policy rule for
  the monitor. `tailscale web --readonly --listen <ip:port>` does not expose it
  on the Tailscale IP.
- Distinct from `tailscale debug metrics` (internal).
- Alert on: `tailscaled_health_messages{type="warning"}`;
  `tailscaled_advertised_routes` minus `tailscaled_approved_routes` (routes
  awaiting approval); `tailscaled_home_derp_region_id`; relay fraction from
  `tailscaled_{inbound,outbound}_bytes_total` by `path` (`direct_*`, `derp`,
  `peer_relay_*`); `tailscaled_{inbound,outbound}_dropped_packets_total` with
  `reason="acl"` spikes (policy denies).
- `tailscaled_serve_{inbound,outbound}_bytes_total{service="svc:name"}` cover
  Tailscale Services hosts only, not device Serve or Funnel; require 1.102.1+.

## Logging and Audit

([logging overview](https://tailscale.com/docs/features/logging))

Configuration audit logs
([audit logging](https://tailscale.com/docs/features/logging/audit-logging)):
always on, cannot be disabled, retained 90 days. Export before then if longer
retention matters. Entries carry `eventGroupID` (one operation, many entries),
actor, target, and old/new values. Policy diffs contain the full old and new
policy, including comment-only changes.

- The audit-logging samples show `origin: ADMIN_UI` (and `NODE`) while the
  [deployment checklist](https://tailscale.com/docs/reference/deployment-checklist)
  SIEM rules match `ADMIN_CONSOLE`; inspect real events before writing a rule.
- In a GitOps-managed tailnet, alert on console-origin CREATE/UPDATE/DELETE as
  drift.

Network flow logs
([network flow logs](https://tailscale.com/docs/features/logging/network-flow-logs)):
off by default, need an Owner/Admin/Network admin/IT admin to start, retained
30 days, cover nodes on 1.34+, record only successful connections (denied
attempts are absent), arrive non-real-time, and have no console viewer (API or
log streaming only). Plan availability changes; check the doc.

- Only `Message.nodeId` is verified by Tailscale. `start`, `end`, `srcNode`,
  `dstNodes`, and counters are self-reported and can be spoofed; clocks skew.
  Both ends log a connection, so cross-check a suspect node against a trusted
  peer.
- Exit-node traffic omits protocol, source port, and destination unless
  exit-node destination logging is enabled (needs log streaming first and a
  sales contract; see [exit nodes](https://tailscale.com/docs/features/exit-nodes)).

API access:

```bash
GET https://api.tailscale.com/api/v2/tailnet/{tailnet}/logging/configuration?start=&end=  # scope logs:configuration:read
GET https://api.tailscale.com/api/v2/tailnet/{tailnet}/logging/network?start=&end=        # scope logs:network:read
```

`start` and `end` are RFC 3339. Neither endpoint paginates; the network
endpoint returns everything in the window, so query short windows. `end` later
than the latest ingested log does not block, so re-running a range can return
more entries. `go run tailscale.com/cmd/netlogfmt@latest` pretty-prints;
`--resolve-addrs=nodeids|names|users` maps addresses (clients 1.92+ embed node
info; older clients also need `--api-key` and `--tailnet-name`).

Log streaming
([log streaming](https://tailscale.com/docs/features/logging/log-streaming)):
audit and network logs are configured separately. Destinations include SIEMs
(Splunk HEC, Datadog, Elasticsearch, Axiom, Cribl, Panther), S3 and
S3-compatible stores, Google Cloud Storage, Azure Blob, and Vector for
anything else. SIEM URLs must be HTTPS. Object stores default to zstd and a
1-minute upload period; use an object key prefix (for example `audit-logs/`)
to share a bucket. Private endpoints (plain HTTP allowed):

- The host must be a tailnet node given by machine name, FQDN, or IPv6
  address; IPv4 is unsupported.
- Tailscale shares the node into its `logstream` tailnet and adds an accept
  rule for `logstream@tailscale` to your policy. With GitOps-managed policy
  the automatic edit fails: add the rule to git first, then add the endpoint.

Webhooks
([webhooks](https://tailscale.com/docs/features/webhooks)): push configuration
events within seconds; not log streaming.

- Endpoint must be HTTPS on port 80 or 443. The payload root is a JSON array.
- Verify `Tailscale-Webhook-Signature: t=<epoch>,v1=<hex>`: HMAC-SHA256 with
  the secret over `<t>.<raw body>`, constant-time compare, reject events older
  than about 5 minutes.
- Failed deliveries retry hourly for up to 24 hours. The secret is shown once,
  is per endpoint, and does not expire.
- Alert on `nodeKeyExpiringInOneDay`, `nodeKeyExpired`, `nodeNeedsApproval`,
  `policyUpdate`, `subnetIPForwardingNotEnabled`,
  `exitNodeIPForwardingNotEnabled`, `userRoleUpdated`, `webhookUpdated`,
  `webhookDeleted`. `nodeAuthorized` and `nodeNeedsAuthorization` are
  deprecated; pre-approved nodes emit no `nodeApproved`.

## Key Expiry and Re-Authentication

Auth-key expiry (blocks new enrollments only) and node-key expiry (breaks
connections to and from the node) are different mechanisms. Node-key
mechanics and the recovery steps for an expired node (`--force-reauth`,
"Temporarily extend key") are in
[policy-security.md](policy-security.md#approval-key-expiry-and-identity-lifecycle);
auth keys are in [automation-api.md](automation-api.md#auth-keys).

For tagged infrastructure the fail-closed risk is an expired auth key blocking
replacement nodes. Untagged (user-owned) routers and servers still expire
unless expiry is disabled.

## Coordination Server Outage

([outage behavior](https://tailscale.com/docs/reference/coordination-server-down))
No traffic transits the control plane. Existing direct and DERP paths keep
working; keys and cached policy are enforced locally. Stopped: adding devices
or users, key refresh (devices gradually lose each other; a node whose key
expires is cut off), policy updates, and revoking user keys. During an
incident do not rely on policy edits or revocations taking effect, and avoid
re-authenticating nodes (login needs the coordination server).

Create a break-glass admin that does not depend on the SSO provider: an Admin
who signs in with a passkey or a second IdP
([passkey admin](https://tailscale.com/docs/reference/tailnet-passkey-admin)).
A production review should check that one exists.

## Device Lifecycle

- Removing a device (Machines > Remove, or
  `DELETE https://api.tailscale.com/api/v2/device/{id}`) cuts it off at once.
  If device approval is off it can rejoin without admin action, and
  uninstalling the client does not remove it
  ([remove a device](https://tailscale.com/docs/features/access-control/device-management/how-to/remove)).
- Ephemeral nodes ([automation-api.md](automation-api.md#ephemeral-nodes)): each
  new node gets a new IP, and removal emits `nodeDeleted`.
- Restoring a backup or cloning a VM or disk copies node state, giving two
  devices with one node key and IP; see
  [containers-tsnet.md](containers-tsnet.md#state).
- Changing a device's tag with the CLI could log the user out before 1.98.9;
  on older clients use the console or API.

## Node State Encryption

([secure node state storage](https://tailscale.com/docs/features/secure-node-state-storage))

- Since 1.92.5, encryption is opt-in on Linux and Windows: `tailscaled --encrypt-state`
  (for example `FLAGS="--encrypt-state"` in `/etc/default/tailscaled`), or the
  `EncryptState` system policy on Windows and macOS Standalone. Apple and
  Android use platform stores. Versions 1.90.2-1.92.4 enabled it by default
  and failed to start after TPM resets and on cloned images.
- It needs a working TPM 2.0; without one startup fails. Do not enable it on
  VMs whose TPM can change (live migration, vTPM reset) without a
  re-registration plan.
- Check with device posture attribute `node:tsStateEncrypted`. Local
  `tailscaled --help` says encryption is enabled "if supported", which
  conflicts with the docs; trust the attribute.
- `failed to unseal state file`: per Tailscale staff in
  [issue 17654](https://github.com/tailscale/tailscale/issues/17654), the error
  suffix matters. `TPM_RC_INTEGRITY` typically means a TPM reset or state
  copied between machines; `TPM_RC_LOCKOUT` means repeated TPM auth failures.
  If the TPM cannot be fixed: remove the device in the admin console, delete
  the state file (`/var/lib/tailscale/tailscaled.state` on Linux), and
  re-register. Never clone state directories.

## Updates and Release Tracks

([client versions](https://tailscale.com/docs/reference/tailscale-client-versions),
[update clients](https://tailscale.com/docs/features/client/update))

- Even minor versions are stable, odd minors are unstable. Release candidates
  are patch builds offered only on pkgs.tailscale.com. Pin production to
  stable. NAS packages (Synology, QNAP) lag.
- Check and switch: `tailscale version --daemon --upstream --track`,
  `sudo tailscale update --dry-run --track stable|release-candidate|unstable`.
  Unstable clients show an informational "Using an unstable version" warning.
- The tailnet toggle "Auto-update new devices" affects only new devices;
  toggle existing ones per device (`tailscale set --auto-update`). Rollout
  starts about a week after release, cannot be scheduled, is unsupported on
  Synology and Arch-based Linux, and system policies override it. Machines page:
  gray arrow = update, red arrow = security update; filter
  `version:update-available`.
- Containers: `tailscale set --auto-update` does not persist across restarts.
  Use `tailscale/tailscale:stable` so each deploy pulls the current stable; a
  pinned tag reverts on redeploy.
- Nodes running Tailscale SSH, Serve, Funnel, or Services should track the
  newest release; the changelog carries recurring security fixes for these
  ([changelog](https://tailscale.com/changelog)).

## Platform Notes

- Boot ordering: use `tailscale wait`
  ([automation-api.md](automation-api.md#non-interactive-cli)). On systemd order
  units after `tailscale-online.target`; `After=tailscaled.service` is not
  enough, because READY means LocalAPI is up, not that the IP is bindable
  (community report in
  [issue 11504](https://github.com/tailscale/tailscale/issues/11504)). Check the
  installed package ships the target.
- Windows runs inside the logged-in user session by default, so it disconnects
  on sign-out or reboot. Enable unattended mode: `tailscale set --unattended=true`,
  `tailscale up --unattended=true --auth-key=...`, or the `UnattendedMode`
  policy. The flag exists only on Windows. Also disable key expiry for such
  hosts ([unattended](https://tailscale.com/docs/how-to/run-unattended)).
- macOS GUI clients run inside the user login session and cannot run as a
  standalone system daemon; the open-source `tailscaled` variant is the one
  recommended for unattended installs
  ([macOS variants](https://tailscale.com/docs/concepts/macos-variants)). Linux
  tailscaled always runs unattended.
- Windows MSI `TS_*` properties (for example `TS_UNATTENDEDMODE`,
  `TS_LOGINURL`) are written as system policy under
  `HKLM\SOFTWARE\Policies\Tailscale`; ARM64 uses the x86 MSI
  ([MSI](https://tailscale.com/docs/install/windows/msi)).
- System policies: `tailscale syspolicy list` shows Name, Origin, Value, Error
  (`unexpected key value type` reveals mistyped values);
  `tailscale syspolicy reload` forces a re-read (for hand-made registry values)
  but does not trigger MDM or Group Policy sync. Since 1.78 changes
  apply without restart. Linux support (1.102+) reads
  `/etc/tailscale/syspolicy.json`, overridable with `tailscaled --syspolicy-file`.
  `AuthKey` applies only while logged out; an MDM-delivered key is a
  credential-exposure risk, so use a one-off, tag-scoped key
  ([system policies](https://tailscale.com/docs/features/tailscale-system-policies)).
- Synology DSM7: inbound tailnet connections only until a boot-time task
  enables the TUN device (re-run after each package upgrade); no
  `--accept-routes`; Tailscale SSH does not run
  ([Synology](https://tailscale.com/docs/integrations/synology)).

## Production Review Checklist

- Policy uses least privilege with groups, tags, grants/ACLs, `tests`, and
  `sshTests`; tag owners do not let ordinary users self-assign production tags.
- Auth keys, OAuth clients, and workload identity are scoped and rotated; auth
  keys are monitored for expiry; untagged routers have expiry disabled or an
  alert.
- Device approval and posture rules match the trust model.
- Subnet routes, exit nodes, app connectors, Serve, Funnel, and Services have
  owners and rollback steps. Public Funnel exposure is intentional and the
  app authenticates.
- Routers have HA where downtime matters; overlapping prefixes are advertised
  consistently by every router.
- Audit logs are exported; flow logs and webhooks feed monitoring; client
  metrics are scraped.
- A passkey or second-IdP break-glass admin exists.
- Clients follow the stable track with an update policy; state encryption is
  a deliberate choice.
- Responders know how to collect bug reports and local logs without leaking
  secrets. Review logs for hostnames, identities, IPs, keys, and internal
  names before pasting them into public trackers.

## Incident Change Discipline

- Capture current state first: `tailscale get --set-flags`, `serve
  get-config --all`, and the policy diff.
- Prefer `tailscale set` for one preference rather than rebuilding a full
  `tailscale up` command. Prefer `serve clear svc:<name>` or `serve drain`
  over `serve reset` on hosts that carry Services, then confirm with
  `serve get-config --all`.
- Keep public exposure changes reversible: record the old Serve/Funnel
  config, policy diff, and rollback command.
- After mitigation, verify from the affected client path, not only from the
  router or admin workstation.
