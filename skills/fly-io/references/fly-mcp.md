# Fly MCP

`https://mcp.fly.io` is Fly.io's hosted MCP server: one Streamable HTTP
connection for Fly apps, Machines, volumes, app secrets, Managed Postgres, and
Sprites. The server's guide, including the full tool catalog, is
`https://mcp.fly.io/guide.md`; read it for a tool's current behavior rather than
relying on this file.

## Setup

Register the server as `fly`, the name `fly setup agent` writes. Registering it
again under the guide's `fly-mcp` name, or installing a Fly plugin that bundles
its own `.mcp.json`, creates a second connection to the same server.

```sh
# Claude Code
claude mcp add --scope user --transport http fly https://mcp.fly.io
claude mcp login fly
claude mcp get fly

# Codex
codex mcp add fly --url https://mcp.fly.io
codex mcp login fly
codex mcp list
```

There is no API-token or bearer-header option: each client signs in through
browser OAuth. On a machine reached over SSH, add `--no-browser` to either
`login` command, open the printed URL in a local browser, and paste the redirect
URL back when prompted. The client refreshes the token afterwards. A new MCP
server's tools load at session start, so restart the agent session after
registering.

## Grant

The consent screen chooses the organization, the existing apps the connection
may touch, the Fly scopes, and the Sprites name prefix and creation limit. Tools
outside the grant do not appear, every call is checked against the grant at
call time, and revoking the connection fails the next call. Grant the apps and
scopes the work needs; leave out `*:delete`, `fly:machines:exec`,
`fly:machines:sensitive:read`, and `fly:secrets:write` unless the task requires
them. Re-consent to widen a grant; retries never do.

## Use

- Call `get_fly_context` first. It reports the organization, app bindings,
  per-resource scopes, and Sprites restrictions; check the organization before
  any write.
- Read before writing: `get_app`, `list_machines`, `get_volume`, or
  `get_postgres_cluster` on the target first. Mutations are not retried; after a
  lost response, inspect the resource before repeating the call.
- Confirm with the user before any delete, `exec_machine_command`, secret write,
  volume extension, memory change, network-policy replacement, or checkpoint
  restore, naming the target and the change. This skill is the only
  confirmation step when no client hook guards these tools.
- `get_sprite_info` reads Sprite metadata without waking the Sprite; runtime,
  file, service, and log reads may wake it.

## Limits

The server does not deploy, create apps, provision products other than
Machines, volumes, Managed Postgres clusters, and Sprites, or administer
organizations. IP addresses and certificates are read-only. Managed Postgres
tools never delete anything, change users or passwords, or return passwords.
Secret tools return names and digests, never values. Use `flyctl` for
deployment and anything outside the catalog.

## Feedback

`submit_feedback` reports a Fly.io platform bug, a documentation or tool
description mismatch, or a missing capability to Fly.io. Pass the `request_id`
from the result's `_meta` (`io.fly/request_id`) or the JSON-RPC error's `data`.
Never use it for errors in the user's application, and never include secrets,
tokens, or customer data.
