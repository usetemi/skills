# Tailscale Policy And Security

Official docs:

- Grants: https://tailscale.com/docs/features/access-control/grants
- Policy syntax: https://tailscale.com/kb/1337/policy-syntax
- Tailscale SSH: https://tailscale.com/kb/1193/tailscale-ssh
- Device posture: https://tailscale.com/kb/1288/device-posture
- Tailnet Lock: https://tailscale.com/kb/1226/tailnet-lock
- Funnel node attributes: https://tailscale.com/docs/features/tailscale-funnel

## Decision Path

1. Identify whether the tailnet uses grants, legacy ACLs, or a mixed migration.
2. Model users and workloads with groups and tags before writing broad rules.
3. Add policy tests for every meaningful allow rule, deny expectation, and SSH
   path.
4. Keep network access, SSH login permission, posture checks, app capabilities,
   and public Funnel eligibility separate in the policy review.

## Grants vs ACLs

- Prefer grants for new policy because they can express network access and
  application-layer capabilities in one policy model.
- Keep legacy ACLs when working inside an existing ACL-only tailnet unless the
  user asked to migrate or the new feature requires grants.
- In mixed policies, avoid duplicating the same intent in both `grants` and
  `acls`; it makes tests harder to reason about.
- A network grant still needs the destination to be reachable. It does not
  approve subnet routes, make a node advertise routes, or change DNS.

Minimal grant shape:

```hujson
{
  "groups": {
    "group:dev": ["alice@example.com", "bob@example.com"],
  },
  "tagOwners": {
    "tag:web": ["group:dev"],
  },
  "grants": [
    {
      "src": ["group:dev"],
      "dst": ["tag:web"],
      "ip": ["tcp:443"],
    },
  ],
  "tests": [
    {
      "src": "alice@example.com",
      "accept": ["tag:web:443"],
      "deny": ["tag:web:22"],
    },
  ],
}
```

## Policy File Basics

- Tailnet policy is HuJSON, not strict JSON. Comments and trailing commas are
  allowed, but automation should still parse and render it deliberately.
- Use `groups` for human teams and `tagOwners` for who may assign device tags.
- Tags replace user identity for access decisions on tagged devices. A tagged
  production node should be owned by an automation or admin group, not by a
  single developer account.
- Use `hosts` or `ipsets` for named IP ranges when policy would otherwise
  repeat the same CIDRs.
- Use `tests` and `sshTests` as regression tests. Add them before or alongside
  rule changes in GitOps flows.
- Device approval, route approval, posture collection, and auth-key creation
  are admin/control-plane decisions outside a simple allow rule.

## Tailscale SSH

- Enabling `tailscale up --ssh` or `tailscale set --ssh=true` only starts the
  SSH capability on the node. Login still depends on policy.
- SSH policy has two layers: who may reach the node over the tailnet and who may
  SSH as a local user.
- Prefer check mode for sensitive hosts so users must re-authenticate before
  privileged SSH sessions.
- Include `sshTests` for production SSH paths, especially when allowing
  `autogroup:nonroot`, local admin users, or tagged servers.

Example SSH policy shape:

```hujson
{
  "ssh": [
    {
      "action": "check",
      "src": ["group:ops"],
      "dst": ["tag:prod"],
      "users": ["ubuntu", "root"],
    },
  ],
  "sshTests": [
    {
      "src": "alice@example.com",
      "dst": ["tag:prod"],
      "accept": ["ubuntu"],
      "check": ["root"],
    },
  ],
}
```

## Device Posture

- Device posture attributes are useful for organization-owned devices and
  sensitive applications. They are usually overkill for personal tailnets and
  early prototypes.
- Treat posture as an additional condition, not a replacement for least
  privilege. A compliant laptop should still receive only the access it needs.
- Check current docs before naming posture attributes because supported signals
  and platform behavior change.

## App Capabilities

- Grants can carry application capabilities that Tailscale-aware apps or Serve
  identity/app-capability headers can consume.
- Use app capabilities when the service needs app-level authorization decisions
  after network admission.
- Keep capability names scoped and explicit. Avoid broad capability grants that
  become a second, untested authorization system.

## Funnel Controls

- Funnel is public internet exposure. The tailnet policy must allow the node to
  use Funnel through `nodeAttrs`.
- Limit Funnel eligibility to explicit users, groups, or tags. Do not use a
  broad default for organization tailnets.
- Pair Funnel changes with a public exposure review: hostname, port, target
  service, authentication at the app layer, and log visibility.

Example public Funnel eligibility shape:

```hujson
{
  "nodeAttrs": [
    {
      "target": ["tag:funnel"],
      "attr": ["funnel"],
    },
  ],
}
```

## Tailnet Lock

- Tailnet Lock adds a signing layer for node keys. It is a high-security
  control with operational consequences.
- Do not casually recommend enabling Tailnet Lock during routine setup. First
  confirm who will hold signing keys, how recovery works, and how automation,
  routers, Kubernetes, and ephemeral nodes will be signed.
- For production reviews, call out whether Tailnet Lock is appropriate, but
  route implementation through current official docs and an explicit rollout
  plan.
