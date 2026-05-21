# Fly Networking

Official docs:

- Private networking: https://fly.io/docs/networking/private-networking/
- Public services: https://fly.io/docs/networking/services/
- Flycast: https://fly.io/docs/networking/flycast/
- Custom private networks: https://fly.io/docs/networking/custom-private-networks/
- Egress IPs: https://fly.io/docs/networking/egress-ips/
- Dynamic request routing: https://fly.io/docs/networking/dynamic-request-routing/
- Request headers: https://fly.io/docs/networking/request-headers/

Fly-authored Fly-Src references:

- Fly-Src announcement and Ruby example: https://community.fly.io/t/fly-src-authenticating-http-requests-between-fly-apps/20566
- Expanded opt-in behavior: https://community.fly.io/t/more-fly-src-authenticating-http-requests-between-fly-apps/26147
- Go parser: https://github.com/superfly/flysrc-go

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
5. If an app needs to authorize another Fly app as the caller, evaluate
   verified `Fly-Src` metadata before introducing shared internal tokens.

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

## Fly-Src App-To-App Auth

Use Fly-Src when a Fly HTTP service needs to authorize the calling Fly Machine,
app, or organization. It is source authentication for Fly-originating requests,
not a replacement for end-user auth, session auth, or third-party API auth.

When Fly Proxy populates source metadata, the receiver sees:

```text
Fly-Src: instance=<machine-id>;app=<app-name>;org=<org-slug>;ts=<timestamp>
Fly-Src-Signature: <base64-ed25519-signature>
```

Receiver behavior:

- Require both `Fly-Src` and `Fly-Src-Signature` on protected internal routes.
- Verify `Fly-Src-Signature` as a base64-encoded Ed25519 signature over the raw
  `Fly-Src` header value.
- Read the hex-encoded verification key from `/.fly/fly-src.pub` inside the
  Machine.
- Parse `instance`, `app`, `org`, and `ts` only after signature verification.
- Reject stale timestamps; the Fly Ruby example uses a 10-second freshness
  window.
- Authorize against the expected `app` and `org`, not just the existence of a
  valid signature.

Request path rules:

- Fly-Src was introduced for Flycast HTTP requests, where app-to-app traffic goes
  through Fly Proxy.
- Fly has also expanded Fly-Src to requests between Fly Machines over 6PN,
  including Flycast.
- For requests that do not go through Flycast, the caller must opt in by sending
  `Fly-Src-OptIn: *`; Fly will not populate `Fly-Src` without that header.
- This opt-in path is useful when a public Fly app should authenticate requests
  from unrelated Fly Machines without provisioning a Flycast address.

Security boundaries:

- A raw `Fly-Src` header is not trustworthy. Other apps can reach services over
  private networking paths and set arbitrary headers unless the receiver verifies
  `Fly-Src-Signature`.
- A valid signature proves Fly Proxy produced the source metadata, but it does
  not prove the caller's application-level intent. Treat SSRF in a trusted
  caller as a real risk because an attacker could cause that trusted app to emit
  a request with valid source metadata.
- Keep normal authorization logic narrow: allow only the specific source apps
  and orgs expected for the route.

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
