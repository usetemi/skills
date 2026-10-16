---
name: sprite-apps
description: >-
  Umbrella workflow for building and shipping web apps with Elixir, Ash, and
  Phoenix on Fly Sprites. Use when creating, restructuring, reviewing, or
  deploying a Phoenix/Ash app that runs on a Sprite, or when a web app build
  should compose software-design, observability, web-design, and fly-io
  judgment in one pass instead of treating them as separate reviews.
---

# Sprite Apps

**sprite-apps is an umbrella skill. It does not replace the skills under it;
it composes them, in order, for one kind of build: an Elixir/Ash/Phoenix web
app that runs on a Fly Sprite.**

The overlap with `fly-io` is deliberate. `fly-io` answers how the platform
works: CLI and API contracts, limits, networking, storage, current docs.
sprite-apps answers how we build the app that runs there: domain shape, code
judgment, interface design, telemetry, and the Sprites app pattern below.
When the two disagree about a platform fact, `fly-io` and current official
docs win; sprite-apps holds no platform contracts of its own.

## Load order

1. **Domain first.** If the domain model is unsettled, use `ddd` to settle
   the ubiquitous language and invariants before designing modules.
2. **`software-design`** for module and interface judgment: deep modules,
   information locality, one canonical statement per fact, design for the
   fresh reader.
3. **Web design** — [references/web-design.md](references/web-design.md):
   the interface discipline for every screen. Less is perfection; motion
   directs attention.
4. **The stack** — [references/elixir-ash-phoenix.md](references/elixir-ash-phoenix.md):
   Elixir, Ash, and Phoenix conventions for this build, including the
   Elixir anti-patterns pass.
5. **`observability`** for telemetry: instrumentation ships in the same
   change as the behavior it explains.
6. **`fly-io`** (its Sprites reference) for every platform operation:
   creating the Sprite, services, URL exposure, checkpoints, exec, and
   current limits. Verify commands against local help and current docs.

## The Sprites app pattern

One Sprite runs one app. These are our architectural commitments on top of
the platform, not platform guarantees:

- **Co-locate app and database.** The Phoenix release and Postgres run as
  two services in the same Sprite (`sprite-env` is the supervisor; there is
  no systemd). The app service claims the one HTTP port (8080) and is
  declared as needing Postgres, and the app still waits for Postgres itself
  before migrating and booting.
- **The database is never exposed.** Postgres listens on loopback and its
  unix socket only. Its only client lives in the same box, so it needs no
  public port and no public TCP.
- **Design to one origin.** A Sprite has exactly one public URL. An app
  that needs two distinct hosts or origins does not fit one Sprite; decide
  that before building, not at deploy time.
- **State lives on the persistent filesystem**, under one data directory:
  database files, socket dir, generated secrets. Boot is idempotent and
  safe after an unclean shutdown: processes start fresh on a cold wake, so
  nothing may depend on a process having survived.
- **Filesystem persistence is not a backup.** Ship `pg_dump` to object
  storage (S3-compatible, e.g. Tigris) and a tested restore as part of the
  app. A checkpoint is filesystem rollback; it is not an
  application-consistent database backup.
- **Secrets are generated, never committed.** First boot generates what the
  app needs (database password, Phoenix secret key base) onto the
  persistent disk with owner-only permissions. Everything else is
  environment configuration. Generate secrets with a tool that cannot be
  killed mid-write by a closed pipe; first-boot-only failures hide exactly
  there.
- **Memory is the wake cost.** Idle pause is automatic and clients must
  reconnect. Keep the boot path and resident footprint lean; a heavy app is
  a slow, expensive wake.

## Build order

1. Settle the domain language and invariants; name Ash resources after
   them.
2. Design each screen against the web-design reference before building it.
3. Implement in Ash and Phoenix per the stack reference, with
   `software-design` judgment at every module boundary.
4. Add observability in the same change: structured terminal records,
   closed result and reason vocabularies, and a `/health` endpoint that
   does a real database round trip, wired as the platform check.
5. Run the anti-patterns pass and the full test suite. Ship nothing with
   compiler warnings.
6. Deploy and operate through the `fly-io` skill's Sprites contracts.

## Verify before claiming done

- Full test suite green, warning-free build.
- Live end-to-end check against the running Sprite, not the local copy.
- `/health` passing live, doing its real dependency round trip.
- Live logs grepped for what must never appear: secrets, passphrases, and
  user content. Zero hits is the pass bar.
- Backup written and restore rehearsed into a separate database.
- For a stateful app, a restart check: kill the app and database, cold
  start, confirm committed data survived.

Report per discipline, not just "done": the web-design verdict, the
software-design calls made, the observability evidence, and the deploy
evidence each get a line.
