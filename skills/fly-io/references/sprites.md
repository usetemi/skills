# Sprites operations and integration

## Choose the product

- Fly Launch apps: image-based services with `fly.toml`, deploys, process groups,
  explicit regions, sizing, and networking.
- Direct Machines: application-owned per-instance images, compute, and lifecycle.
- Sprites: persistent mutable Linux environments for agents, user code, and
  development sessions, with exec, filesystem access, checkpoints, and idle pause.

Sprites has its own CLI and API. Do not use `fly machine`, Fly Volumes, or
`fly deploy` to manage a Sprite. See the [overview](https://docs.sprites.dev/)
and current capacity/pricing before making workload guarantees.

## Authentication, targeting, and files

Read [CLI commands](https://docs.sprites.dev/cli/commands/) and local help before
running commands. If `sprite` is absent, report that; installation is a separate
task. Use explicit organization and Sprite selection in automation:

```sh
sprite --help
sprite login -o <org>
sprite list -o <org>
sprite exec -o <org> -s <name> -- pwd
sprite console -o <org> -s <name>
sprite exec -o <org> -s <name> --file ./input.txt:/home/sprite/input.txt -- cat /home/sprite/input.txt
sprite exec -o <org> -s <name> -- cat /home/sprite/output.txt > ./output.txt
```

`exec --dir` selects a working directory; `--tty` is for interactive programs.
Prefer non-TTY file transfers. `sprite use` writes per-directory selection;
inspect it when a command targets the wrong environment. Check whether automatic
local port forwarding is desired (`exec --no-port-forward` disables it).

[Authentication](https://docs.sprites.dev/cli/authentication/) uses Fly account
access and Sprites org tokens. CLI login state and SDK tokens are separate
inputs. Keep tokens in local credential storage or CI secrets; do not paste them
into chat, dump `~/.sprites/sprites.json`, or disable keyring storage just to
inspect authentication. Check selected org and permissions before reauthenticating;
do not log out unrelated Fly sessions as a routine troubleshooting step.

## Creation and removal

For an authorized new environment, `sprite create -o <org> --skip-console <name>`
creates it without opening a console. Idle pause is automatic; closing a console
is not deletion. `sprite destroy -o <org> -s <name>` removes the environment:
export needed work and confirm its identity before destruction. Do not use
recreation as the first response to an exec or authentication failure.

## Persistence and checkpoints

The [lifecycle contract](https://docs.sprites.dev/concepts/lifecycle/) distinguishes
warm suspension (memory can resume) from cold wake (processes start fresh).
Filesystem state persists independently of idle compute; network clients must
reconnect. Do not rely on a process surviving indefinitely or copy the overview's
broad “memory between runs” wording into a durability guarantee.

The [checkpoint contract](https://docs.sprites.dev/concepts/checkpoints/) is a
snapshot of the writable filesystem overlay, not memory, processes, sockets,
or the base image. Restore replaces that overlay and restarts the environment,
terminating active sessions. This resolves the apparent conflict with warm
suspension: restore is filesystem rollback, not process continuation.

```sh
sprite checkpoint create -o <org> -s <name> --comment "before experiment"
sprite checkpoint list -o <org> -s <name>
sprite restore -o <org> -s <name> <checkpoint-id>
```

Restore overwrites current work. Capture anything that must survive first and
confirm the intended Sprite/checkpoint. Check completion/readiness before the
next operation; an accepted restore is not proof the environment is ready.
Checkpoints cannot undo external database writes, published messages, or leaked
credentials. Flush application state appropriately; do not promise an
application-consistent snapshot of unrelated external systems.

[Building Agents that Don't Break Themselves](https://fly.io/blog/building-agents-that-dont-break-themselves/)
(June 8, 2026) demonstrates recovering both project files and toolchains. Apply
that pattern before risky sandbox edits, bounded by the filesystem contract.
The January [implementation post](https://fly.io/blog/design-and-implementation/)
is architectural history, not today's storage implementation contract; later
[engineering changes](https://fly.io/blog/kurt-scott-money-sprites/) replaced it.

## Services and activity

Use [services](https://docs.sprites.dev/concepts/services/) for processes that
must return after cold wake. `sprite-env` runs inside the Sprite:

```sh
sprite exec -o <org> -s <name> -- sprite-env services list
sprite exec -o <org> -s <name> -- sprite-env services create web --cmd python3 --args "-m,http.server,3000" --http-port 3000
sprite exec -o <org> -s <name> -- sprite-env services get web
```

Serve only an intended public directory in a real application. `--cmd` is the
binary; arguments use `--args`. The URL defaults to port 8080; one service can
claim an HTTP port. Registered services restart after crashes/cold wake, but an
idle service does not by itself prevent pause. Use the [Tasks API](https://docs.sprites.dev/keeping-sprites-running/)
for work that needs an active hold. Avoid keepalive loops as a substitute.
Logs live under `/.sprite/logs/services/`; Sprites does not run systemd.

## Networking and exposure

[Networking](https://docs.sprites.dev/concepts/networking/) separates an HTTPS
URL from local TCP forwarding (`sprite proxy 3001:3000`). Stop local proxy
sessions when finished. Do not assume Fly `.internal` DNS or org 6PN membership
is part of Sprites networking.

URLs default to org-authenticated access; public mode removes that gate.
Check the installed CLI's URL/config help: the command reference documents
`sprite url update --auth public|sprite`, while the networking guide shows
`sprite config update --url-auth public|sprite`. Use the supported form for the
installed version and verify the resulting setting. Changing to public is an
exposure change, not a remedy for a 401. Keep application authorization where
needed, and test both unauthenticated and authenticated access after changes.

Egress is unrestricted unless a policy is applied. An empty rules list does not
mean deny-all. Current policies are managed externally and visible read-only at
`/.sprite/policy/network.json`. Consult the API for rule precedence and enforcement;
check DNS refusal separately from connect/TLS errors. [Connectors](https://docs.sprites.dev/concepts/connectors/)
can broker external credentials without placing the upstream token in the guest;
verify the connector's destination and permissions before relying on it.

## API and SDK contracts

Use the [API reference](https://sprites.dev/api) for the base URL
`https://api.sprites.dev/v1`, bearer authentication, exec sessions, filesystem,
checkpoints, services, and network policy. Read the specific endpoint contract:
streamed exec/checkpoint responses are not necessarily one JSON document.
Handle exit codes separately from transport success and cancellation separately
from disconnect. Inspect state before retrying non-idempotent operations.

Official SDKs and examples are linked from [integrations](https://docs.sprites.dev/integrations/).
For JavaScript/TypeScript, inspect [superfly/sprites-js](https://github.com/superfly/sprites-js)
and the installed `@fly/sprites` version. `SpritesClient` selects a named Sprite;
`execFile` takes an executable and argument array. Prefer it to interpolated shell
commands. Check that version's filesystem, streaming, timeout, and error APIs
rather than guessing method names from another SDK. Keep org tokens outside
untrusted guests and browser bundles; grant only the access the task needs.

## Troubleshooting without destroying evidence

- Authentication: verify org, selection, token availability, and endpoint first.
- Exec transport: distinguish command exit from WebSocket/HTTP connection failure;
  reconnect after wake/restore and inspect whether work already completed.
- HTTP: check URL auth, service definition, port, listener, and startup logs.
- Missing process: distinguish warm resume from cold wake; register a service
  when restart is required, or use a task hold for bounded active work.
- Resource pressure: inspect memory, disk, and process behavior before assuming a
  checkpoint defect. Do not destroy the Sprite to diagnose an unexplained hang.

An [April 2026 forum report](https://community.fly.io/t/sprites-become-unusable-when-agents-checkpoint/27678)
initially blamed checkpoints and later identified an application memory leak.
That correction supports checking resource pressure, not a general workaround
or a guarantee about checkpoint reliability. Cross-check future reports against
current maintenance docs and reproducible evidence before recommending changes.
