# Machines and workload-specific compute

Use [Machines](https://fly.io/docs/machines/overview/) when code needs to create,
start, stop, or size individual instances. Fly Launch manages Machines for an
app; direct API ownership puts lifecycle reconciliation on your application.
Use [Sprites](sprites.md) when the requirement is a mutable, persistent execution
environment rather than control of container images, VM sizes, and volumes.

## Own the lifecycle

Read the [Machines API](https://fly.io/docs/machines/api/) and installed
`fly machine --help` for the operation. Inspect before mutating:

```sh
fly machine list -a <app>
fly machine status <machine-id> -a <app>
```

Record app, Machine ID, region, image, volume, restart policy, and ownership.
Do not expect `fly deploy` to manage ad-hoc Machines automatically. For API
updates, use the current configuration/version and leases where required;
handle asynchronous transitions by waiting for the requested state. A timeout
is not proof an operation failed: inspect before retrying creation or execution.

For jobs, make outputs durable outside ephemeral root storage, bound retries,
and separate job identity from Machine identity. Decide whether completion
stops or destroys the Machine. Stopped resources can retain storage costs.
For untrusted code, keep orchestration credentials outside the guest and choose
network/app isolation deliberately; a VM boundary does not revoke its secrets.

## Pattern: give expensive work its own compute

[Print on Demand](https://fly.io/blog/print-on-demand/) separates PDF rendering
from normal web serving (November 29, 2023; [official example](https://github.com/fly-apps/pdf-appliance))
and uses request routing to select the workload's
compute. This helps when occasional CPU/RAM-heavy work would dictate the size
of every web instance. Compare an HTTP worker with a queued job: a long render
may outlive the request even if the Machine can run it.

Verify the implementation against [process groups](https://fly.io/docs/launch/processes/),
[Machine sizing](https://fly.io/docs/machines/guides-examples/machine-sizing/),
and [request routing](https://fly.io/docs/networking/dynamic-request-routing/).
Choose separate apps when independent routing, permissions, or lifecycle are
needed; process groups suffice when only commands and resource sizes differ.
Do not add a new app solely because the blog's example used one.

## Pattern: per-user environments

The [per-user development blueprint](https://fly.io/docs/blueprints/per-user-dev-environments/)
uses a router, user-to-app/Machine mapping, and pre-created capacity. It is
useful when a product needs specific images, per-user compute, or explicit
lifecycle control. Persist ownership mappings; authenticate before routing to
an environment; reclaim abandoned compute and account for persistent storage.
An idle timeout does not preserve an ephemeral root filesystem. Avoid packing
thousands of user Machines into one app and relying on proxy autostop: its stop
loop is rate-limited, and app-level secrets are shared. Separate apps still need
an explicit private-network isolation design.

Compare Sprites when users mainly need persistent worktrees, installed tools,
exec, and rollback. Do not port the blueprint's Machine and volume orchestration
to Sprites without checking which responsibilities the product already owns.
