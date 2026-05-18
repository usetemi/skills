# Fly Data And Storage

Official docs:

- Managed Postgres: https://fly.io/docs/mpg/
- Volumes: https://fly.io/docs/volumes/overview/
- App config mounts: https://fly.io/docs/reference/configuration/#the-mounts-section
- Tigris: https://fly.io/docs/tigris/
- Upstash Redis: https://fly.io/docs/upstash/redis/
- LiteFS: https://fly.io/docs/litefs/

## Storage Decision Defaults

- Production Postgres: use Managed Postgres (`fly mpg`).
- Object storage: use Tigris.
- Redis/cache/queues: use Fly's Upstash Redis integration unless self-hosting is
  explicitly required.
- Durable local files: use Fly Volumes only when the app understands local
  storage, replication, and backups.
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
fly mpg connect <cluster-id>
```

Guidance:

- Place MPG near the app's primary region unless data residency or latency says
  otherwise.
- Current CLI supports Postgres major versions 16 and 17; verify with
  `fly mpg create --help` before choosing.
- MPG supports `pgvector`; PostGIS can be enabled when provisioning.
- Some features remain under development in official docs, including
  customer-facing alerting and database migration tooling. Do not assume those
  exist without checking current docs.
- For deploys that run migrations, use app-level `release_command`, but remember
  release Machines have no volumes.
- Downrank legacy unmanaged `fly postgres` clusters for new production work.
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
- Root filesystems are ephemeral. Anything important must live outside the root
  filesystem or be reconstructable.
- Volumes are not available during image builds or release commands.

Production guidance:

- Provision at least two Machines and two volumes when the app needs volume data
  to stay available.
- Put redundant volumes in separate hardware zones when possible.
- Build application-level replication or use a data system that handles it.
- Take backups outside Fly snapshots for important data. Automatic snapshots are
  useful but should not be the only backup plan.
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

Check generated secrets and bucket region behavior in current docs before
hardcoding SDK configuration. Prefer app secrets for keys and bucket names.

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
- Keep regular off-site backups.
- Put LiteFS data on a persistent volume.
- Ensure write paths route to the primary and read-after-write behavior is
  understood.
- LiteFS Cloud docs are deprecated because LiteFS Cloud was retired on
  October 15, 2024. LiteFS itself was not retired.

Use LiteFS only when SQLite locality is a deliberate architecture choice and the
team understands the operational model.
