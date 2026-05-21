# Fly Production Review

Official docs:

- Production checklist: https://fly.io/docs/apps/going-to-production/
- App availability: https://fly.io/docs/reference/app-availability/
- Organization roles: https://fly.io/docs/security/org-roles-permissions/
- Access tokens: https://fly.io/docs/security/tokens/
- Logging: https://fly.io/docs/monitoring/logging-overview/
- Metrics: https://fly.io/docs/monitoring/metrics/
- Arcjet: https://fly.io/docs/security/arcjet/
- Sentry: https://fly.io/docs/monitoring/sentry/

## Review Order

1. Identify the app, org, primary region, process groups, data services, public
   IPs, and private networks.
2. Run read-only checks where credentials are available:

   ```bash
   fly status
   fly config validate --strict
   fly checks list
   fly services list
   fly ips list
   fly releases
   fly volumes list
   fly mpg list
   ```

3. Report the Fly-native decision, exact commands/config, and the gotchas
   checked. Do not deploy during review unless asked.

## Production Defaults

- Use Managed Postgres for production Postgres.
- Run at least two Machines for request-serving production apps.
- Use explicit CPU/RAM sizing after measuring memory and latency.
- Put the primary app region near the primary database or users. Avoid accidental
  cross-region database chatter.
- Configure service-level health checks for anything receiving Fly Proxy
  traffic.
- Use rolling deploys by default. Use canary or bluegreen only when health
  checks and volume constraints allow it.
- Disable autostop for latency-sensitive services, long-lived workers, and any
  app whose state layer cannot tolerate unexpected stop/start.
- Use app-scoped deploy tokens for CI and least-privilege org roles for humans.

## Public Exposure Audit

Check:

```bash
fly ips list
fly services list
```

Rules:

- If a service is configured in `fly.toml` and public IPs exist, treat that
  service as public.
- Flycast does not make a service private if the app also has public IPs for the
  same service config.
- Shared IPv4 is usually enough for public HTTP apps. Dedicated IPv4 is for
  concrete protocol or routing needs.
- Anycast inbound IPs are unrelated to outbound allowlisting. Use app-scoped
  egress IPs for fixed outbound source IPs.

## Data Durability Audit

- For MPG, confirm backups, restore practice, region, plan, storage size, and
  migration process.
- For volumes, confirm at least two volumes where availability matters, separate
  hardware zones where possible, application replication, snapshot retention,
  and an external backup plan.
- For Tigris, confirm bucket, credentials, lifecycle expectations, and whether
  objects replace any inappropriate volume use.
- For SQLite with Litestream, confirm the volume, Tigris secrets, restore drill,
  RPO/RTO, and replication logs or alerts.
- For Redis, confirm it is cache/coordination unless the plan and app semantics
  deliberately make it durable state.
- For LiteFS, confirm autostop/autostart is off, backups exist, and primary
  write routing is understood.

## Observability

- `fly logs` is useful for immediate debugging, but production apps need a log
  retention/export story.
- Use Fly metrics and checks for platform visibility.
- Add app-level metrics for queue depth, worker freshness, DB migration status,
  replication lag, and business-critical paths.
- Consider Sentry for application errors and Arcjet or a WAF extension when
  public apps need bot, abuse, or edge protection.
- For workers without public services, use watchdog jobs, metrics, queue alerts,
  or Machines API checks. Fly service health checks do not cover them.

## CI/CD And Release Safety

- Keep `fly.toml` in the repo used by CI.
- Use deploy tokens instead of broad personal auth tokens when possible.
- Add GitHub Actions concurrency for deploy workflows.
- Make release commands idempotent. They run before rollout, can stop deploys,
  and cannot access volumes.
- For migrations, decide rollback behavior before switching traffic.
- After changes, prefer:

  ```bash
  fly config show --local
  fly config validate --strict
  fly checks list
  fly status
  ```

  Then deploy only when the user asked for it.

## Extensions

Current `fly extensions` includes services such as Arcjet, Sentry, Tigris
storage, Supabase, Upstash Vector, Wafris, MySQL, and Kubernetes. Treat
extensions as strong options when they match the production need, but verify the
current extension help and official docs before provisioning:

```bash
fly extensions --help
fly extensions <name> --help
```
