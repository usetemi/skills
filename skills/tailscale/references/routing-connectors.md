# Tailscale Routing, Connectors, And DNS

## Decision Path

Classify the traffic: node to node, private subnet, all internet egress (exit
node), or specific SaaS domains (app connector). Four gates fail alone:
advertisement, approval (admin console or `autoApprovers`), client acceptance,
and access policy. Check read-only first:

```bash
tailscale status --json; tailscale netcheck; tailscale ping <peer>
tailscale dns status; tailscale appc-routes --all
ip route show table 52    # Linux: Tailscale-installed routes
```

## Route Injection

Tailscale injects routes into CLIENT routing tables, not cloud route tables.
Windows, macOS, Android, iOS, and tvOS accept routes by default; Linux needs
`tailscale set --accept-routes`.

Grants never inject routes. A route without a grant enters the tunnel and is
dropped by the packet filter; a grant without a route never enters the tunnel.
A client that turns route acceptance off also bypasses app connectors.

On Linux the routes live in table 52, not `main`, so `ip route` does not show
them; `5270: from all lookup 52` is normal, not a leak. An accepted route
overlapping a local LAN or cluster CIDR captures that traffic.

## Subnet Routers

```bash
sudo tailscale set --advertise-routes=10.0.0.0/24,192.168.1.0/24
```

Linux needs `net.ipv4.ip_forward = 1` and `net.ipv6.conf.all.forwarding = 1`
in `/etc/sysctl.d/99-tailscale.conf` (`/etc/sysctl.conf` if there is no
`sysctl.d`), then `sudo sysctl -p <file>`.

- Enable forwarding only with a default-deny forward firewall. firewalld hosts
  may also need `firewall-cmd --permanent --add-masquerade`. Linux client
  1.98.2+ reports missing forwarding as a health warning.
- Disable key expiry on routers (tagged devices already have it off): an
  expired router's routes stay on clients but become unreachable.
- Never advertise `0.0.0.0/0` (use an exit node) or `172.0.0.0/8`: only
  `172.16.0.0/12` is private, and the route would black-hole Google public
  addresses.
- Kernel mode (root Linux) forwards real IP packets. Userspace mode (all
  non-Linux OSes, or `--tun=userspace-networking`) re-originates TCP/UDP,
  relays only ping for ICMP, and drops other protocols such as SCTP.

### autoApprovers

- Applies only when the control plane first receives an advertisement. Adding
  an approver does not approve pending routes; remove the route and advertise
  it again.
- Advertising stops if the device is re-authenticated by a user who cannot
  advertise the route, or the approving user is suspended or deleted. Use a tag
  as approver for production routers.
- Covers subnet routes and `autoApprovers.exitNode`. App connectors need route
  approval too. Services use `autoApprovers.services`
  ([expose-services.md](expose-services.md#policy)).

### SNAT

SNAT is on by default. `--snat-subnet-routes=false` (Linux only) keeps real
source IPs, but LAN hosts then need a return route for `100.64.0.0/10` via the
router or replies are lost. Never disable SNAT on a node that is also an exit
node: exit traffic leaves with a `100.x` source and is dropped upstream
([issue 18725](https://github.com/tailscale/tailscale/issues/18725), community
report); use separate nodes.

`--stateful-filtering` defaults to false; a node that stored `true` before
1.66.4 keeps it ([Docker-host symptoms](containers-tsnet.md#docker-on-a-tailscale-linux-host)).
`--netfilter-mode=off` means you own all NAT and forward rules.

### High availability

- Routers advertising the same prefix fail over by default. The primary is
  the router added earliest; failover takes about 15 seconds after
  `tailscale down`, longer for partitions. There is no preferred-router
  setting.
- Failover is exact-prefix only. A `10.0.0.0/16` router is not a backup for
  `10.0.0.0/24`: if the /24 router goes offline that traffic is dropped. Every
  router of the broader prefix must also advertise the specific one
  ([doc](https://tailscale.com/docs/reference/troubleshooting/network-configuration/overlapping-subnet-route-failover)).
- Do not set `--accept-routes` on HA routers sharing routes: the standby
  accepts its own route from the primary and hairpins its directly connected
  subnet through it.

### 4via6

For overlapping IPv4 sites:

```bash
tailscale debug via 7 10.1.1.0/24     # fd7a:115c:a1e0:b1a:0:7:a01:100/120
sudo tailscale set --advertise-routes=fd7a:115c:a1e0:b1a:0:7:a01:100/120
```

- Write access rules with the IPv6 CIDR as `dst`, not the IPv4 address. DNS
  form is `10-1-1-16-via-7`; deprecated name formats were removed in 1.102.1.
- Site IDs are 0-65535 (above 255 needs 1.58+); the same ID and CIDR on two
  routers forms an HA pair.
- Run 1.102.3+ on 4via6 routers (TS-2026-011): earlier versions let a peer
  reach host-scoped targets such as the router's cloud metadata service. The fix
  blocks loopback, link-local, and `100.64.0.0/10` targets in the client, so
  grants cannot re-allow them.

## Exit Nodes

Three separate opt-ins:

```bash
sudo tailscale set --advertise-exit-node   # node offers itself
# approval: admin console or autoApprovers.exitNode
tailscale set --exit-node=<ip|name>        # client selects; empty clears
```

- Policy trap: once the policy is not default allow-all, users need a grant
  with `dst: autogroup:internet` (`ip: ["*"]`). Naming the exit node device as
  `dst` only permits connecting to that device.
- Linux exit nodes need IP forwarding. Windows, macOS, and Android exit nodes
  are userspace-only; macOS and Windows must not sleep.
- `--exit-node=auto:any` (1.86+) follows `tailscale exit-node suggest`. MDM
  `ExitNode.AllowOverride` (1.88+) lets users override a fixed `ExitNodeID`.
- The local LAN is untrusted while an exit node is active, so LAN hosts and LAN
  DNS are unreachable. `--exit-node-allow-lan-access=true` opts in; use it only
  on trusted networks.
- A client on an exit node uses it as resolver for all domains and ignores
  global and split-DNS nameservers. Enable "Use with exit node" on a nameserver
  in the admin console DNS page to keep it. Check this first when split DNS
  breaks only with an exit node.
- For a few destinations that allowlist your IP, prefer a subnet router on a
  fixed-IP VM with a `via` grant over an exit node:
  `{"src": ["group:regulated"], "dst": ["198.51.100.5/32"], "ip": ["*"], "via": ["tag:egress"]}`

## App Connectors

Connector node: Linux, public IP, IP forwarding.

```bash
sudo tailscale up --advertise-connector --advertise-tags=tag:connector
```

`set` also takes `--advertise-connector`. Beyond `tagOwners`, policy needs:

1. A grant giving clients `tcp:53`/`udp:53` to the connector tag (DNS discovery
   uses PeerAPI DoH and needs the connector visible as a peer).
2. A grant with `dst: autogroup:internet` for discovered IPs (this also grants
   exit node use).
3. `autoApprovers.routes` for the connector tag (custom apps always; preset
   apps only for DNS-learned routes).
4. A `nodeAttrs` entry:

```hujson
{"target": ["*"], "app": {"tailscale.com/app-connectors": [
  {"name": "github", "connectors": ["tag:connector"],
   "domains": ["github.com", "*.github.com"]}]}}
```

- `*.acme.com` excludes `acme.com`; list both. Wildcards cannot cover a TLD.
  Any other FQDN sharing a resolved IP is also routed through the connector.
- Traffic egresses from the connector even when the client uses an exit node;
  add every connector's public IP to third-party allowlists.
- If the only connector for a domain is down, that domain fails to resolve. Run
  several connectors on one tag. CNAME chains are followed, so geo-DNS
  services need connectors in matching regions.
- Routes in the `routes` field are implicitly approved. New learned routes
  trigger client network changes (Chrome may show `ERR_NETWORK_CHANGED`):
  preconfigure known ranges or run without auto-approval for a
  representative business cycle, then batch-approve.
- Limits: Linux connectors only; not shareable across tailnets; over 10K routes
  causes client problems; 250 domains per tailnet; avoid ephemeral connector
  nodes. A Terraform/GitOps-managed policy overwrites console edits to app
  connectors.

## Peer Relays

GA. Relay and consumers need 1.86+; the relay can be any OS except iOS, Apple
TV, and Android. Path order is direct, peer relay, DERP. Relays serve only
devices in the same tailnet.

```bash
sudo tailscale set --relay-server-port=40000        # 0 = random, "" = disable
#   optional: --relay-server-static-endpoints="203.0.113.10:40000"
```

- The UDP port must be reachable by peers; static endpoints cover port
  forwards and load balancers.
- The grant is the access control, with no separate network grant. `src` is
  the hard-NAT devices that should use the relay, `dst` the relay nodes, and
  the capability is `"app": {"tailscale.com/cap/relay": []}`. Keep `src`
  narrow (stable devices behind strict NAT), never `*`, and avoid roaming
  laptops and mobile.
- Verify: `tailscale status | grep peer-relay`. Kubernetes:
  [kubernetes.md](kubernetes.md#multi-tailnet-and-peer-relay).

## Connection Types, NAT Traversal, DERP

- Path types and `netcheck` (hard vs easy NAT; public IPv6 counts as easy):
  [triage](production-diagnostics.md#layered-connectivity-triage); egress
  allow-list: [ports](production-diagnostics.md#firewall-udp-and-ports).
- AWS and Azure NAT Gateways are hard NAT. Put critical nodes in a public
  subnet with a public IP and the WireGuard UDP port open, or place a peer
  relay there.
- DERP cannot decrypt traffic; clients save the DERP map, so it works with the
  control plane down.
- Connectors stuck on DERP's TCP transport suffer head-of-line blocking (DNS
  timeouts); give them a direct or easy-NAT path.
- Custom DERP is alpha (prefer peer relays). Region IDs are 900-999, one
  server each; `derper --hostname=<fqdn> --verify-clients` limits use to your
  tailnet. Servers need direct internet access (no NAT or load balancer) with
  HTTP, HTTPS, STUN 3478, and ICMP open.

## IPv6, CGNAT, And Addressing

- Every node has a `100.x` IPv4 and a ULA IPv6 from `fd7a:115c:a1e0::/48`;
  IPv4-only and IPv6-only devices connect only through a relay.
- Linux drops non-Tailscale traffic from `100.64.0.0/10`, breaking other
  CGNAT-addressed services (ISPs, other VPNs, Kubernetes API servers, some
  cloud providers' internal DNS or metadata). Preferred fix: a `nodeAttrs`
  entry with `"attr": ["disable-linux-cgnat-drop-rule"]`. Verify `ts-input` has
  RETURN, not DROP, for `100.64.0.0/10`, and keep `net.ipv4.conf.all.rp_filter`
  at 1 or 2. `--netfilter-mode=nodivert` is the older fix and wins if both are set.
  `disable-ipv4` (IPv6-only) is the other option and breaks IPv4-only
  resources.

## MagicDNS And Split DNS

- A restricted nameserver is split DNS for one search domain; a global one
  handles all queries. Override DNS servers forces global nameservers over local
  DNS, so every device must reach them by grant or resolution breaks.
- Tailscale proxies DNS (all nameservers in parallel, fastest answer) or defers
  to the OS, so resolver order is not guaranteed; use split DNS when an
  internal server must win. Private nameservers need a subnet route or a
  Tailscale IP.
- `--accept-dns=false` stops applying tailnet DNS settings, but
  `100.100.100.100` (`fd7a:115c:a1e0::53`) still answers tailnet names while
  MagicDNS is enabled. Shared-in devices resolve only by full domain name.
- Renaming the tailnet DNS name (`tail<hex>.ts.net`) breaks existing MagicDNS,
  HTTPS, and sharing links; do not hard-code the FQDN.
- `nslookup`/`host` bypass system resolution on macOS or ignore NRPT on Windows:
  use `dscacheutil -q host -a name <host>` (macOS) or
  `Resolve-DnsName <host>` (Windows).
  `tailscale dns query <name> [type]` tests Tailscale's resolver directly.
- Linux: Tailscale overwrites `/etc/resolv.conf` only when MagicDNS is on,
  `--accept-dns` is true, and no DNS manager is detected. Without one,
  `dhclient` and `tailscaled` fight and DHCP renewal can drop MagicDNS; use
  systemd-resolved or resolvconf.
