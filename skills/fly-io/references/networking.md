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
- Fly expanded the opt-in behavior for requests originating from Fly Machines
  and passing through Fly Proxy. Raw direct 6PN HTTP bypasses the proxy and
  must not be assumed to receive signed metadata.
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
  for the isolation boundary, such as tenant isolation or environment isolation
  within one organization. They are single-org only; for cross-org access, use
  separate organizations or a Flycast address allocated with `--org`.
- `fly apps create --network <network-id-or-name>` places a new app on a custom
  private network. flyctl has no command to list networks or read an app's
  network; discover it through the Machines API app object's `network` field.
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
- Check current egress pricing and per-pair Machine limits before allocation;
  confirm the region and scaling requirement, including temporary deploy capacity.
- Legacy machine-scoped egress IPs still exist but are no longer the default
  recommendation for new work; migrate one with
  `fly machine egress-ip promote <machine-id>`.

## Dynamic Routing

- Fly adds request headers such as `Fly-Client-IP`, `Fly-Region`,
  `Fly-Forwarded-Port`, and forwarded protocol headers when the HTTP handler is
  used.
- `Fly-Prefer-Region`, `Fly-Prefer-Instance-Id`, `Fly-Force-Instance-Id`, and
  `Fly-Force-Region` can influence routing for clients that know where they
  want to land; the `Force` variants have no nearest-region fallback.
- Use `fly-replay` when an app should accept a request in one place and ask Fly
  Proxy to replay it to another region, app, or Machine. This is useful for
  write-primary routing, tenant locality, and regional data placement.
- Requests over 1MB cannot be replayed. Route large uploads directly to storage
  or steer them with `Fly-Prefer-Region` instead.
- Make replay targets explicit and bounded. Avoid loops and verify auth context
  survives replay.

## Diagnose the actual path

Trace caller → DNS/address → listener → proxy/handler → health check → process.
Record whether the failure is resolution, connect, TLS, HTTP, or authorization.
From a caller Machine inspect `.internal`/`.flycast` resolution and try the
actual service port; a successful laptop request does not test private DNS.
Compare listeners, `internal_port`, process assignments, checks, Machine state,
and public/private IP allocations. Check autostart only for proxy-routed traffic.
Do not change exposure or allocate addresses just to investigate.

## Pattern: an application-controlled router

[Playing Traffic Cop with Fly-Replay](https://fly.io/blog/how-to-fly-replay/)
uses a small router to map a hostname to a tenant app, then return `fly-replay`.
This helps when tenant placement or write-primary locality belongs to application
state. Keep destination services configured and audit their public IPs so direct
access cannot bypass the intended entrypoint. Validate tenant authorization before
choosing a target; replay does not supply that authorization.

Use the [current routing contract](https://fly.io/docs/networking/dynamic-request-routing/)
for body limits, timeout/fallback, cache behavior, and cross-network/org routing.
The blog's old Apps v2 enablement command is obsolete; do not copy it. Default
replay scope is the same org and network; wider routing requires the documented
receiver permissions. Cache routing only when stale placement is acceptable;
it must remain correct if Fly consults the router again.
