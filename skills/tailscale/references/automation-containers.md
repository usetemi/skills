# Tailscale Automation And Containers

Official docs:

- OAuth clients: https://tailscale.com/docs/features/oauth-clients
- Workload identity federation: https://tailscale.com/docs/features/workload-identity-federation
- GitHub Action: https://tailscale.com/docs/integrations/github/github-action
- Ephemeral nodes: https://tailscale.com/docs/features/ephemeral-nodes
- Docker: https://tailscale.com/kb/1282/docker
- tsnet: https://tailscale.com/kb/1244/tsnet
- API: https://tailscale.com/api
- Policy syntax: https://tailscale.com/kb/1337/policy-syntax

## Decision Path

1. Identify whether the workload is a one-off CI job, long-running container,
   serverless task, embedded app, or infrastructure controller.
2. Prefer OAuth clients or workload identity federation for automation that can
   mint scoped auth keys just in time.
3. Use reusable auth keys only when the environment cannot support a stronger
   automation identity.
4. Tag automation nodes and write policy against tags, not human users.
5. Make cleanup explicit with ephemeral nodes where machines are short-lived.

## Auth Keys

- Auth keys are sensitive. Treat them like passwords or deploy tokens.
- Use pre-approved, tagged, ephemeral, short-lived keys for automation whenever
  possible.
- Key expiry can fail closed for routers, connectors, CI, and service proxies.
  Include expiry and rotation checks in production reviews.
- Avoid long-lived reusable keys in shared repos or broad CI environments.
- Prefer `file:` inputs for local CLI secrets so keys do not appear in shell
  history or process listings.

Command shape:

```bash
sudo tailscale up \
  --auth-key=file:/run/secrets/ts_authkey \
  --advertise-tags=tag:ci \
  --hostname=ci-${GITHUB_RUN_ID}
```

## OAuth Clients

- OAuth clients are the preferred control-plane automation primitive for many
  production workflows.
- Scope OAuth clients narrowly to the API operations and tags they need.
- Store client secrets in the platform secret store, not in repository files.
- For generated auth keys, prefer short expiry and ephemeral nodes unless the
  node needs durable identity.

## Workload Identity Federation

- Workload identity federation lets a supported identity provider token be
  exchanged for Tailscale auth without storing a long-lived Tailscale secret.
- Use it for CI/CD and cloud workloads that already have strong identity tokens.
- Check current CLI and docs for required `--client-id`, `--audience`, and
  `--id-token` usage because provider flows vary.

CLI shape:

```bash
tailscale up \
  --client-id=<oauth-client-id> \
  --audience=<audience> \
  --id-token=file:/run/secrets/oidc_token \
  --advertise-tags=tag:ci
```

## GitHub Actions

- Prefer the official Tailscale GitHub Action for CI jobs that need tailnet
  access.
- Use ephemeral, tagged identity for jobs so completed runners disappear from
  the tailnet.
- Keep policy narrow: the CI tag should reach only the build, deploy, or test
  endpoints it needs.

Workflow shape:

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: actions/checkout@v4
  - uses: tailscale/github-action@v3
    with:
      oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}
      audience: ${{ secrets.TS_OIDC_AUDIENCE }}
      tags: tag:ci
  - run: ./scripts/smoke-test-tailnet-service
```

## Containers

- Use the official Docker guidance for required capabilities, state, userspace
  networking, and sidecar patterns.
- Persist Tailscale state for long-running containers that should keep a stable
  node identity. Use ephemeral mode for disposable jobs.
- Userspace networking is useful when a container cannot create a TUN device,
  but it changes how traffic reaches local services.
- Do not put auth keys into Dockerfiles or committed compose files. Use secrets
  or environment injection from the runtime platform.

Common environment shape:

```yaml
services:
  tailscale:
    image: tailscale/tailscale:latest
    environment:
      TS_AUTHKEY: ${TS_AUTHKEY}
      TS_STATE_DIR: /var/lib/tailscale
      TS_USERSPACE: "false"
    volumes:
      - tailscale-state:/var/lib/tailscale
    devices:
      - /dev/net/tun:/dev/net/tun
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
volumes:
  tailscale-state:
```

## Serverless And Short-Lived Workloads

- For short-lived compute, prefer ephemeral nodes and just-in-time auth.
- Make teardown explicit where the platform can run cleanup. Ephemeral nodes
  reduce stale device accumulation but do not replace policy design.
- Confirm whether the platform supports TUN devices. If not, use userspace
  networking or app-level integration.

## tsnet

- `tsnet` embeds Tailscale directly into a Go program.
- Use it when the app should join a tailnet without requiring a separately
  managed `tailscaled` daemon.
- Store state deliberately. Ephemeral state is good for throwaway services; a
  stable service identity needs durable state.
- Keep auth and tag ownership scoped the same way as any other Tailscale node.

## API Usage

- Use the Tailscale API for repeatable operations such as device inventory,
  route approval, key generation, policy updates, and audits.
- Prefer OAuth clients over user API keys for automation.
- Make API updates idempotent where possible. Read current state, compute the
  desired change, apply the smallest mutation, and verify.
- Do not log tokens, generated auth keys, or full policy files if they contain
  sensitive comments or internal IP ranges.

## GitOps Policy Workflows

- Store tailnet policy in version control when the organization needs review
  and repeatability.
- Validate policy syntax and tests before applying.
- Require tests for expected denies, not only expected allows.
- Keep generated or environment-specific secrets out of policy files.
- After applying policy, verify with `tailscale status`, connectivity tests, and
  API reads rather than assuming the write succeeded.
