# Tailscale Production Diagnostics

Official docs:

- Connection types: https://tailscale.com/docs/reference/connection-types
- Network flow logs: https://tailscale.com/docs/features/logging/network-flow-logs
- Audit logs: https://tailscale.com/docs/features/logging/audit-logging
- Webhooks: https://tailscale.com/kb/1213/webhooks
- Device approval: https://tailscale.com/kb/1099/device-approval
- Update clients: https://tailscale.com/kb/1067/update
- CLI reference: https://tailscale.com/docs/reference/tailscale-cli

## Safe Read-Only Commands

Start here during incidents and reviews:

```bash
tailscale version
tailscale status
tailscale status --json
tailscale netcheck
tailscale ping --verbose <peer>
tailscale ip
tailscale dns status
tailscale serve status
tailscale funnel status
tailscale bugreport
```

For hosts with systemd:

```bash
systemctl status tailscaled
journalctl -u tailscaled --since '1 hour ago'
```

For Kubernetes:

```bash
kubectl get pods -n tailscale
kubectl logs -n tailscale -l app=tailscale-operator --tail=200
kubectl get crd | rg 'tailscale'
```

## Production Review Checklist

- Policy uses least privilege with groups, tags, grants/ACLs, tests, and
  `sshTests`.
- Tag owners are narrow and do not let ordinary users self-assign production
  tags.
- Auth keys, OAuth clients, and workload identity federation are scoped,
  rotated, and monitored for expiry.
- Device approval and posture rules match the organization's trust model.
- Subnet routes, exit nodes, app connectors, Serve, Funnel, and Services have
  explicit owners and rollback steps.
- Public exposure through Funnel is intentional and app-layer auth is reviewed.
- Routers and connectors have HA where downtime matters.
- Logs, network flow logs, audit logs, and webhooks/log streaming are connected
  to the organization's monitoring process.
- Clients and routers have an update policy.
- Incident responders know how to collect bug reports and local logs without
  leaking secrets.

## Connectivity Triage

1. Is `tailscaled` running and logged in?
2. Does `tailscale status` show both peers?
3. Does `tailscale ping <peer>` work? Does it use direct, DERP, or peer relay?
4. Does policy allow the source to reach the destination and port?
5. If a subnet or app connector is involved, is the route advertised, approved,
   accepted by the client, and reachable from the router?
6. If DNS is involved, does `tailscale dns status` show expected MagicDNS or
   split DNS configuration?
7. If Serve/Funnel/Services are involved, does the local serve config expose the
   expected target and protocol?

## Access Policy Triage

- Read the policy as code, not prose. Identify the exact `src`, `dst`, and port.
- Check whether the destination is a user-owned node, tagged node, service,
  subnet CIDR, or app connector route.
- Add or update `tests` and `sshTests` before changing production policy.
- For denies, look for missing group membership, missing tag ownership, route
  not approved, posture mismatch, or wrong port/protocol.
- Avoid emergency broad grants without a removal plan.

## Logs And Audit Data

- Audit logs track configuration and administrative activity. Use them to answer
  who changed policy, keys, devices, routes, or settings.
- Network flow logs track network activity metadata. Use them for visibility
  into who connected to what, subject to plan and configuration availability.
- Webhooks or log streaming can feed external monitoring and SIEM systems.
- Do not paste raw logs into public issue trackers without reviewing hostnames,
  user identities, IP ranges, keys, and internal service names.

## DERP And Performance

- DERP indicates relay fallback for connectivity, not plaintext traffic.
- Common causes of relay paths include UDP blocking, NAT behavior, firewalls,
  captive networks, and asymmetric routing.
- Use `tailscale netcheck` for local network conditions and `tailscale ping
  --verbose <peer>` for peer-specific path behavior.
- Optimize for direct connections only after confirming policy, DNS, route, and
  service configuration are correct.

## Key And Credential Expiry

- Expired auth keys can prevent replacement routers, connectors, or CI jobs
  from joining.
- Expired OAuth client secrets or insufficient scopes can break automation that
  generates keys or updates policy.
- Include expiry checks in runbooks for app connectors, subnet routers,
  Kubernetes operator credentials, GitHub Actions, and long-running containers.

## Incident Change Discipline

- Capture current state before changing it.
- Prefer `tailscale set` for one preference rather than reconstructing a full
  `tailscale up` command under pressure.
- Keep public exposure changes reversible: record the old Serve/Funnel config,
  policy diff, and rollback command.
- After mitigation, verify from the affected client path, not only from the
  router or admin workstation.
