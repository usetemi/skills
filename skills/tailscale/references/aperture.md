# Aperture (AI Gateway)

Official docs:

- What is Aperture: https://tailscale.com/docs/aperture/what-is-aperture
- Configuration reference: https://tailscale.com/docs/aperture/configuration
- How grants work: https://tailscale.com/docs/aperture/how-grants-work
- Gateway grants vs tailnet policy grants:
  https://tailscale.com/docs/aperture/reference/aperture-vs-tailnet-grants
- Grant model access:
  https://tailscale.com/docs/aperture/how-to/grant-model-access
- Grant MCP tool access:
  https://tailscale.com/docs/aperture/how-to/grant-mcp-tool-access
- Per-user spending limits:
  https://tailscale.com/docs/aperture/how-to/set-per-user-spending-limits
- Built-in connectors:
  https://tailscale.com/docs/aperture/connectors/built-in-connectors
- Aperture CLI: https://tailscale.com/docs/aperture/cli
- GA announcement: https://tailscale.com/blog/aperture-ga
- Lethal-trifecta pattern: https://tailscale.com/blog/aperture-lethal-trifecta

## What It Is And When To Use It

Aperture is Tailscale's identity-aware AI/LLM gateway. It runs as a device on
the tailnet, and clients reach it by its MagicDNS name. It:

- reads the caller's identity from the tailnet, so clients hold no provider key
- injects the provider credential on the way out
- enforces per-user model access and spend quotas
- logs requests and runs pre-call guardrail hooks
- proxies MCP servers and HTTP APIs
- fronts OpenAI, Anthropic, Gemini, and OpenAI-compatible or self-hosted
  endpoints

Use it when an agent, CI job, or team needs LLM access without distributing
provider API keys, or when tool access for agents must follow identity and
audit requirements. Guardrail hooks choose `fail_closed` or `fail_open` for
the case where the hook service is unreachable; pick `fail_closed` for
anything that must not bypass the check
(https://tailscale.com/blog/aperture-audit-AI-agents).

Callers outside the tailnet connect through the Aperture CLI bridge or
`ts-unplug` (https://tailscale.com/docs/aperture/what-is-aperture).

## Release Stage

- The gateway is generally available (changelog 2026-08-25, launch blog
  2026-08-26): https://tailscale.com/changelog,
  https://tailscale.com/blog/aperture-ga.
- The Aperture CLI (https://tailscale.com/docs/aperture/cli) and the built-in
  Tailnet connectors
  (https://tailscale.com/docs/aperture/connectors/built-in-connectors) carry
  an alpha note in their docs.
- The 2026-06-16 changelog entry labeled Aperture chat, connectors, and
  sandboxes alpha. The GA entry does not restate their stage, so check the
  docs page before relying on it.
- Do not build durable automation on alpha surfaces' exact syntax without
  re-reading the docs page.

## Pointing A Client At Aperture

Set the client's API base URL to the instance's MagicDNS name and send a
placeholder key. Aperture supplies the real credential.

Claude Code, `~/.claude/settings.json`
(https://tailscale.com/blog/aperture-private-alpha), where `ai` is the
Aperture instance hostname:

```json
{
  "apiKeyHelper": "echo '-'",
  "env": {
    "ANTHROPIC_BASE_URL": "http://ai"
  }
}
```

The pattern is the same for other SDKs and tools: base URL to the instance,
any non-empty placeholder as the key.

## Grants: Two Places

Aperture grants use the `tailscale.com/cap/aperture` capability and can be
defined in either place
(https://tailscale.com/docs/aperture/reference/aperture-vs-tailnet-grants):

- The gateway's own configuration: dashboard Administration > Grants, or the
  JSON on Administration > Configuration.
- The tailnet policy file.

Differences that break copy-paste:

| Location | `dst` | `ip` |
| --- | --- | --- |
| Gateway config | omit (implicitly the gateway) | omit |
| Tailnet policy file | required, e.g. `["tag:aperture"]` | as for any grant |

A gateway-config grant pasted into the policy file without `dst` is accepted
but silently has no effect. The reverse fails validation, because `dst` is not
a valid field in gateway config. Define each grant in exactly one place:
defining the same grant in both adds no access and makes the effective policy
harder to reason about.

Gateway-config grant:

```json
{
  "src": ["group:ai-users"],
  "app": {
    "tailscale.com/cap/aperture": [
      { "role": "user" },
      { "models": "anthropic/**" }
    ]
  }
}
```

Tailnet policy-file form of the same grant adds the destination:

```json
{
  "src": ["group:ai-users"],
  "dst": ["tag:aperture"],
  "app": {
    "tailscale.com/cap/aperture": [
      { "role": "user" },
      { "models": "anthropic/**" }
    ]
  }
}
```

Rules
(https://tailscale.com/docs/aperture/how-to/grant-model-access,
https://tailscale.com/docs/aperture/how-grants-work):

- Access is deny-by-default. Without a matching grant a user can connect to
  the device but sees no models or MCP capabilities. A new gateway ships with
  a default grant giving all users all models; narrow or replace it.
- Without a `role` grant (`user` or `admin`) the user gets HTTP 403 even when
  model grants match. With a role but no matching `models` grant (or a model
  no provider serves) the request returns HTTP 404.
- Multiple matching grants merge additively; `admin` beats `user`. There is no
  deny rule. When several `models` patterns match, the most specific wins.
- `group:` sources need visible groups: add the `tailscale.com/visible-groups`
  node attribute to the Aperture device
  (https://tailscale.com/docs/aperture/visible-groups).
- Model patterns are globs: `**`, `anthropic/**`, `*/claude-sonnet*`,
  `openai/gpt-5.5`.

This is separate from ordinary network reachability: the tailnet access policy
still has to let the client reach the gateway device at all. Aperture and the
agents working through it remain bound by Tailscale's unidirectional
access-control rules (https://tailscale.com/blog/aperture-ga).

## Config Reference Essentials

The gateway config is one JSON document
(https://tailscale.com/docs/aperture/configuration). Top-level sections:
`providers`, `grants`, `quotas`, `hooks`, `exporters`, `database`,
`connectors`, `auto_cost_basis`, `flags`, `mcp`, `temp_grants`, `chat_models`.
`mcp` and `temp_grants` are deprecated; use `connectors` and `grants`.

Providers:

- `baseurl` must NOT include `/v1`. Aperture appends it, so a trailing `/v1`
  produces `/v1/v1/...` upstream and HTTP 405.
- `authorization` is `bearer` (default), `x-api-key`, or `x-goog-api-key`.
- `auth_mode`:
  - `""` or `override`: inject the configured key
  - `passthrough`: forward the client's own credential, falling back to the
    configured key
  - `none`: send no upstream credential
- Consumer subscription plans (Claude Pro/Max, ChatGPT Plus, Gemini Advanced)
  need `auth_mode: "passthrough"`.
- `compatibility` flags include `openai_chat` (on by default, but cleared when
  you enable another flag without mentioning it), `openai_responses`,
  `anthropic_messages`, `gemini_generate_content`, and `bedrock_model_invoke`.

Quotas
(https://tailscale.com/docs/aperture/how-to/set-per-user-spending-limits):

- A bucket has `capacity`, `rate` (for example `"$5.00/day"`; units are
  min, hour, day, week, month), and `on_exceed: reject`.
- `reject` is the only mode. It returns HTTP 429 with `Retry-After`. A request
  whose estimated cost would take the bucket below zero is rejected.
- A matching grant charges every quota in its `quotas` array at once, for
  example `{"bucket":"daily:<user>"}` plus a shared pool bucket.
- Lowering a bucket's capacity caps the existing balance.

Database: an empty retention duration means the Tailscale default of one year.

## MCP And HTTP Connectors

`connectors.servers.<id>` proxies an MCP server or an HTTP API through
Aperture so credentials stay in the gateway
(https://tailscale.com/docs/aperture/how-to/grant-mcp-tool-access,
https://tailscale.com/docs/aperture/configuration).

- `protocol` is `mcp` or `http`.
- `auth.type` is one of `bearer_token`, `api_key`, `basic`,
  `oauth2_client_credentials`, `oauth2_authorization_code`, `oauth2_dcr`.
- Connector IDs must match `[a-zA-Z][a-zA-Z0-9]*`: no hyphens or underscores,
  which the MCP wire format uses as separators.
- Reserved: IDs `aperture`, `tailscale`, `internal`; label `system`.

Three layers must all hold before a user reaches a connector: the connector is
declared in config, a grant matches, and (for OAuth connectors) the user has
completed credentials.

Access patterns are fully qualified: `connectorID/category/resource`.
Categories are `tools`, `resources`, `templates` (MCP) and `proxy` (HTTP).
`*` matches within one segment; `**` matches zero or more segments.

```json
{
  "src": ["group:ai-users"],
  "app": {
    "tailscale.com/cap/aperture": [
      { "connectors": ["github/**", "local/tools/*"] }
    ]
  }
}
```

Gotchas:

- A malformed pattern (more than two slashes, or an unknown category) is
  silently dropped, not reported. If a user cannot see a tool, check pattern
  shape first.
- Unauthorized tools are hidden ("unknown tool"); unauthorized HTTP proxy
  paths return 403 access denied. A missing tool is usually a grant problem,
  not a connector outage.
- A `label:` grant gives the whole connector, including `proxy`. Use FQN
  patterns when you need tool-level restriction.

## Built-In Tailscale Connectors

Alpha (see Release Stage). Introduced around GA
(https://tailscale.com/blog/aperture-ga,
https://tailscale.com/docs/aperture/connectors/built-in-connectors): connector
IDs `Tailnet` and `TailnetSSH`.

- `Tailnet` has one tool, `provision_node`. The user approves an authorization
  link, then the agent receives a single-use, short-lived auth key bound to the
  user's identity. By default the device carries the node attributes
  `custom:createdByAperture` and `custom:createdByAI`.
- `TailnetSSH` has `list_machines` and `run_command`. It connects as the
  Aperture node, so the tailnet's Tailscale SSH policy decides what it reaches.
- Access-control rules still bind Aperture and the agents behind it. All agent
  actions are audit-logged.
- Admins set each connector up from the dashboard (My Aperture > Connectors);
  setup does not grant other users access. Grant by ID, for example
  `{ "connectors": ["TailnetSSH/tools/list_machines"] }`. The `system` label
  never matches these connectors.

## Lethal-Trifecta Pattern

Goal: keep any one agent from holding private data, untrusted content, and an
external communication path at once
(https://tailscale.com/blog/aperture-lethal-trifecta, 2026-08-06).

1. Label each connector, for example `hasCustomerData` and `noCustomerData`.
2. Mark devices (sandboxes) that have internet egress with a custom device
   attribute, for example `custom:hasEgress`, and define postures over it.
   Device provisioning with OAuth apps can apply the attribute at creation so
   the user cannot change it.
3. In the tailnet policy file, use `srcPosture` to give egress-capable devices
   only the `noCustomerData` label and egress-free devices both labels:

```json
"postures": {
  "posture:hasEgress": ["custom:hasEgress == true"],
  "posture:noEgress": ["custom:hasEgress == false"]
},
"grants": [
  {
    "src": ["autogroup:member"],
    "srcPosture": ["posture:noEgress"],
    "dst": ["tag:aperture"],
    "app": {
      "tailscale.com/cap/aperture": [
        { "connectors": ["label:noCustomerData", "label:hasCustomerData"] }
      ]
    }
  },
  {
    "src": ["autogroup:member"],
    "srcPosture": ["posture:hasEgress"],
    "dst": ["tag:aperture"],
    "app": {
      "tailscale.com/cap/aperture": [
        { "connectors": ["label:noCustomerData"] }
      ]
    }
  }
]
```

Why it holds: the grants live in the tailnet policy, outside the gateway, and
Aperture keeps the LLM and MCP credentials outside the agent harness. Stated
threat model: an agent driven by an outside actor, not a malicious insider
such as a Tailscale admin.

For posture syntax and custom attributes, see
[policy-security.md](policy-security.md#device-posture).

## Aperture CLI (Alpha)

Announced 2026-05-20; alpha
(https://tailscale.com/blog/aperture-cli-AI-experimentation,
https://tailscale.com/changelog).

```bash
go install github.com/tailscale/aperture-cli/cmd/aperture@latest
aperture
```

Requires a recent Go toolchain; check the repository README for the minimum.

- Launches and configures coding agents against an Aperture instance: Claude
  Code, Codex, OpenCode, Gemini CLI, GitHub Copilot CLI, and others such as
  Droid and Pi.
- Bridge mode connects to the tailnet containing the Aperture instance
  without the Tailscale client, and can run alongside an existing VPN. Use it
  for hosts that cannot or should not join the tailnet.
- Because it is alpha, prefer the plain base-URL configuration above for
  anything that must keep working across releases.

## Quick Diagnosis

| Symptom | First check |
| --- | --- |
| HTTP 403 from the gateway | No `role` grant (`user` or `admin`) for the caller |
| Connects, but no models or tools listed | Deny-by-default: no matching grant, or grant in the wrong location |
| HTTP 404 from the gateway | Role granted, but no `models` grant matches the model, or no provider serves it |
| Policy-file grant has no effect | Missing `dst` (Aperture never receives the capability) |
| Upstream HTTP 405 | Provider `baseurl` includes `/v1` |
| HTTP 429 with `Retry-After` | Quota bucket exhausted; check every quota on the matching grant |
| Subscription login rejected | Provider needs `auth_mode: "passthrough"` |
| Tool "unknown" or proxy 403 | Grant pattern missing, malformed (silently dropped), or wrong category |
