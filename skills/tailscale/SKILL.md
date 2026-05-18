---
name: tailscale
description: "Use for any Tailscale platform work: tailnets, tailscaled, tailscale CLI, grants and ACLs, MagicDNS, Serve, Funnel, Tailscale Services, app connectors, subnet routers, exit nodes, Tailscale SSH, Kubernetes Operator, containers, tsnet, auth keys, OAuth clients, CI/CD automation, API usage, GitOps policy workflows, connectivity debugging, and production diagnostics."
---

# Tailscale Platform

Use this skill for any Tailscale work, from local development connectivity to
production tailnet architecture and incident diagnostics.

Tailscale changes quickly. Ground version-sensitive advice in the local CLI and
current official docs before making claims about flags, policy syntax, product
limits, or Kubernetes CRDs.

## First Steps

1. Infer posture from context.
   - For personal tailnets, MVPs, local dev, demos, and scrappy startup work,
     give the fastest viable path first.
   - For organizations, production, shared tailnets, sensitive systems, or
     compliance contexts, use secure-first defaults.
   - If the context is unclear and the posture changes commands, exposure, key
     handling, or access policy, ask before changing state.

2. Inspect local project and system context before prescribing commands.

   ```bash
   rg --files -g 'tailnet*.json' -g '*tailscale*' -g 'acl.hujson' -g 'policy.hujson' -g 'docker-compose*.yml' -g 'Dockerfile*' -g '.github/workflows/**' -g 'k8s/**' -g 'helm/**'
   command -v tailscale
   tailscale version
   tailscale --help
   tailscale <subcommand> --help
   ```

3. Prefer read-only checks first unless the user explicitly asks to mutate local
   Tailscale state, tailnet policy, Kubernetes resources, or remote resources.

   ```bash
   tailscale status
   tailscale status --json
   tailscale netcheck
   tailscale ping <peer>
   tailscale dns status
   tailscale serve status
   tailscale funnel status
   ```

4. Use official Tailscale docs as the source of truth. Third-party posts can
   help discover issues, but do not encode them as facts unless confirmed by
   official docs or the current CLI.

## Reference Routing

- Read `references/policy-security.md` for grants vs ACLs, policy HuJSON,
  tags, groups, tests, `sshTests`, Tailscale SSH, device posture, app
  capabilities, Funnel `nodeAttrs`, and Tailnet Lock cautions.
- Read `references/routing-connectors.md` for subnet routers, exit nodes, app
  connectors, MagicDNS, split DNS, route injection, HA/failover, regional
  routing, DERP/direct diagnostics, `tailscale netcheck`, `tailscale ping`, and
  `tailscale status`.
- Read `references/expose-services.md` for Tailscale Serve, Funnel, Tailscale
  Services, TailVIPs, HTTPS certs, identity headers, app capabilities headers,
  service config files, drain/advertise flows, TCP/TLS forwarding, and public
  exposure gotchas.
- Read `references/automation-containers.md` for auth keys, OAuth clients,
  workload identity federation, ephemeral nodes, GitHub Actions, Docker,
  userspace networking, serverless patterns, `tsnet`, API usage, and GitOps
  policy workflows.
- Read `references/kubernetes.md` for the Tailscale Kubernetes Operator,
  tags/OAuth prerequisites, ingress, egress, API server proxy, Connector,
  ProxyGroup, ProxyClass, Recorder, subnet routers, app connectors, version
  compatibility, and CNI notes.
- Read `references/production-diagnostics.md` for production review checklists,
  least privilege, key expiry, device approval, logs, network flow logs, audit
  logs, webhooks/log streaming, update policy, incident diagnostics, and safe
  read-only commands.

## Defaults

- For new access policy, prefer grants. Use legacy ACLs only when maintaining an
  existing ACL-only policy or when the needed behavior is not yet expressible in
  grants.
- Treat `tailscale up` flags as a complete desired state. To change one
  preference, prefer `tailscale set` when available.
- Keep route advertisement, route approval, client route acceptance, and access
  policy separate in explanations. Routing makes paths reachable; policy
  decides who may connect.
- Treat auth keys, OAuth client secrets, and generated auth keys as secrets.
  Prefer tagged, ephemeral, short-lived, scoped automation identities.
- For public exposure, make the Serve vs Funnel boundary explicit: Serve is
  tailnet-private; Funnel is internet-public.
- Use dry runs, status commands, policy tests, and local config inspection
  before changing production tailnets.

## Gotchas To Surface Early

- `tailscale up` with flags requires the complete set of desired settings; an
  omitted setting can trigger an error or reset only with `--reset`.
- Grants are preferred for new policy, but existing tailnets may still use ACLs.
- Subnet routes, exit-node routing, app connector route injection, and access
  rules are separate control layers.
- Serve and Funnel cannot both own the same node, DNS name, and port combination
  as private and public exposure at the same time.
- Auth keys expire; connector or automation key expiry can fail closed.
- MagicDNS and split DNS behavior depends on resolver setup and platform DNS
  integration.
- DERP relay use is a performance and reachability fallback, not plaintext
  traffic. Tailscale traffic remains WireGuard-encrypted between nodes.

## Output Style

When answering Tailscale tasks, include:

1. The fastest viable path.
2. The security hardening path when relevant.
3. Exact commands, policy shape, Kubernetes manifests, or API calls.
4. The gotchas checked and any remaining risk.

Downrank dashboard-only instructions, stale CLI flags, broad tailnet access, and
long-lived reusable keys unless the user explicitly asks for them.
