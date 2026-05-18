# Fly Networking

Official docs:

- Private networking: https://fly.io/docs/networking/private-networking/
- Public services: https://fly.io/docs/networking/services/
- Flycast: https://fly.io/docs/networking/flycast/
- Custom private networks: https://fly.io/docs/networking/custom-private-networks/
- Egress IPs: https://fly.io/docs/networking/egress-ips/
- Dynamic request routing: https://fly.io/docs/networking/dynamic-request-routing/
- Request headers: https://fly.io/docs/networking/request-headers/

## Decision Path

1. Decide whether traffic is public, private direct, or private through Fly
   Proxy.
2. Check the app's public and private addresses:

   ```bash
   fly ips list
   fly services list
   fly status
   ```

3. If fixed outbound IPs are required, use app-scoped egress IPs per region.
4. If regional routing, tenant routing, or write-primary routing is involved,
   evaluate `fly-replay` and request headers.

## Private Networking And 6PN

- Fly private networking lets apps in the same organization private network
  communicate over IPv6 without the public internet.
- Use `.internal` names for Machine-to-Machine private DNS when clients can
  handle Fly's DNS behavior and the target Machines are running.
- Bind private-only app listeners to the appropriate private address or all
  interfaces, and omit public services if Fly Proxy should not route to them.
- Raw private networking does not provide Fly Proxy features. It will not
  autostart stopped Machines, terminate TLS, apply proxy handlers, or give
  geographically aware proxy load balancing.
- Do not treat per-Machine private addresses as a stable service abstraction.
  Use DNS, Flycast, or explicit Machine targeting depending on the need.

## Public Services

- `[http_service]` and `[[services]]` define what Fly Proxy can route to.
- A public app with eligible HTTP/TLS services normally gets Anycast IPv6 and
  shared Anycast IPv4. Shared IPv4 is the default recommendation unless the app
  has a concrete need for a dedicated IPv4.
- Anycast IPs are for inbound traffic. They are not the source IPs used by
  Machines for outbound requests.
- Public ports may appear open at the edge, but traffic only reaches the app for
  configured services. Still, if a service is configured and public IPs exist,
  assume it is internet exposed.
- Use `force_https` only on HTTP handlers. It is not appropriate for Flycast
  HTTP-only internal services.

## Flycast

Use Flycast when a private service should use Fly Proxy features:

- private app-wide addressing with `my-app.flycast`
- proxy load balancing across private services
- autostop/autostart based on private network requests
- TLS termination or PROXY protocol support
- clients that cannot use round-robin `.internal` DNS
- cross-org or custom private network exposure

Commands:

```bash
fly launch --flycast
fly deploy --flycast
fly ips allocate-v6 --private
```

Requirements and gotchas:

- The app needs a Flycast private IPv6 address on the relevant org network.
- The app should bind to `0.0.0.0:<port>` for Flycast. Binding only to
  `fly-local-6pn:<port>` does not work for Flycast.
- Configure `[http_service]` or `[[services]]`; Flycast routes through Fly Proxy.
- If public IPs are also assigned, the same configured services are publicly
  exposed. Run `fly ips list` and release public IPs when the service must be
  private-only.

## Custom Private Networks

- Use custom private networks when the default organization network is too broad
  for the isolation boundary, such as tenant isolation, environment isolation, or
  cross-org access control.
- `fly apps create --network <network-id-or-name>` can place a new app on a
  custom private network. Check current `fly networks --help` and docs before
  creating or modifying networks.
- When exposing a Flycast service across networks, allocate the private address
  for the originating network with `fly ips allocate-v6 --private --network ...`.

## Static Egress IPs

- Default outbound IPs are unstable and may change after Machine lifecycle or
  infrastructure events.
- Use static egress only when a third party requires IP allowlisting.
- Prefer app-scoped static egress IPs:

  ```bash
  fly ips allocate-egress --region <region>
  fly ips release-egress <address>
  ```

- Allocate one egress pair for each region where the app runs Machines that need
  allowlisting.
- Static egress costs more and limits how many Machines can run at once. Confirm
  the region and scaling requirement before allocating.
- Legacy machine-scoped egress IPs still exist but are no longer the default
  recommendation for new work.

## Dynamic Routing

- Fly adds request headers such as `Fly-Client-IP`, `Fly-Region`,
  `Fly-Forwarded-Port`, and forwarded protocol headers when the HTTP handler is
  used.
- `Fly-Prefer-Region`, `Fly-Prefer-Instance-Id`, and
  `Fly-Force-Instance-Id` can influence routing for clients that know where
  they want to land.
- Use `fly-replay` when an app should accept a request in one place and ask Fly
  Proxy to replay it to another region, app, or Machine. This is useful for
  write-primary routing, tenant locality, and regional data placement.
- Make replay targets explicit and bounded. Avoid loops and verify auth context
  survives replay.
