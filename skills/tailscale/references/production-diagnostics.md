# Tailscale Production Diagnostics

Docs: [troubleshooting](https://tailscale.com/docs/reference/troubleshooting), [message IDs](https://tailscale.com/docs/reference/messages). CLI flags drift from docs; confirm with
`<subcommand> --help` on the installed version. The grants troubleshooting page cites
`tailscale status --routes`, which client 1.102.4 rejects; use `tailscale status --json` (peers
expose `.PrimaryRoutes`, self `.AllowedIPs`) or `tailscale get advertise-routes`.

## Safe Read-Only Commands

```bash
tailscale version --daemon --upstream   # client, daemon, newest release
tailscale status [--json]               # --json schema changes between releases
tailscale whois --proto tcp <ip>:<port> # user, tags, caps a source resolves to
tailscale get --set-flags               # prints `tailscale set` args; snapshot before changing
tailscale serve get-config --all        # complete Service inventory; `serve status` differs
```

`whoami` and `service list` need 1.102.1+; Services: [expose-services.md](expose-services.md).
Client logs are readable only on the node: `journalctl -u tailscaled`,
`tailscale debug daemon-logs`, `kubectl logs -n tailscale deployment/operator` (Helm default name;
use your `fullnameOverride` if set).

## Layered Connectivity Triage

1. Is `tailscaled` running and logged in? Read [health warnings](#health-warnings) in
   `tailscale status` first.
2. Path column: `direct <ip:port>`, `relay "<region>"` (DERP), `peer-relay <ip:port>:vni:<id>`. A
   naive `grep relay` also matches peer-relay. A DERP reply on the first pings is normal:
   connections start relayed and upgrade to direct ([connection types](https://tailscale.com/docs/reference/connection-types)).
3. Use the right ping ([TCP between two devices](https://tailscale.com/docs/reference/troubleshooting/network-configuration/tcp-connection-two-devices)):
   `ping 100.x` is OS ICMP over the tailnet. `tailscale ping 100.x` tests whether the two tailscaled
   processes reach each other (disco) and by which path; it stops after 10 pings or the first direct
   path (`--c N`, 0 = infinite; `--until-direct=false`). `--tsmp` skips both host network stacks,
   `--icmp` only the local one, `--peerapi` tests PeerAPI. If `tailscale ping` works but ping/TCP
   does not, an OS firewall or access rule blocks it.
4. `tailscale whois` on the destination shows the identity the source resolves to; check the
   policy allows it. Subnet routes or app connectors: check each route gate
   ([routing-connectors.md](routing-connectors.md#route-injection)).
5. `tailscale dns status` or `dns query <name>` shows the expected MagicDNS or split DNS?
   `serve get-config --all` shows the expected target and protocol? Serve is tailnet-private, Funnel
   public. Peer relays: [routing-connectors.md](routing-connectors.md#peer-relays).
6. Large packets fail but small ones work: the Tailscale interface MTU is 1280 and larger packets
   from other interfaces can be dropped silently. Confirm with tcpdump; fix with a lower LAN MTU or
   MSS clamping.

### Reading netcheck

([device connectivity](https://tailscale.com/docs/reference/device-connectivity)) `UDP: false` means
no outbound UDP, relay only. `MappingVariesByDestIP: true` means hard NAT, the main reason direct
connections fail; `PortMapping` present (UPnP, NAT-PMP, PCP) makes it generally easy NAT. `IPv6: No`
only means no IPv6 address. Direct if either side has no NAT or both are easy; relayed (peer relay
if available, else DERP) if both are hard, or one hard and one easy. Hard NAT on a subnet router,
exit node, or app connector is worse than latency:
[routing-connectors.md](routing-connectors.md#connection-types-nat-traversal-derp).

## Firewall, UDP, and Ports

Tailscale needs no inbound ports. When direct connections fail, allow ([firewall ports](https://tailscale.com/docs/reference/faq/firewall-ports)):

- Outbound TCP 443 to `*:443` (control plane and DERP). Do not enumerate DERP hosts; partial
  blocks look like random peer failures.
- Outbound UDP from source port 41641 (default, configurable) to `*:*`, and to `*:3478` (STUN).
- Optional TCP 80: without it connections are delayed and captive portals go undetected.

Prefer domain rules over IP ranges; derive DERP allowlists from `tailscale debug derp-map`. A
public-IP host that blocks inbound UDP behaves like easy NAT. Linux uses iptables by default
([firewall mode](https://tailscale.com/docs/features/firewall-mode));
`TS_DEBUG_FIREWALL_MODE=auto|iptables|nftables` (in `/etc/default/tailscaled`) is a temporary,
unsupported knob; `router:` lines in `journalctl -ru tailscaled` show the chosen mode.

## Health Warnings

Warnings appear in `tailscale status` and the `tailscaled_health_messages` metric. Message page
slugs do not always equal the reference ID; find the page from the messages index.

- `invalid-packet-filter`: the client rejects all packets for safety. Causes: invalid port,
  protocol, or CIDR in policy; the same policy tag assigned to both Funnel and an app connector; a
  host pf/iptables/nftables conflict.
- `docker-stateful-filtering`:
  [containers-tsnet.md](containers-tsnet.md#docker-on-a-tailscale-linux-host).
  `resolv-conf-overwritten`: enable systemd-resolved, run tailscaled as root.
  `ssh-unavailable-selinux-enabled`: SELinux can block the in-process SSH server (permissive mode,
  custom policy, or OpenSSH over the tailnet).
- `no-derp-home` / `no-derp-connection`: check outbound TCP 443 to DERP. `not-in-map-poll` ("Out
  of sync"): test with `tailscale debug ts2021 --host controlplane.tailscale.com`; peer reachability
  degrades over time.
- IP forwarding: from 1.98.2 (1.98.1's Linux build was withdrawn) the Linux client warns when
  subnet routers and exit nodes lack forwarding; webhook events `subnetIPForwardingNotEnabled` and
  `exitNodeIPForwardingNotEnabled` cover it tailnet-wide.

CGNAT conflicts (`disable-ipv4` versus `disable-linux-cgnat-drop-rule`):
[routing-connectors.md](routing-connectors.md#ipv6-cgnat-and-addressing).

## Debug, Bug Reports, and Metrics

`tailscale debug` is unstable. Useful: `capture -o file.pcap` (needs the ts-dissector Lua script in
Wireshark), `derp-map`, `ts2021`, `netmap`. Avoid in production: `derp-set-on-demand`, `break-*`,
`pick-new-derp`, `force-netmap-update`, `set-expire`, `rotate-disco-key`, `clear-netmap-cache`,
`restun`, `rebind`.

`tailscale bugreport` is not read-only: it writes an identifier into the client logs uploaded to
Tailscale, with health status and the coordination server's netmap ([bug report](https://tailscale.com/docs/account/bug-report)). Run it on the affected host; `--record`
writes one identifier, waits while you reproduce the issue, then writes a second on Enter (share
both); `--diagnose` adds system detail. `tailscaled --no-logs-no-support` (env
`TS_NO_LOGS_NO_SUPPORT=true`; Windows: only the env var in
`%ProgramData%\Tailscale\tailscaled-env.txt`; macOS: only the open-source variant) generates no bug
report, disables support that needs the logs, and the node reports no flow logs (an investigation
blind spot).

Client metrics (1.78.0+) ([client metrics](https://tailscale.com/docs/reference/tailscale-client-metrics)): `tailscale metrics print`
or `metrics write <path>` (textfile collector); HTTP `/metrics` at `http://100.100.100.100/metrics`
on the host, or over the tailnet on port 5252 after `tailscale set --webclient` plus a policy rule
for the monitor (`tailscale web --readonly --listen` does not expose it). Alert on
`tailscaled_health_messages{type="warning"}`; `tailscaled_advertised_routes` minus
`tailscaled_approved_routes` (routes awaiting approval); relay fraction from
`tailscaled_{inbound,outbound}_bytes_total` by `path` (`direct_*`, `derp`, `peer_relay_*`); spikes
in `tailscaled_{inbound,outbound}_dropped_packets_total` with `reason="acl"`.
`tailscaled_serve_*_bytes_total{service="svc:name"}` (1.102.1+) covers Services hosts only, not
device Serve or Funnel.

## Logging and Audit

Configuration audit logs ([audit logging](https://tailscale.com/docs/features/logging/audit-logging)): always on, retained 90 days
(export if longer matters). Entries carry `eventGroupID` (one operation, many entries), actor,
target, and old/new values (policy diffs include comment-only changes). Samples show
`origin: ADMIN_UI` while the [deployment checklist](https://tailscale.com/docs/reference/deployment-checklist) SIEM rules match
`ADMIN_CONSOLE`; inspect real events before writing a rule. In a GitOps-managed tailnet, alert on
console-origin CREATE/UPDATE/DELETE as drift.

Network flow logs ([network flow logs](https://tailscale.com/docs/features/logging/network-flow-logs)): off by default, need an
Owner/Admin/Network admin/IT admin to start, retained 30 days, cover nodes on 1.34+, record only
successful connections (denials are absent), arrive non-real-time, and have no console viewer (API
or log streaming only). Only `Message.nodeId` is verified; `start`, `end`, `srcNode`, `dstNodes`,
and counters are self-reported and can be spoofed, and clocks skew. Both ends log a connection, so
cross-check a suspect node against a trusted peer. Exit-node traffic omits protocol, source port,
and destination unless exit-node destination logging is enabled (needs log streaming and a sales
contract).

```bash
GET https://api.tailscale.com/api/v2/tailnet/{tailnet}/logging/configuration?start=&end=  # scope logs:configuration:read
GET https://api.tailscale.com/api/v2/tailnet/{tailnet}/logging/network?start=&end=        # scope logs:network:read
```

`start` and `end` are RFC 3339. Neither endpoint paginates and the network endpoint returns
everything in the window, so query short windows. `end` later than the latest ingested log does not
block, so re-running a range can return more entries. `go run tailscale.com/cmd/netlogfmt@latest`
pretty-prints; `--resolve-addrs=nodeids|names|users` maps addresses (clients 1.92+ embed node
info; older clients also need `--api-key` and `--tailnet-name`).

Log streaming ([log streaming](https://tailscale.com/docs/features/logging/log-streaming)): audit
and network logs are configured separately. SIEM URLs must be HTTPS. A private endpoint (plain HTTP
allowed) must be a tailnet node given by machine name, FQDN, or IPv6 address (IPv4 is unsupported).
Tailscale adds an accept rule for `logstream@tailscale` to your policy; with GitOps-managed policy
that edit fails, so add the rule to git first, then the endpoint.

Webhooks ([webhooks](https://tailscale.com/docs/features/webhooks)) push configuration events within
seconds. The endpoint must be HTTPS on port 80 or 443; the payload root is a JSON array. Verify
`Tailscale-Webhook-Signature: t=<epoch>,v1=<hex>`: HMAC-SHA256 with the secret over
`<t>.<raw body>`, constant-time compare, reject events older than about 5 minutes. Failed deliveries
retry hourly for up to 24 hours. The secret is shown once. Alert on `nodeKeyExpiringInOneDay`,
`nodeKeyExpired`, `nodeNeedsApproval`, `policyUpdate`, `userRoleUpdated`, `webhookUpdated`, and
`webhookDeleted`; `nodeAuthorized` and `nodeNeedsAuthorization` are deprecated, and pre-approved
nodes emit no `nodeApproved`.

## Key Expiry and Re-Authentication

Auth-key expiry blocks new enrollments only; node-key expiry breaks connections to and from the
node. Recovery: [policy-security.md](policy-security.md#approval-key-expiry-and-identity-lifecycle);
auth keys: [automation-api.md](automation-api.md#auth-keys). Untagged routers and servers still
expire unless expiry is disabled; on tagged infrastructure the risk is an expired auth key blocking
replacement nodes.

## Coordination Server Outage

([outage behavior](https://tailscale.com/docs/reference/coordination-server-down)) Existing direct
and DERP paths keep working; keys and cached policy are enforced locally. Stopped: adding devices or
users, key refresh (a node whose key expires is cut off), policy updates, and revoking user keys, so
do not rely on edits or revocations taking effect, and avoid re-authenticating nodes. Keep a
break-glass Admin that signs in with a passkey or a second IdP ([passkey admin](https://tailscale.com/docs/reference/tailnet-passkey-admin)).

## Device Lifecycle

Removing a device (Machines > Remove, or `DELETE https://api.tailscale.com/api/v2/device/{id}`) cuts
it off at once. If device approval is off it can rejoin without admin action, and uninstalling the
client does not remove it. Cloned VMs or restored backups duplicate node state
([containers-tsnet.md](containers-tsnet.md#state)). Changing a tag with the CLI could log the user
out before 1.98.9; use the console or API on older clients. Ephemeral nodes:
[automation-api.md](automation-api.md#ephemeral-nodes) (removal emits `nodeDeleted`).

## Node State Encryption

([secure node state storage](https://tailscale.com/docs/features/secure-node-state-storage))

- Since 1.92.5, opt-in on Linux and Windows: `tailscaled --encrypt-state` (for example
  `FLAGS="--encrypt-state"` in `/etc/default/tailscaled`), or the `EncryptState` system policy on
  Windows and macOS Standalone. Versions 1.90.2-1.92.4 enabled it by default and failed to start
  after TPM resets and on cloned images.
- It needs a working TPM 2.0; without one startup fails. Do not enable it on VMs whose TPM can
  change (live migration, vTPM reset) without a re-registration plan. Check with posture attribute
  `node:tsStateEncrypted`, not `tailscaled --help` ("if supported").
- `failed to unseal state file` (per Tailscale staff, [issue 17654](https://github.com/tailscale/tailscale/issues/17654)): `TPM_RC_INTEGRITY` typically means a
  TPM reset or state copied between machines; `TPM_RC_LOCKOUT` means repeated TPM auth failures. If
  the TPM cannot be fixed, remove the device in the admin console, delete the state file
  (`/var/lib/tailscale/tailscaled.state` on Linux), and re-register. Never clone state directories.

## Updates and Release Tracks

([client versions](https://tailscale.com/docs/reference/tailscale-client-versions))

- Even minor versions are stable, odd minors unstable. Release candidates are patch builds offered
  only on pkgs.tailscale.com. Pin production to stable;
  `tailscale update --dry-run --track stable|release-candidate|unstable`.
- Nodes running Tailscale SSH, Serve, Funnel, or Services should track the newest release; the
  changelog carries recurring security fixes for these.
- "Auto-update new devices" affects only new devices; use `tailscale set --auto-update` on
  existing ones. Rollout starts about a week after release and cannot be scheduled; system policies
  override it.
- Containers: `tailscale set --auto-update` does not persist across restarts; use
  `tailscale/tailscale:stable`, since a pinned tag reverts on redeploy.

## Platform Notes

- Boot ordering: use `tailscale wait`
  ([automation-api.md](automation-api.md#non-interactive-cli)). On systemd order units after
  `tailscale-online.target`; `After=tailscaled.service` is not enough: READY means LocalAPI is up,
  not that the IP is bindable ([issue 11504](https://github.com/tailscale/tailscale/issues/11504)).
  Check the package ships the target.
- Windows runs in the logged-in user session by default and disconnects on sign-out or reboot;
  enable unattended mode (`tailscale set --unattended=true`,
  `tailscale up --unattended=true --auth-key=...`, or the `UnattendedMode` policy; Windows-only
  flag) and disable key expiry for such hosts. macOS: the open-source `tailscaled` variant is the
  one recommended for unattended installs.
- [System policies](https://tailscale.com/docs/features/tailscale-system-policies):
  `syspolicy list` shows Error (`unexpected key value type` reveals mistyped values);
  `syspolicy reload` does not trigger MDM sync. Linux (1.102+) reads
  `/etc/tailscale/syspolicy.json` (`tailscaled --syspolicy-file`). `AuthKey` applies only while logged out; an
  MDM-delivered key is a credential-exposure risk, so use a one-off, tag-scoped key.

## Incident Change Discipline

Snapshot `tailscale get --set-flags`, `serve get-config --all`, and the policy diff first, with a
rollback command for any public Serve/Funnel change. Prefer `tailscale set` over rebuilding a full
`tailscale up`; on hosts that carry Services prefer `serve clear svc:<name>` or `serve drain` over
`serve reset`. Verify from the affected client, not the router.
