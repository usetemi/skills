---
name: fly-io
description: Use when deploying, configuring, troubleshooting, reviewing, or architecting Fly.io apps and infrastructure. Covers flyctl, fly.toml, Fly Launch, Fly Machines, process groups, health checks, deployment strategies, private networking, 6PN, Flycast, Fly-Src app-to-app auth, egress IPs, volumes, Managed Postgres, Tigris, Redis, LiteFS, extensions, CI/CD, and production readiness.
---

# Fly.io Platform

Use this skill for any Fly.io work, including routine deploy/config changes and
architecture decisions for apps known to run on Fly.

Fly changes quickly. Ground decisions in the local CLI and current official docs
before making version-sensitive claims. When a Fly-authored feature is only
documented in Fly forum announcements or official example repos, say so and
avoid presenting it as broadly documented platform surface.

## First Steps

1. Inspect the project shape before prescribing commands.

   ```bash
   rg --files -g 'fly.toml' -g 'Dockerfile*' -g '.dockerignore' -g '.github/workflows/**' -g 'package.json' -g 'pyproject.toml' -g 'go.mod' -g 'Cargo.toml'
   ```

2. Check the current `flyctl` surface for the task.

   ```bash
   fly version
   fly help
   fly <command> --help
   ```

3. Prefer non-mutating validation unless the user explicitly asked to deploy or
   change remote resources.

   ```bash
   fly config show --local
   fly config validate --strict
   fly status
   fly checks list
   ```

4. Use official Fly docs as the source of truth for unstable details. Do not
   use arbitrary community posts as encoded facts. For Fly-Src, use the
   Fly-authored forum announcements and official example repo linked from
   `references/networking.md`, and state that limitation when it matters.

## Reference Routing

- Read `references/deploy-config.md` for `fly.toml`, process groups, health
  checks, deploy strategies, GitHub Actions, secrets, scaling, autostop, and
  config validation.
- Read `references/networking.md` for 6PN, `.internal`, Flycast, public
  services, private services, custom private networks, request routing headers,
  `fly-replay`, Fly-Src request source auth, and static egress IPs.
- Read `references/data-storage.md` for Managed Postgres, volumes,
  auto-extension, snapshots, backups, Tigris, Upstash Redis, LiteFS, and
  durability decisions.
- Read `references/production.md` for production reviews, security, orgs,
  tokens, public IP audits, backups, monitoring, logging, and extensions.

## Fly-Native Defaults

- For ordinary apps, prefer Fly Launch-managed apps (`fly launch`, `fly deploy`,
  `fly.toml`) over hand-managed Machines.
- Use `fly machine` or the Machines API only when the task needs per-Machine
  control, unmanaged workloads, one-app-per-customer isolation, or runtime code
  execution patterns.
- For production Postgres, prefer Managed Postgres (`fly mpg`) over legacy
  unmanaged Postgres.
- For object storage, prefer Tigris.
- For Redis, use Fly's Upstash integration unless the app has a clear reason to
  run its own Redis.
- For private proxy-routed services, prefer Flycast over raw `.internal` when
  the service needs Fly Proxy behavior such as autostart, load balancing, TLS,
  PROXY protocol, or DNS-hostile clients.
- For Fly app-to-app HTTP origin checks, use verified `Fly-Src` metadata when
  the request path goes through Fly Proxy and caller identity is the auth
  boundary. Do not replace user auth or third-party auth with Fly-Src.
- For fixed outbound allowlisting, prefer app-scoped static egress IPs with
  `fly ips allocate-egress`; do not recommend legacy machine-scoped egress IPs
  for new work.

## Gotchas To Surface Early

- Data locality: Machines, volumes, regions, and data durability are not
  interchangeable. Volumes are local NVMe slices, not replicated network disks.
- Network exposure: a service in `fly.toml` plus public IPs exposes that service
  publicly, even if the intended consumer is private or Flycast.
- Fly-Src: never trust `Fly-Src` without verifying `Fly-Src-Signature` against
  `/.fly/fly-src.pub`, and check timestamp freshness before authorizing.
- CLI surprises: current `fly launch --no-deploy` can also offer GitHub Actions
  setup in GitHub repos; use `--no-github-workflow` when that automation is not
  wanted.
- Process groups: defining `[processes]` makes the list complete. Removing a
  process group from config can destroy Machines in that group on deploy.
- Health checks: service-level checks affect routing, but failing checks do not
  restart or stop Machines by themselves.
- Secrets: `fly secrets set` restarts Machines unless staged; secrets are runtime
  env vars, not build args.
- Release commands: they run in temporary Machines without attached volumes.
- Egress: default outbound IPs are unstable. Allocate app-scoped egress IPs per
  region only when third parties require allowlisting.
- LiteFS: use with caution, keep off-site backups, and do not combine LiteFS
  with Fly Proxy autostop/autostart.
- GPUs: do not recommend Fly GPUs for new work. Fly docs say GPUs are deprecated
  and unavailable after August 1.

## Architecture Triggers

Pause for Fly-specific architecture thinking when the prompt involves state,
databases, volumes, private services, internal APIs, app-to-app auth, regions,
tenants, queues, workers, egress allowlisting, HA, failover, production, or cost
boundaries. In those cases, answer with:

1. The Fly-native recommendation.
2. The exact commands or `fly.toml` shape.
3. The gotchas checked and any remaining production risks.

Downrank beginner tutorials, dashboard-first workflows, deprecated offerings,
and experimental surfaces unless the user asks directly.
