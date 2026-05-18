# Fly Deploy And App Config

Official docs:

- App config: https://fly.io/docs/reference/configuration/
- Deploy: https://fly.io/docs/launch/deploy/
- Process groups: https://fly.io/docs/launch/processes/
- Health checks: https://fly.io/docs/reference/health-checks/
- Secrets: https://fly.io/docs/apps/secrets/
- GitHub Actions: https://fly.io/docs/launch/continuous-deployment-with-github-actions/

## Config Workflow

Start by reading the app config and current local CLI behavior:

```bash
fly version
fly launch --help
fly deploy --help
fly config show --local
fly config validate --strict
```

Use `fly status`, `fly checks list`, `fly releases`, and `fly services` for
read-only remote inspection when app credentials are available. Do not run
`fly deploy`, `fly launch`, `fly scale`, `fly secrets set`, `fly ips`, or
resource creation commands unless the user asked for remote changes.

## New Apps

- `fly launch` creates a Fly App and `fly.toml`. Use `--no-deploy` when the user
  wants a reviewable config before the first deploy.
- Current `flyctl` exposes `--no-github-workflow`; in GitHub repos, launch may
  offer to provision a deploy workflow, token, and GitHub secret. Let the prompt
  drive this. Use `--no-github-workflow` when CI setup is not part of the task.
- Use `--db mpg` for production Postgres when launch should provision a database.
  Use `--no-db`, `--no-redis`, and `--no-object-storage` to avoid surprise
  services.
- Prefer an explicit `--primary-region` for production apps, chosen near the
  main database or primary users.

## `fly.toml` Structure

- `app` names the Fly App used by default. Commands can override it with `-a`,
  and some commands can use `-c` for a non-default config path.
- `primary_region` controls where `fly deploy` creates new Machines and sets the
  `PRIMARY_REGION` runtime environment variable.
- `[env]` is for non-sensitive runtime strings. Use `fly secrets` for secrets.
  Build-time values require build args or build secrets, not runtime secrets.
- Use `[http_service]` for normal HTTP/HTTPS apps on ports 80 and 443.
- Use `[[services]]` for non-standard ports, multiple services, raw TCP, UDP,
  Flycast services, custom handlers, or multiple process groups.
- If the app should not be reachable through Fly Proxy at all, omit
  `[http_service]` and `[[services]]`.

## Process Groups

- `[processes]` defines named commands such as `web`, `worker`, or `cron`.
  Commands act like Docker `CMD`; they do not replace `ENTRYPOINT`.
- Once `[processes]` exists, flyctl treats it as the complete process list. Add
  `app = "..."` explicitly if the default `app` process should remain.
- `fly deploy` creates at least one Machine for new process groups and destroys
  Machines for process groups removed from `fly.toml`.
- Attach services to the right process group with `processes = ["web"]`.
  Fly Proxy routes by service port, not by intent; avoid external port
  collisions between processes.
- Scale horizontally per process with `fly scale count web=2 worker=1` and
  vertically per process with `fly scale vm ... --process-group web`.

## Deploy Behavior

- `fly deploy` updates Fly Launch-managed Machines as a group. Machines created
  by `fly machine run` may be unmanaged and are not automatically reconciled by
  deploy.
- If an eligible public service lacks public IPs, first deploy can allocate a
  dedicated Anycast IPv6 and shared Anycast IPv4.
- `release_command` runs once before a release in a temporary Machine. It has
  network, env, and secrets, but no attached volumes, and non-zero exit stops
  deploy.
- For migrations, make `release_command` idempotent and set an appropriate
  timeout with `[deploy] release_command_timeout = "10m"` or the deploy flag.
- Deployment strategies:
  - `rolling` is the default and works with volumes.
  - `immediate` is for urgent replacement when risk is understood.
  - `canary` and `bluegreen` require capacity for extra Machines; they cannot be
    used for Machines with attached volumes.
  - `bluegreen` needs at least one health check.
- Configure `max_unavailable` for rolling deploys when availability matters.

## Health Checks

- Service-level TCP or HTTP checks control whether Fly Proxy routes traffic to a
  Machine.
- Top-level `[checks]` are useful for monitoring but do not affect routing.
- A failing check does not restart or stop a Machine. Pair checks with alerting
  and operational response.
- HTTP checks expect success from the configured endpoint. They do not follow
  redirects, so a forced HTTP-to-HTTPS redirect can make a health check fail.
- Workers and jobs without services need indirect health signals such as queue
  depth, watchdog jobs, metrics, or Machines API status checks.

## Secrets And Files

- `fly secrets set NAME=value` stores runtime secrets and updates Machines,
  causing restarts unless `--stage` is used.
- `fly secrets set --stage` makes the secret available only after a later deploy
  or `fly secrets deploy`.
- Secret values cannot be read back through Fly. Use `fly secrets list` for
  names and digests only.
- `[[files]]` can mount secret contents as files at Machine boot, but referenced
  secret values must be base64 encoded.

## CI/CD

- Keep `fly.toml` committed when GitHub Actions deploys from the repo.
- Prefer app-scoped deploy tokens for CI:

  ```bash
  fly tokens create deploy -x 999999h
  ```

- Store the token as `FLY_API_TOKEN`, run `flyctl deploy --remote-only`, and use
  GitHub Actions concurrency so multiple pushes do not deploy over each other.
- Review generated workflows. Match the branch name, app config path, monorepo
  working directory, and whether deploy should run for PRs, pushes, or tags.
