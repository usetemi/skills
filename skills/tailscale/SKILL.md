---
name: tailscale
description: Deploy, configure, review, troubleshoot, and automate Tailscale tailnets and the tailscale/tailscaled CLI, including grants and ACLs, Tailscale SSH, device posture, Tailnet Lock, Tailscale PAM, Serve, Funnel, Tailscale Services, tsidp, subnet routers, exit nodes, app connectors, peer relays, MagicDNS, the Kubernetes Operator, containers and tsnet, auth keys, OAuth clients, workload identity federation, the API, Terraform and GitOps, Aperture, and connectivity and production diagnostics.
---

# Tailscale

Inspect the project's policy file, deployment manifests, CI workflows, and
relevant runtime code before choosing changes, then check what the local client
and the tailnet actually run. A feature's availability depends on the client
version, the plan, and its release stage.

Ground commands, flags, limits, and availability in local help and current
official docs. Do not install tools, join a tailnet, or create keys, nodes, or
policy merely to inspect them.

```bash
command -v tailscale && tailscale version   # client version
tailscale version --daemon                  # tailscaled version, when it differs
tailscale --help; tailscale <subcommand> --help
tailscale status --json                     # peers, versions, routes, health
```

Help output is per installed version; a flag in the docs may not exist locally.
A surviving CLI flag is not proof that a feature is available on the plan.

## Read the relevant reference

- [Policy and security](references/policy-security.md): grants vs ACLs, tags,
  policy tests, Tailscale SSH and session recording, device posture, app
  capabilities, Tailnet Lock, key expiry, device and user approval, identity
  lifecycle, node sharing, Tailscale PAM (beta), and hardening.
- [Routing, connectors, and DNS](references/routing-connectors.md): route
  injection, subnet routers (autoApprovers, SNAT, HA, 4via6, site-to-site),
  exit nodes, app connectors, peer relays, connection types and DERP, CGNAT and
  addressing, MagicDNS and split DNS.
- [Exposing services](references/expose-services.md): Serve, Funnel, Tailscale
  Services, identity and app-capabilities headers, HTTPS certificates, and
  tsidp (OIDC provider).
- [Automation and API](references/automation-api.md): credential choice (workload
  identity federation, OAuth clients, auth keys), ephemeral nodes, the GitHub
  Action, non-interactive CLI, the API, Terraform, GitOps, and alpha APIs.
- [Containers, tailscaled, and tsnet](references/containers-tsnet.md): Docker
  image, state and credentials, userspace networking, serverless, tailscaled on
  Linux servers (state storage, declarative config), and tsnet.
- [Kubernetes](references/kubernetes.md): the Operator's ingress, egress, API
  server proxy, Connector, ProxyGroup, ProxyClass, Recorder, multi-tailnet,
  PeerRelay, and sidecars without the Operator.
- [Production diagnostics](references/production-diagnostics.md): read-only
  triage, netcheck, firewall and UDP, health and message IDs, debug and metrics,
  logging, audit and webhooks, outages, device lifecycle, node state encryption,
  updates, platform notes, and incident change discipline.
- [Aperture](references/aperture.md): the AI gateway, client setup, the two
  grant layers, config, MCP and HTTP connectors, and the CLI.

Load only the references the task needs; combine them for cross-cutting work.

## Defaults and gotchas that span references

- Infer posture. Personal tailnets and demos get the fastest viable path;
  organizations and shared tailnets get secure-first defaults. Ask before
  changing state when the choice alters exposure, key handling, or access.
- Write new access policy as grants; keep legacy ACLs only where an existing
  policy uses them or the behavior is not expressible in grants.
- Route advertisement, route approval, client acceptance, and access policy are
  separate gates that each fail alone. Serve is tailnet-private and Funnel is
  public; Funnel is gated separately by `nodeAttrs`.
- `tailscale up` with any flag needs the complete desired set (or `--reset`);
  `--auth-key`, `--force-reauth`, and `--qr` are exempt. Prefer `tailscale set`
  for one preference, but `set` lacks `--advertise-tags`, `--auth-key`, and
  `--login-server`, and the peer-relay flags exist only on `set`. Run
  `tailscale set --help` and `tailscale up --help` before choosing.
- Scripts hang on confirmation prompts: pass `--yes` to `serve`/`funnel` and
  `--accept-risk=<type>` to `up`/`set`/`down` (client 1.88.1 added the prompts).
- Treat auth keys, OAuth client secrets, and API tokens as secrets. Prefer
  workload identity federation, then tagged, ephemeral, scoped credentials.
- Version-gate recommendations. Tailscale Services and peer relays need client
  1.86+; `tailscale wait` is 1.96.2+ (see the references for finer floors). Check
  the versions the tailnet runs before recommending a feature.
- DERP relays carry WireGuard-encrypted traffic, not plaintext.
- The admin console is `console.tailscale.com`. Link canonical `/docs/` URLs;
  `/kb/NNNN` links are redirects.

## Research opportunities, not just syntax

Use these sources, in this order, for design and hard troubleshooting:

- Official docs at `tailscale.com/docs`. Append `.md` to a docs URL for clean
  Markdown (for example `https://tailscale.com/docs/features/exit-nodes.md`);
  pages carry a "Last validated" date. `https://tailscale.com/docs/llms.txt` is
  a curated index and `https://tailscale.com/api` is the interactive API
  reference; its OpenAPI spec is
  `https://api.tailscale.com/api/v2?outputOpenapiSchema=true` (the endpoints
  are stable unless noted, the spec document itself is not).
- The [changelog](https://tailscale.com/changelog) for client versions and
  feature stages, [security bulletins](https://tailscale.com/security-bulletins),
  the [blog](https://tailscale.com/blog), and health or console messages by ID
  at `https://tailscale.com/docs/reference/messages`.
- GitHub issues and source in `tailscale/tailscale` (and `tailscale/tsidp`,
  `tailscale/tailscale-skill`). Tailscale's own agent skill,
  `tailscale/tailscale-skill`, is alpha and unsupported; treat it as another
  community-grade source and verify it.
- r/Tailscale for field reports. The forum at `forum.tailscale.com` was sunset
  in July 2023 and is a read-only archive: useful history, often stale.

## Verify sources

Treat community reports and archived forum threads as diagnostic leads, not
platform guarantees. Check dates, the whole thread, staff corrections, and later
releases. Confirm a claim against current docs, the installed CLI, the source,
or a disposable reproduction. When sources conflict, state the conflict and use
the narrower confirmed contract. Do not claim behavior was tested when only
help or docs were read.

Check the release stage before recommending a feature. Alpha may break and has
no support obligation; beta is public, may still change, and has no support
obligation; only GA carries support and no breaking changes. The CLI marks
alpha and beta commands in `--help`. Do not put alpha or beta surfaces (for
example `tailscale switch`, `tailscale drive`, the Tailnets API, declarative
sharing, PAM) into production automation without a fallback, and re-check the
stage before each use. Confirm plan-dependent features against current plan pages.

## Stay within the task

Reviews and investigations are read-only: use `status`, `netcheck`, `ping`,
`serve status`, `dns status`, `get`, and GET calls on the API. Do not run `up`,
`set`, `serve`, `funnel`, `logout`, `kubectl apply`, or policy or API writes
during a review. Ask before mutating a shared tailnet, its policy, keys, or remote
nodes. For authorized changes, validate with policy tests or a dry run first,
make the bounded change, and verify the resulting behavior.

## Output

Report the recommendation or change, exact commands, policy, manifests, or API
calls, the evidence (docs pages and versions checked), gotchas checked, and
remaining risks. Give the fastest viable path and, for organizations, the
hardening path. Downrank dashboard-only steps, stale
flags, broad tailnet access, and long-lived reusable keys unless asked.
