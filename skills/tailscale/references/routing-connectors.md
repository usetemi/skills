# Tailscale Routing, Connectors, And DNS

Official docs: [subnet routers](https://tailscale.com/docs/features/subnet-routers),
[exit nodes](https://tailscale.com/docs/features/exit-nodes),
[app connectors](https://tailscale.com/docs/features/app-connectors),
[peer relay](https://tailscale.com/docs/features/peer-relay),
[route injection](https://tailscale.com/docs/reference/route-injection),
[DNS](https://tailscale.com/docs/reference/dns-in-tailscale),
[connectivity](https://tailscale.com/docs/reference/device-connectivity).

## Decision Path

1. Classify the traffic: node to node, a private subnet, all internet egress
   (exit node), or specific SaaS domains (app connector).
2. Keep four gates separate; each fails alone: advertisement (router offers
   the route), approval (admin console or `autoApprovers`), client acceptance,
   and access policy (grants/ACLs).
3. Run read-only checks before changing anything:

```bash
tailscale status --json
tailscale netcheck
tailscale ping <peer>
tailscale dns status
tailscale appc-routes --all
ip route show table 52    # Linux: Tailscale-installed routes
```

Routers, exit nodes, and connectors reach private or egress destinations for
tailnet members. Serve is tailnet-private and Funnel is public; neither is a
routing feature.

## Route Injection

Tailscale injects routes into CLIENT routing tables; it is not cloud
route-table management. A route reaches a client only when a router advertises
it, an admin approves it, the control plane sends it in the netmap, and the
client accepts it. Windows, macOS, Android, iOS, and tvOS accept by default;
Linux needs `tailscale set --accept-routes`.

Grants never inject routes. A route without a grant enters the tunnel and is
dropped by the packet filter; a grant without a route never enters the tunnel.
A grant on `10.0.0.0/8` creates no routes inside it. A client that turns route
acceptance off also bypasses app connectors.

On Linux the routes live in table 52, not `main`, so `ip route` does not show
them; use `ip route show table 52`
([IP routes](https://tailscale.com/docs/reference/troubleshooting/network-configuration/tailscale-ip-routes)).
Rules 5210/5230/5250 match Tailscale's own fwmark packets (`0x80000/0xff0000`)
and send them to `main` (then `default`, then `unreachable`), so they bypass
table 52; `5270: from all lookup 52` is normal, not a leak. An accepted route
overlapping a local LAN or cluster CIDR captures that traffic.

## Subnet Routers

```bash
sudo tailscale set --advertise-routes=10.0.0.0/24,192.168.1.0/24
```

Linux forwarding (use `/etc/sysctl.conf` if there is no `sysctl.d`):

```bash
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
sudo sysctl -p /etc/sysctl.d/99-tailscale.conf
```

- Enable forwarding only with a default-deny forward firewall. firewalld hosts
  may also need `firewall-cmd --permanent --add-masquerade`. Linux client
  1.98.2+ reports missing forwarding as a health warning (1.98.1 introduced it
  but its Linux build was withdrawn).
- Disable key expiry on routers (tagged devices already have it off): an
  expired router's routes stay in place on clients but become
  unreachable ("fail close", so traffic is not leaked to untrusted networks;
  [doc](https://tailscale.com/docs/features/subnet-routers)). Devices behind a
  router do not count toward the device limit.
- Never advertise `0.0.0.0/0` (use an exit node). Do not advertise
  `172.0.0.0/8`: only `172.16.0.0/12` is private and the rest includes Google
  public addresses that the route would black-hole
  ([doc](https://tailscale.com/docs/reference/troubleshooting/cloud/aws-google-routes)).
- Kernel mode (root Linux) forwards real IP packets. Userspace mode (all
  non-Linux OSes, or `--tun=userspace-networking`) re-originates TCP/UDP,
  relays only ping for ICMP, and drops other protocols such as SCTP. Use
  kernel-mode Linux for busy routers and exit nodes
  ([doc](https://tailscale.com/docs/reference/kernel-vs-userspace-routers)).
- Slow throughput with high CPU on Linux (client 1.54+, kernel 6.2+):
  `ethtool -K <default-route-dev> rx-udp-gro-forwarding on rx-gro-list off`.
  It is not persistent; persist from `/etc/networkd-dispatcher/routable.d/`
  ([performance](https://tailscale.com/docs/reference/best-practices/performance)).

### autoApprovers

([policy file](https://tailscale.com/docs/reference/syntax/policy-file))

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
router (on hosts, the VPC route table, or DHCP) or replies are lost. Never
disable SNAT on a node that is also an exit node: a community report
([issue 18725](https://github.com/tailscale/tailscale/issues/18725)) shows exit
traffic leaving with a `100.x` source and being dropped upstream; use separate
nodes.

`--stateful-filtering` defaults to false. A node that stored `true` before
1.66.4 keeps it ([issue 12108](https://github.com/tailscale/tailscale/issues/12108),
maintainer comment). The Docker-host symptom and fixes are in
[containers-tsnet.md](containers-tsnet.md#docker-on-a-tailscale-linux-host).
`--netfilter-mode` is `on|nodivert|off`; `off` means you own all NAT and
forward rules.

### High availability

([HA](https://tailscale.com/docs/how-to/set-up-high-availability))

- Routers advertising the same prefix fail over by default. The primary is
  the router added earliest; failover takes about 15 seconds after
  `tailscale down`, longer for partitions. There is no preferred-router
  setting.
- Failover is exact-prefix only. A `10.0.0.0/16` router is not a backup for
  `10.0.0.0/24`: if the /24 router goes offline that traffic is dropped, by
  design. Every router of the broader prefix must also advertise the specific
  one ([doc](https://tailscale.com/docs/reference/troubleshooting/network-configuration/overlapping-subnet-route-failover)).
- Do not set `--accept-routes` on HA routers sharing routes: the standby
  accepts its own route from the primary and hairpins its directly connected
  subnet through it.
- Regional routing (tailnet-wide setting, plan-gated) groups routers by the
  client's closest DERP region; it does not work with custom DERP.
- Test failover by taking one router down at a time.

### 4via6

For overlapping IPv4 sites:

```bash
tailscale debug via 7 10.1.1.0/24     # fd7a:115c:a1e0:b1a:0:7:a01:100/120
sudo tailscale set --advertise-routes=fd7a:115c:a1e0:b1a:0:7:a01:100/120
```

- Write access rules with the IPv6 CIDR as `dst`, not the IPv4 address. DNS
  form is `10-1-1-16-via-7`; deprecated name formats were removed in 1.102.1.
- Site IDs are 0-65535 (above 255 needs 1.58+); the same ID and CIDR on two
  routers forms an HA pair ([doc](https://tailscale.com/docs/features/subnet-routers/4via6-subnets)).
- Run 1.102.3+ on 4via6 routers (bulletin TS-2026-011, 2026-08-18): earlier
  versions let a peer with access reach host-scoped targets embedded in the
  address, such as the router's cloud metadata service
  ([bulletin](https://tailscale.com/security-bulletins)). The fix
  ([PR 20866](https://github.com/tailscale/tailscale/pull/20866)) blocks
  loopback, link-local, multicast, unspecified, broadcast, and `100.64.0.0/10`
  targets in the client, so grants cannot re-allow them; the one exception is
  GCP internal DNS (`169.254.169.254:53`).

### Site-to-site

([doc](https://tailscale.com/docs/features/site-to-site)) CIDRs must differ
(use HA or 4via6 otherwise) and both routers must be Linux. On each router:

```bash
sudo tailscale up --advertise-routes=<local-cidr> --snat-subnet-routes=false --accept-routes
sudo iptables -t mangle -A FORWARD -o tailscale0 -p tcp -m tcp \
  --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
```

Approve both routes and grant each direction. LAN hosts other than the router
need `ip route add 100.64.0.0/10 via <router-LAN-IP>` and
`ip route add <remote-cidr> via <router-LAN-IP>` unless the router is their
default gateway; `ip route` changes do not survive reboot.

### Overlap with the local LAN

([doc](https://tailscale.com/docs/reference/troubleshooting/network-configuration/lan-traffic-overlapping-subnets))
Windows/macOS: advertise a less specific route than the LAN (`192.168.2.0/23`
for a /24). Linux: `sudo ip rule add to 192.168.2.0/24 priority 2500 lookup
main` (not persistent; use a systemd-networkd `RoutingPolicyRule`). Avoid these
on roaming laptops. A device that does not need the routes should use
`--accept-routes=false`.

## Exit Nodes

Three separate opt-ins:

```bash
sudo tailscale set --advertise-exit-node          # node offers itself
# admin console approval, or autoApprovers.exitNode
tailscale exit-node list
tailscale set --exit-node=<ip|name>               # client selects
tailscale set --exit-node=                        # clear
```

- Policy trap: once the policy is not default allow-all, users need a grant
  with `dst: autogroup:internet`. Naming the exit node device as `dst` only
  permits connecting to that device:

  ```hujson
  {"src": ["autogroup:member"], "dst": ["autogroup:internet"], "ip": ["*"]}
  ```

- Linux exit nodes need IP forwarding. Windows, macOS, and Android exit nodes
  are userspace-only; macOS and Windows must not sleep.
- `tailscale exit-node suggest` prints the recommendation and the set command.
  `--exit-node=auto:any` (1.86+) follows it automatically
  ([auto](https://tailscale.com/docs/features/exit-nodes/auto-exit-nodes)).
  Managed fleets set `ExitNodeID` (node ID or `auto:any`) by MDM policy;
  `ExitNode.AllowOverride` (1.88+) lets users pick another node
  ([mandatory](https://tailscale.com/docs/features/exit-nodes/mandatory-exit-nodes)).
- The local LAN is untrusted while an exit node is active, so LAN hosts and LAN
  DNS are unreachable. `tailscale set --exit-node-allow-lan-access=true` opts
  in; use it only on trusted networks
  ([doc](https://tailscale.com/docs/reference/troubleshooting/connectivity/connect-lan-failure)).
- A client on an exit node uses it as resolver for all domains and ignores
  global and split-DNS nameservers. Enable "Use with exit node" on a nameserver
  in the admin console DNS page to keep it. Check this first when split DNS
  breaks only with an exit node.
- For a few known destinations that allowlist your IP, prefer a subnet router
  on a fixed-IP VM with a `via` grant over an exit node
  ([pattern](https://tailscale.com/docs/use-cases/regulated-environment/static-egress-ip-allowlist)):

  ```hujson
  {"src": ["group:regulated"], "dst": ["198.51.100.5/32"], "ip": ["*"], "via": ["tag:egress"]}
  ```

## App Connectors

([setup](https://tailscale.com/docs/features/app-connectors/how-to/setup),
[best practices](https://tailscale.com/docs/reference/best-practices/app-connectors))
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
{
  "target": ["*"],
  "app": {
    "tailscale.com/app-connectors": [
      {
        "name": "github",
        "connectors": ["tag:connector"],
        "domains": ["github.com", "*.github.com"],
        // optional: "routes": ["192.0.2.0/24"], "presetAppID": "github"
      },
    ],
  },
}
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
  preconfigure known ranges or run without auto-approval for a representative
  business cycle, then batch-approve.
- Limits: Linux connectors only; not shareable across tailnets; over 10K routes
  causes client problems; 250 domains per tailnet; avoid ephemeral connector
  nodes.
- A Terraform/GitOps-managed policy overwrites console edits to app connectors.
- `tailscale appc-routes`: default shows domains with learned-route counts,
  `--map` domain to routes, `--all` learned plus policy routes, `-n` total.

## Peer Relays

([doc](https://tailscale.com/docs/features/peer-relay)) GA.
Relay and consumers need 1.86+; the relay can be any OS except iOS, Apple TV,
and Android. Path order is direct, peer relay, DERP. Relays serve only devices
in the same tailnet.

```bash
sudo tailscale set --relay-server-port=40000        # 0 = random, "" = disable
sudo tailscale set --relay-server-port=40000 \
  --relay-server-static-endpoints="203.0.113.10:40000"
```

- The UDP port must be reachable by peers. Static endpoints advertise fixed
  candidates behind port forwards or load balancers (for example an AWS NLB).
- The grant is the access control, with no separate network grant. `src` is
  the hard-NAT devices that should use the relay, `dst` the relay nodes. Keep
  `src` narrow (stable devices behind strict NAT), never `*`, and avoid roaming
  laptops and mobile:

  ```hujson
  {"src": ["tag:us-east-vpc"], "dst": ["tag:us-east-relays"],
   "app": {"tailscale.com/cap/relay": []}}
  ```

- Verify: `tailscale status | grep peer-relay` shows
  `peer-relay <ip>:<port>:vni:<id>`. Clients export
  `tailscaled_peer_relay_forwarded_{packets,bytes}_total`.
- Kubernetes has a `PeerRelay` resource (operator 1.102.2+); see
  [kubernetes.md](kubernetes.md#multi-tailnet-and-peer-relay).
- Leads, not guarantees (open as of 2026-09): relays never selected despite a
  correct grant ([18851](https://github.com/tailscale/tailscale/issues/18851),
  [20785](https://github.com/tailscale/tailscale/issues/20785)); dead data plane
  after ~5 idle minutes ([20452](https://github.com/tailscale/tailscale/issues/20452)).
  Check grant, UDP reachability, and connection type first.

## Connection Types, NAT Traversal, DERP

- Reading `tailscale status` path types, `tailscale ping`, and `netcheck` (hard
  vs easy NAT) is in
  [production-diagnostics.md](production-diagnostics.md#layered-connectivity-triage).
  Public IPv6 counts as easy NAT.
- AWS and Azure NAT Gateways are hard NAT. Put critical nodes in a public
  subnet with a public IP and the WireGuard UDP port open, or place a peer
  relay there
  ([NAT traversal](https://tailscale.com/blog/nat-traversal-improvements-pt-2-cloud-environments)).
- The egress allow-list is in
  [production-diagnostics.md](production-diagnostics.md#firewall-udp-and-ports).
  `ufw allow 41641/udp` on a server helps peers connect directly.
- Connectors stuck on DERP's TCP transport can suffer head-of-line blocking
  (DNS timeouts are the visible symptom). Give connectors a direct or easy-NAT
  path, or isolate latency-sensitive services
  ([doc](https://tailscale.com/docs/reference/troubleshooting/network-configuration/hard-nat-issues)).
- DERP relays DISCO discovery packets and WireGuard-encrypted packets; it
  cannot decrypt traffic. Clients pick a home DERP by latency and fall to
  another server in the region, then the next closest region. The client saves
  the DERP map, so DERP works if the control plane is down
  ([doc](https://tailscale.com/docs/reference/derp-servers)).
- Custom DERP is alpha and Tailscale steers users to peer relays. Regions use
  IDs 900-999 with one server each; `OmitDefaultRegions: true` forces only
  yours; `derper --hostname=<fqdn> --verify-clients` limits use to your tailnet.
  Servers need direct internet access (no NAT or load balancer) with HTTP,
  HTTPS, STUN 3478, and ICMP open. No Mullvad or regional routing. Disable a
  Tailscale region with `"derpMap": {"regions": {"1": null}}`
  ([doc](https://tailscale.com/docs/reference/derp-servers/custom-derp-servers)).

## IPv6, CGNAT, And Addressing

- Every node has a `100.x` IPv4 and a ULA IPv6 from `fd7a:115c:a1e0::/48`, so
  IPv6 works inside the tailnet without ISP IPv6. IPv4-only and IPv6-only
  devices connect only through a relay
  ([IPv6](https://tailscale.com/docs/concepts/ipv6)).
- Linux drops non-Tailscale traffic from `100.64.0.0/10`, breaking other
  CGNAT-addressed services (ISPs, other VPNs, Kubernetes API servers, some
  cloud providers' internal DNS or metadata, for example Alibaba ECS per a
  community report in
  [issue 21249](https://github.com/tailscale/tailscale/issues/21249))
  ([CGNAT](https://tailscale.com/docs/reference/cgnat-interoperability)).
  Preferred fix:

  ```hujson
  {"target": ["tag:x"], "attr": ["disable-linux-cgnat-drop-rule"]}
  ```

  Verify `ts-input` has RETURN, not DROP, for `100.64.0.0/10`, and keep
  `net.ipv4.conf.all.rp_filter` at 1 or 2. `--netfilter-mode=nodivert` is the
  older fix and wins if both are set. `disable-ipv4` (IPv6-only) is the other
  option and breaks IPv4-only resources.

## MagicDNS And Split DNS

([MagicDNS](https://tailscale.com/docs/features/magicdns))

- A restricted nameserver is split DNS for one search domain; a global
  nameserver handles all queries. Override DNS servers forces global
  nameservers over local DNS, so every device must reach them by grant or
  resolution breaks.
- Tailscale either proxies DNS (all nameservers in parallel, fastest answer)
  or defers to the OS, so resolver order is not guaranteed. Use split DNS when
  an internal server must win. Private nameservers need a subnet route or a
  Tailscale IP.
- MagicDNS cannot hold arbitrary records; use public DNS or split DNS to your
  own server. If a home or ISP resolver blocks private answers (rebinding
  protection), use split DNS ([FAQ](https://tailscale.com/docs/reference/faq/dns-rebinding)).
- `--accept-dns=false` stops applying tailnet DNS settings, but
  `100.100.100.100` (`fd7a:115c:a1e0::53`) still answers tailnet names while
  MagicDNS is enabled
  ([FAQ](https://tailscale.com/docs/reference/faq/dns-resolv-conf)). Shared-in devices resolve only by full domain name.
- Machine names are the MagicDNS names, derived from the OS hostname at first
  join and unique per tailnet (a collision yields `<name>-1`, not reverted
  later). They follow OS hostname changes unless auto-generate is unchecked.
  Pin with `tailscale set --hostname=<name>`
  ([doc](https://tailscale.com/docs/concepts/machine-names)).
- Renaming the tailnet DNS name (`tail<hex>.ts.net`) breaks existing MagicDNS,
  HTTPS, and sharing links; do not hard-code the FQDN
  ([doc](https://tailscale.com/docs/concepts/tailnet-name)).
- Testing: `nslookup` and `host` bypass system resolution on macOS or ignore
  NRPT on Windows. Use `dscacheutil -q host -a name <host>` on macOS and
  `Resolve-DnsName <host>` on Windows; nslookup is valid on Linux. To test
  Tailscale's resolver independent of the OS:

  ```bash
  tailscale dns status [--all] [--json]
  tailscale dns query [--json] <name> [type]
  ```

### Linux DNS

([doc](https://tailscale.com/docs/reference/linux-dns))

- Tailscale overwrites `/etc/resolv.conf` only when MagicDNS is on,
  `--accept-dns` is true, and no DNS manager is detected
  ([FAQ](https://tailscale.com/docs/reference/faq/dns-resolv-conf)). Without one,
  `dhclient` and `tailscaled` fight and a DHCP renewal can drop MagicDNS; use
  systemd-resolved or resolvconf.
- NetworkManager with systemd-resolved:

  ```bash
  sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
  sudo systemctl restart systemd-resolved NetworkManager tailscaled
  ```

- Lead: if tailscaled starts before the resolver populates resolv.conf, the
  host can be left with only `100.100.100.100`, which answers tailnet names but
  SERVFAILs public ones ([issue 20341](https://github.com/tailscale/tailscale/issues/20341),
  closed; fix PR 20358 closed unmerged as of 2026-09-29). Check `resolvectl status`.

## Cloud Router Notes

- AWS private hosted zones resolve only through the VPC resolver at base+2
  (`10.0.96.0/20` gives `10.0.96.2`). Advertise the VPC CIDR, grant
  `tcp:53`/`udp:53` to that address, and add split DNS for the internal domain
  pointing at it. Azure uses a DNS private resolver inbound endpoint the same
  way. Use 4via6 for overlapping VPCs
  ([AWS](https://tailscale.com/docs/reference/reference-architectures/aws),
  [Azure](https://tailscale.com/docs/reference/reference-architectures/azure)).
