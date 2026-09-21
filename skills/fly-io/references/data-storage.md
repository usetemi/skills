# Fly Data And Storage

Official docs:

- Managed Postgres: https://fly.io/docs/mpg/
- Volumes: https://fly.io/docs/volumes/overview/
- App config mounts: https://fly.io/docs/reference/configuration/
- Tigris: https://fly.io/docs/tigris/
- Upstash Redis: https://fly.io/docs/upstash/redis/
- LiteFS: https://fly.io/docs/litefs/
- Litestream: https://litestream.io/
- Litestream on Tigris: https://litestream.io/guides/tigris/
- Litestream in Docker: https://litestream.io/guides/docker/
- Litestream tips: https://litestream.io/tips/
- Fly Prisma SQLite: https://fly.io/docs/js/prisma/sqlite/

## Storage Decision Defaults

- Production Postgres: use Managed Postgres (`fly mpg`).
- Object storage: use Tigris.
- Redis/cache/queues: evaluate Fly's Upstash integration against the client
  command set, latency, eviction, persistence, and connection requirements.
- Durable local files: use Fly Volumes only when the app understands local
  storage, replication, and backups.
- SQLite with restore-based durability: use a Fly Volume plus Litestream to
  Tigris for simple single-writer apps.
- SQLite at the edge: consider LiteFS only with care, off-site backups, and
  autostop/autostart disabled.

## Managed Postgres

Use `fly mpg` for production Postgres. It is Fly's managed service with HA,
backups, failover, monitoring, encryption, connection pooling, and storage
management.

Useful commands:

```bash
fly mpg list
fly mpg create --name <cluster> --region <region> --plan <plan>
fly mpg attach <cluster-id> --app <app> --variable-name DATABASE_URL
fly mpg status <cluster-id>
fly mpg backup list <cluster-id>
fly mpg backup create <cluster-id>
fly mpg restore <cluster-id>
fly mpg connect <cluster-id>
fly mpg proxy <cluster-id>
fly mpg databases --help
fly mpg users --help
```

Guidance:

- Place MPG near the app's primary region; account for cross-region latency
  and network billing using [current pricing](https://fly.io/docs/about/pricing/).
- Select plans, supported Postgres versions, extensions, and available regions
  from `fly mpg create --help` and the current MPG docs. Check feature availability
  before promising alerting, migration tooling, or a particular service generation.
- `fly mpg restore` creates a separately billed new cluster; it does not overwrite
  the source. Verify backup/PITR coverage and plan connection cutover separately.
- For deploys that run migrations, use app-level `release_command`, but remember
  release Machines have no volumes.
- Legacy unmanaged `fly postgres` clusters are unsupported by Fly support.
  Mention them only for existing apps or explicit requests.

## Volumes

Fly Volumes are local persistent NVMe storage attached to Machines. Treat them
like a disk inside one server, not a cloud network disk.

Core constraints:

- A volume belongs to one Fly App.
- A volume exists on one server in one region.
- A volume can attach to only one Machine, and a Machine can mount only one
  volume at a time.
- Volumes are independent. Fly does not replicate data between volumes for the
  app.
- Check current size limits before choosing an `auto_extend_size_limit`.
- Root filesystems are ephemeral by default. Anything important must live
  outside the root filesystem or be reconstructable; `[[vm]]`
  `persist_rootfs = "restart"`/`"always"` is an available override.
- Volumes are not available during image builds or release commands.

Production guidance:

- Provision at least two Machines and two volumes when the app needs volume data
  to stay available.
- Put redundant volumes in separate hardware zones when possible.
- Build application-level replication or use a data system that handles it.
- Take backups outside Fly snapshots for important data. Automatic snapshots are
  useful but should not be the only backup plan.
- Check current snapshot pricing and retention before setting
  `fly volumes update --snapshot-retention`. Test restoration into a new volume.
- Volumes can grow but not shrink. Plan size and retention deliberately.

Useful commands:

```bash
fly volumes list
fly volumes create <name> --size <gb> --region <region> --count 2
fly volumes extend <volume-id> --size <gb>
fly volumes snapshots list <volume-id>
fly volumes snapshots create <volume-id>
fly volumes update <volume-id> --snapshot-retention <days>
```

Mount and auto-extension example:

```toml
[[mounts]]
  source = "data"
  destination = "/data"
  auto_extend_size_threshold = 80
  auto_extend_size_increment = "1GB"
  auto_extend_size_limit = "5GB"
```

Use auto-extension to reduce emergency disk-full incidents, but still alert on
usage and make the limit explicit. Auto-extension is not a replication or backup
strategy.

## Tigris Object Storage

Use Tigris for S3-compatible object storage close to Fly apps. It fits user
uploads, generated assets, logs, backups, and other object workloads that should
not live on a local volume.

Useful commands:

```bash
fly storage create
fly storage list
fly storage status <bucket>
fly storage update <bucket>
fly storage destroy <bucket>
```

Capabilities worth knowing:

- Shadow buckets (`fly storage create/update --shadow-*` flags) support migration
  from existing storage. Write-through requires `--shadow-write-through`; do not
  assume configuring a shadow alone enables dual writes. Verify cutover and
  failure behavior in [Tigris docs](https://www.tigrisdata.com/docs/).
- `--public`/`--private` toggle bucket visibility, and `--custom-domain` serves
  a bucket from a production hostname.
- For bucket branching or snapshots, check the current Tigris API contract
  separately from flyctl; do not infer database-consistent backups from a bucket copy.

Check generated secrets and bucket region behavior in current docs before
hardcoding SDK configuration. Prefer app secrets for keys and bucket names.

## SQLite With Litestream

Use Litestream when SQLite simplicity is a better fit than a separate database
server and the app can tolerate restore-based recovery.

Default Fly shape:

- Store the database on a volume, usually `/data/<app>.db`.
- Create Tigris storage with `fly storage create --app <app>` and use the
  generated secrets.
- For Prisma SQLite apps, inspect the `fly launch` generated Litestream setup
  before replacing it.
- Run Litestream with the app, typically `litestream replicate -exec "<cmd>"`.
- Restore on boot with `litestream restore -if-db-not-exists -if-replica-exists
  /data/<app>.db`, then start replication.

Minimal replica shape:

```yaml
dbs:
  - path: /data/<app>.db
    replica:
      url: s3://${BUCKET_NAME}?endpoint=fly.storage.tigris.dev&region=auto
```

SQLite pragmas and gotchas:

- Litestream requires WAL mode and will enable it if the app has not.
- Set `PRAGMA busy_timeout = 5000` on app connections.
- Enable `PRAGMA foreign_keys = ON` on every app connection.
- Use one writer for a database replica path. Multiple apps replicating to the
  same bucket path can break restores.
- Test restore before calling this production-ready.
- Treat the default async replication window as possible data loss during a
  catastrophic host failure.
- For direct backup queries through Litestream VFS, check the installed
  Litestream version and its VFS docs; do not treat that as a writable replica.
- Never put durable SQLite on the root filesystem or a network filesystem.

## Upstash Redis

Use Fly's Upstash Redis integration for managed Redis-compatible storage when
the app needs caching, rate limiting, job coordination, or lightweight state.

Useful commands:

```bash
fly redis plans
fly redis create
fly redis list
fly redis status <name>
fly redis connect <name>
fly redis proxy <name>
```

Do not treat Redis as the primary durable database unless the app and selected
plan are explicitly designed for that.

## LiteFS

LiteFS can replicate SQLite at the edge, but it is not the default answer for
ordinary production databases.

Rules:

- Do not combine LiteFS with Fly Proxy autostop/autostart. Official docs warn
  this can risk rollback and data loss.
- Keep regular off-site backups. Evaluate community backup tooling separately;
  do not imply Fly operates or supports it.
- Put LiteFS data on a persistent volume.
- Ensure write paths route to the primary and read-after-write behavior is
  understood.
- LiteFS Cloud docs are deprecated because LiteFS Cloud was retired on
  October 15, 2024. LiteFS itself was not retired.

Use LiteFS only when SQLite locality is a deliberate architecture choice and the
team understands the operational model.

## Redis selection and diagnosis

Separate disposable cache data from queue state. For BullMQ, verify Redis command
compatibility and connection behavior with the installed BullMQ version; its
[production guidance](https://docs.bullmq.io/guide/going-to-production) requires
`noeviction` and discusses persistence and reconnect settings. Confirm the chosen
Upstash plan can supply the required behavior before selecting it. Do not apply
cache eviction to a queue merely because both use Redis.

Use Fly's integration endpoint and region intentionally; check whether a client
is using TCP Redis or an HTTP API, TLS requirements, and access from the caller's
network. Local clients may need `fly redis proxy`; `127.0.0.1` inside an app is
that Machine, not the Redis service. Investigate DNS, connection churn, timeouts,
command errors, and plan limits before resizing or replacing the service.

Self-host only when a verified requirement justifies owning upgrades, private
listeners, persistent volumes, backups, restore, replication, and failover.
A single Redis Machine with a volume is not HA. HTTP autostart cannot wake a
queue worker that only polls Redis; use an appropriate worker lifecycle.
