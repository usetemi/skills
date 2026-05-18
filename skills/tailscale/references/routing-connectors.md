# Tailscale Routing And Connectors

Official docs:

- Subnet routers: https://tailscale.com/kb/1019/subnets
- Exit nodes: https://tailscale.com/kb/1103/exit-nodes
- App connectors: https://tailscale.com/kb/1281/app-connectors
- Route injection: https://tailscale.com/docs/reference/route-injection
- Subnet failover: https://tailscale.com/kb/1115/subnet-failover/
- MagicDNS: https://tailscale.com/kb/1081/magicdns
- DNS: https://tailscale.com/kb/1054/dns
- Connection types: https://tailscale.com/docs/reference/connection-types

## Decision Path

1. Decide which traffic class is involved:
   - tailnet-to-tailnet private node traffic
   - access to a private subnet
   - full internet egress through an exit node
   - domain-specific SaaS or internet traffic through an app connector
2. Check reachability and route state before changing policy.
3. Separate advertisement, control-plane approval, client acceptance, and access
   policy in the answer.
4. For production, include failover, route priority, DNS behavior, and logging.

Safe read-only checks:

```bash
tailscale status
tailscale status --json
tailscale netcheck
tailscale ping <peer>
tailscale ip
tailscale dns status
tailscale appc-routes
```

## Subnet Routers

- A subnet router lets tailnet clients reach non-Tailscale IPs behind a
  Tailscale node.
- On the router node, advertise routes with `tailscale up --advertise-routes`
  or change only that setting with `tailscale set --advertise-routes`.
- Routes normally need approval in the admin console or API before clients can
  use them.
- Clients must accept routes (`--accept-routes=true` on platforms that expose
  the setting).
- Access policy must allow the source identities to reach the routed CIDR and
  ports.
- Linux subnet routers usually need IP forwarding enabled. Check current docs
  before writing sysctl commands for a target distribution.

Fast path:

```bash
sudo tailscale set --advertise-routes=10.0.0.0/24
tailscale status
```

Secure path:

```hujson
{
  "tagOwners": {
    "tag:subnet-router": ["group:netops"],
  },
  "grants": [
    {
      "src": ["group:eng"],
      "dst": ["10.0.0.0/24"],
      "ip": ["tcp:443", "tcp:22"],
    },
  ],
  "tests": [
    {
      "src": "alice@example.com",
      "accept": ["10.0.0.10:443"],
      "deny": ["10.0.0.10:3389"],
    },
  ],
}
```

## Exit Nodes

- An exit node routes a client's internet traffic through a Tailscale node.
- Advertising an exit node and selecting an exit node are different operations.
- Use `--exit-node-allow-lan-access` only when the client must keep local LAN
  access while using an exit node.
- For organization tailnets, restrict who can use exit nodes and monitor which
  devices advertise them.

Commands:

```bash
sudo tailscale set --advertise-exit-node=true
tailscale exit-node list
tailscale set --exit-node=<node-or-ip>
tailscale set --exit-node=
```

## App Connectors

- App connectors route configured domain-specific traffic through tagged
  connector nodes. They are useful for SaaS allowlisting and private access to
  selected internet destinations.
- A connector node advertises itself with `--advertise-connector`, but app
  connector configuration and domain routing are control-plane concerns.
- Connector auth key or OAuth credential expiry can break routing. For
  production, prefer scoped OAuth clients and explicit rotation checks.
- Avoid treating app connectors as a general exit node. Keep routes specific to
  the domains or apps that need connector egress.

Local connector setup shape:

```bash
sudo tailscale up \
  --advertise-tags=tag:app-connector \
  --advertise-connector \
  --auth-key=file:/run/secrets/ts_authkey
```

## Route Injection

- Route injection lets Tailscale manage routes in supported cloud networking
  environments. It changes how non-Tailscale resources learn routes to tailnet
  or subnet destinations.
- Keep route injection separate from tailnet policy. Injected routes can make a
  path exist, but grants/ACLs still decide permitted access.
- Check provider support and current docs before giving implementation steps.
  Cloud route tables, account permissions, and failure modes vary.

## High Availability And Failover

- Multiple subnet routers can advertise the same route. Tailscale can fail over
  between routers for resilience.
- For production, deploy routers in different hosts or zones, tag them, and test
  failover by disabling one router at a time.
- Document route ownership and approval state. A replaced router that is not
  approved can look healthy locally but fail to serve clients.
- Avoid overlapping CIDRs unless there is a deliberate priority and ownership
  model.

## MagicDNS And Split DNS

- MagicDNS gives tailnet names for devices and services. It depends on client
  DNS integration and resolver behavior.
- Split DNS routes selected domains to configured nameservers. It is often the
  right fit for private corporate zones.
- DNS failures are often platform-specific. Check:

  ```bash
  tailscale dns status
  tailscale status --json
  scutil --dns 2>/dev/null
  resolvectl status 2>/dev/null
  ```

- Use FQDNs when search domains or local resolver behavior could change the
  query.

## DERP, Direct, And Peer Relay Diagnostics

- Direct WireGuard paths are preferred when NAT and firewalls allow them.
- DERP relay is a fallback for reachability. It affects latency and throughput,
  but traffic remains end-to-end encrypted between Tailscale nodes.
- Peer relay can help when direct paths are blocked and another peer can bridge
  reachability.
- Use `tailscale netcheck` for local UDP/NAT/DERP observations and
  `tailscale ping <peer>` to see how a specific peer path is routed.

Useful checks:

```bash
tailscale netcheck
tailscale ping --verbose <peer>
tailscale status
tailscale status --json
```
