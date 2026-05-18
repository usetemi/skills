# Tailscale Service Exposure

Official docs:

- Tailscale Serve: https://tailscale.com/docs/features/tailscale-serve
- Tailscale Funnel: https://tailscale.com/docs/features/tailscale-funnel
- Tailscale Services: https://tailscale.com/docs/features/tailscale-services/
- Services config files: https://tailscale.com/docs/reference/tailscale-services-configuration-file
- Serve/Funnel examples: https://tailscale.com/kb/1247/funnel-serve-use-cases
- HTTPS certificates: https://tailscale.com/kb/1153/enabling-https
- CLI reference: https://tailscale.com/docs/reference/tailscale-cli

## Decision Path

1. Decide who should reach the service:
   - only tailnet identities: Serve
   - public internet users: Funnel
   - a stable tailnet service identity decoupled from one node: Tailscale
     Services
2. Confirm hostname, port, protocol, target process, and authentication layer.
3. Check current local config before adding exposure.
4. For public exposure, include app-layer auth, logs, rate limits, and removal
   steps.

Read-only checks:

```bash
tailscale serve status
tailscale serve status --json
tailscale funnel status
tailscale funnel status --json
tailscale status
```

## Serve

- Tailscale Serve exposes local files, directories, text, local HTTP services,
  TCP services, TLS-terminated TCP services, or Unix sockets to the tailnet.
- Serve is private to tailnet identities subject to policy.
- `tailscale serve <target>` runs in the foreground; `--bg` persists config in
  the background.
- Use `https+insecure://` only when proxying to a local HTTPS service with a
  self-signed or otherwise invalid certificate.
- Prefer `tailscale serve status` before changing an existing service so you do
  not overwrite an unrelated local exposure.

Examples:

```bash
tailscale serve 3000
tailscale serve --bg 3000
tailscale serve --https=443 http://127.0.0.1:3000
tailscale serve --tcp=5432 tcp://127.0.0.1:5432
tailscale serve reset
```

## Funnel

- Funnel exposes a local service to the public internet using Tailscale.
- Funnel requires tailnet policy eligibility through `nodeAttrs`; do not assume
  a node can use Funnel just because Serve works.
- Treat every Funnel change as public exposure. Check hostname, port, target,
  app-layer auth, secrets in responses, and logs.
- Serve and Funnel share the local serve configuration model. Avoid trying to
  make the same node/DNS name/port private and public at the same time.

Examples:

```bash
tailscale funnel 3000
tailscale funnel --bg 3000
tailscale funnel --https=443 http://127.0.0.1:3000
tailscale funnel reset
```

Minimal Funnel policy shape:

```hujson
{
  "nodeAttrs": [
    {
      "target": ["tag:funnel"],
      "attr": ["funnel"],
    },
  ],
}
```

## Tailscale Services And TailVIPs

- Tailscale Services provide stable service identities and virtual IPs for
  services, separate from any one device.
- Use Services when clients should target a service name or TailVIP instead of a
  specific node name.
- Service proxy nodes can advertise and drain service backends. This is useful
  for rolling maintenance and HA patterns.
- Keep service identity, backend node tags, and access grants explicit in
  production policy.

Commands to inspect current CLI behavior:

```bash
tailscale serve advertise --help
tailscale serve drain --help
tailscale serve get-config --help
tailscale serve set-config --help
```

## HTTPS Certificates

- HTTPS certificates for tailnet names depend on MagicDNS and HTTPS/cert
  settings in the tailnet.
- Use `tailscale cert <name>` only after checking current docs and whether the
  node is allowed to request certificates.
- Do not confuse certificates for tailnet-private HTTPS with public Funnel
  exposure.

Command shape:

```bash
tailscale cert <machine-or-service-name>.<tailnet-name>.ts.net
```

## Identity And Capability Headers

- Tailscale Serve can forward identity information to a local service. Use this
  when the upstream app needs to know the authenticated tailnet identity.
- App capabilities can be forwarded with `--accept-app-caps` for services that
  understand them.
- Treat these headers as trusted only from the local Tailscale proxy path. Do
  not expose the upstream directly on an untrusted interface where a client can
  forge headers.

Command shape:

```bash
tailscale serve --accept-app-caps=com.example.app/read,com.example.app/write 3000
```

## Config Files

- Use `tailscale serve get-config` and `tailscale serve set-config` for
  repeatable service exposure configuration.
- Store generated configs only when they do not contain environment-specific
  secrets. Review before committing.
- For GitOps, keep Serve/Funnel config review next to tailnet policy review so
  access and exposure change together.

Commands:

```bash
tailscale serve get-config tailscale-serve.json
tailscale serve set-config tailscale-serve.json
```

## Public Exposure Checklist

- Is the exposure Serve-private or Funnel-public?
- Which DNS name and port will clients use?
- What local process, port, directory, file, or socket is exposed?
- Is the upstream bound only to localhost or another intended interface?
- Does the app enforce auth for public users?
- Are identity headers protected from spoofing?
- How will logs, abuse, rollback, and key rotation be handled?
