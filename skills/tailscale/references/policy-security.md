# Tailscale Policy And Security

A grant never approves or advertises a route; the separate route gates are in
[routing-connectors.md](routing-connectors.md#route-injection). Funnel is gated
separately by `nodeAttrs` ([expose-services.md](expose-services.md#funnel-public)).

Docs: [policy file](https://tailscale.com/docs/reference/syntax/policy-file),
[grants](https://tailscale.com/docs/reference/syntax/grants),
[Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh),
[device posture](https://tailscale.com/docs/features/device-posture),
[Tailnet Lock](https://tailscale.com/docs/features/tailnet-lock),
[tags](https://tailscale.com/docs/features/tags),
[security best practices](https://tailscale.com/docs/reference/best-practices/security).

## Decision Path

1. Read the current policy first (admin console, or GET
   `/api/v2/tailnet/{tailnet}/acl`). Note whether it uses `grants`, `acls`, or
   both.
2. Model people with `groups` and workloads with `tags` before writing rules.
3. Add `tests`/`sshTests` for each allow and expected deny; run them before and
   after a change.
4. Review network access, SSH login, posture, app capabilities, and Funnel
   eligibility as separate items.

## Grants vs ACLs

Grants are the preferred syntax and are feature complete with ACLs; only grants
get new features. ACLs stay supported indefinitely and can coexist with grants
in one file, so do not rewrite an ACL-only policy just to modernize it. `via`
and application capabilities (`app`) exist only in grants
([grants vs ACLs](https://tailscale.com/docs/reference/grants-vs-acls)). The
default policy uses grants syntax on new tailnets and never-edited policy files
([changelog](https://tailscale.com/changelog)).

Sections: `grants`, `acls`, `ssh`, `autoApprovers`, `nodeAttrs`, `postures`,
`tagOwners`, `groups`, `hosts`, `ipsets`, `tests`, `sshTests`. The file is
HuJSON. `autogroup:members` is a legacy alias of `autogroup:member`; both cannot
appear in one file.

```hujson
{
  "groups": {"group:dev": ["alice@example.com", "bob@example.com"]},
  "tagOwners": {"tag:web": ["group:dev"]},
  "grants": [
    {"src": ["group:dev"], "dst": ["tag:web"], "ip": ["tcp:443"]},
  ],
  "tests": [
    {"src": "alice@example.com", "accept": ["tag:web:443"], "deny": ["tag:web:22"]},
  ],
}
```

Semantics ([grants syntax](https://tailscale.com/docs/reference/syntax/grants)):

- Deny by default; no `action` field. Each grant needs `src`, `dst`, and at
  least one of `ip` or `app`.
- Matching grants UNION. A more specific grant never narrows a broader one; to
  narrow access, remove the broader grant.
- An `app` capability applies only if src also has network-level access to dst
  (exception: peer relay `tailscale.com/cap/relay`).
- `ip`: `*` (all ports, TCP/UDP/ICMP), `<port>` or `<lo>-<hi>` (also
  TCP/UDP/ICMP), `<proto>:*` for portless protocols (`icmp:*`), and
  `<proto>:<port|range>` such as `tcp:443`. Only TCP, UDP, and SCTP have ports.

Selectors ([policy file](https://tailscale.com/docs/reference/syntax/policy-file)):

- `*` as src includes devices, approved subnets, and `autogroup:shared`.
- `autogroup:self` covers only user-owned devices (not tags) and cannot combine
  with `autogroup:tagged`. `autogroup:member` includes invited users, not users
  of shared devices.
- `user:*@domain` and `localpart:*@domain` take no partial wildcards and cannot
  use shared domains such as gmail.com.
- Exit nodes need `dst: autogroup:internet`, not the exit-node device; see
  [routing-connectors.md](routing-connectors.md#exit-nodes).
- `via` ([docs](https://tailscale.com/docs/features/access-control/grants/grants-via)):
  values must be tags of routers the source can already reach. Omit it (or
  `[]`/`null`) to allow any exit node, subnet router, or app connector. Grants
  are additive, so a broader grant without `via` still allows the paths a
  narrower `via` grant was meant to pin; audit for overlaps.

### Migrating ACLs to grants

([migration](https://tailscale.com/docs/reference/migrate-acls-grants))

- Drop `action`; port/`proto` move into `ip`; `srcPosture` copies unchanged; the
  `ssh` section is not migrated.
- An ACL `dst` mixing ports across targets (`["tag:web:80","tag:dev:22"]`) must
  split into one grant per target; a merged grant silently widens access.
- The console's "Convert to grants" button rewrites `acls` immediately with no
  confirmation. Review the diff before saving; the change is audit-logged and
  revertible.

## Validation

([troubleshooting](https://tailscale.com/docs/reference/troubleshooting/grants))

- Syntax errors and undefined groups/tags are rejected on save. A group or tag
  that exists but is empty or unapplied passes and matches nothing.
- A failing `tests` or `sshTests` entry makes Tailscale reject the policy.
- `tests`: `src` (no wildcards), `accept`/`deny` as `host:port` with one numeric
  port, optional `proto` (ICMP: `"proto":"icmp"`, port 0), `srcPostureAttrs` when
  rules use postures. Destinations may be an IP, host, user, group, tag, or
  `svc:` name; never CIDRs. `tests` do not cover app capabilities.
- `sshTests`: `src`, `dst`, and `accept`/`check`/`deny` lists of usernames.
  The docs' prose says "disallow" for `accept`/`check`; that is a typo.
- Community lead (2025-07-24, no staff response): plan-gated rules reportedly
  passed save and `tests` on a free plan yet dropped traffic
  (https://github.com/tailscale/tailscale/issues/16643). Check plan limits
  before trusting green tests.

## Tags

([tags](https://tailscale.com/docs/features/tags))

- A device is user-owned OR tagged: applying a tag removes the user identity,
  and authenticating as a user strips tags. Tags are not ANDed in rules; use a
  composite tag such as `tag:prod-database`. Tagged devices cannot SSH to
  user-owned devices. Tagged devices get key expiry disabled on first tagged
  authentication.
- `tagOwners` owners may be users, groups, autogroups, or tags; `tagOwners: []`
  means only Owners, Admins, and Network admins. Those roles may apply any tag;
  IT admin may not.
- A credential (OAuth client or auth key) may request only its full tag set, or
  tags that one of its tags owns in `tagOwners`. Ownership is one hop: if
  `tag:a` owns `tag:b` and `tag:b` owns `tag:c`, `tag:a` cannot apply `tag:c`.
  A subset needs explicit ownership (make the tag its own owner).
- `--advertise-tags` cannot remove tags from an auth-key device; issue a new key.
  IP sets cannot contain tags, and `autogroup:tagged` cannot define an IP set or
  a custom group.

## Other Policy Sections

- `autoApprovers` (routes, exit nodes, Services): first-advertisement timing and
  approver choice are in
  [routing-connectors.md](routing-connectors.md#autoapprovers).
- `ipsets`: `ipset:<name>` lists of `add`/`remove <target>` processed in order
  (plain targets are implicit adds only if the set has no `remove`). Targets:
  CIDR, IP, `host:<name>`, `autogroup:internet`, other ipsets; no tags or cycles.
  Pattern: subtract private ranges from `autogroup:internet` to limit exit-node
  reach ([IP sets](https://tailscale.com/docs/features/tailnet-policy-file/ip-sets)).
- Funnel is gated by the `funnel` node attribute; scoping and the default-policy
  entry are in [expose-services.md](expose-services.md#funnel-public).
- The device web interface is at `http://100.100.100.100` locally; `tailscale
  set --webclient` also serves it on `<tailscale-ip>:5252` to anyone whose policy
  allows that port. Restrict with a grant on 5252, or disable everywhere with
  `nodeAttrs` `{"target":["autogroup:member"],"attr":["disable-web-client"]}`
  ([docs](https://tailscale.com/docs/features/client/device-web-interface)).

## Tailscale SSH

([Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh))

Two rule sets are needed: a grant/ACL letting src reach dst on port 22, and an
`ssh` rule.

```hujson
{
  "ssh": [
    {"action": "check", "src": ["group:ops"], "dst": ["tag:prod"],
     "users": ["ubuntu"], "checkPeriod": "12h"},
  ],
  "sshTests": [
    {"src": "alice@example.com", "dst": ["tag:prod"], "check": ["ubuntu"]},
  ],
}
```

- Fields: `action` (`accept`|`check`), `src` (not `*`), `dst`, `users`, optional
  `checkPeriod`, `acceptEnv`, `srcPosture`, `recorder`/`enforceRecorder`.
- `dst` may be a tag, `autogroup:self` (when src is only users/groups), or the
  single named user matching src; not `*`, IPs, hostnames, or ports. Port 22 only.
- Users must already exist on the host; Tailscale creates none. Omitted `users`
  uses the client's local username. `localpart:*@domain` is plan-gated.
- Privilege trap: changing `dst` from `autogroup:self` to a tag while keeping
  `users: ["autogroup:nonroot"]` lets every permitted src SSH as ANY nonroot
  account on the tagged host. List explicit usernames for tag destinations.
- If a check and an accept rule both match, the check rule applies and only its
  `users` apply. A tagged src cannot use check mode.
- `checkPeriod`: 1 minute to 168h, default 12h, or `"always"` (breaks tools that
  open many connections, such as Ansible). A default-period check covers all
  check-mode destinations; a custom period covers that destination only.
  Per-rule `checkPeriod` is plan-gated.
- There is no client-side key, so any OS user on a client machine can connect,
  limited only by server-side policy. Mitigate with check mode and `"always"`.
- Server side runs on Linux and the open-source macOS `tailscaled` variant, not
  Synology/QNAP or the macOS App Store/Standalone apps
  ([macOS variants](https://tailscale.com/docs/concepts/macos-variants)).
- `tailscale set --ssh` hangs existing SSH sessions to the node's Tailscale IP;
  restarting `tailscaled` (including upgrades) ends sessions.
- Editing the default `ssh` policy replaces it; removing the `ssh` section
  disables Tailscale SSH tailnet-wide. Removing a rule ends live sessions;
  `authorized_keys` access is separate and must be removed separately.
- `acceptEnv` (wildcards `*`, `?`) needs host >= 1.76.0. Do not forward secrets
  through it: before 1.102.1 names and values appeared on a child command line
  and in session logs (TS-2026-010); rotate any credentials sent this way.
- Run >= 1.98.10 on SSH hosts. Earlier releases let numeric-UID (`0@host`) and
  leading-dash usernames bypass `autogroup:nonroot` or reach root, and Unix-socket
  forwarding followed symlinks to privileged sockets such as `docker.sock`
  (TS-2026-004, -006, -009). The bulletins list 1.98.9 as the fix; the 1.98.10
  release completes the symlink and UID fixes
  ([bulletins](https://tailscale.com/security-bulletins),
  [changelog](https://tailscale.com/changelog)). Current clients reject UID,
  numeric-only, and leading-dash usernames.

### Session recording

`tsrecorder` (SSH and the Kubernetes Recorder) is deprecated: not offered to new
users, support for existing users ends August 2027. Tailscale points recording
to Tailscale PAM below. Do not propose new deployments
([tsrecorder](https://tailscale.com/docs/features/tsrecorder)). For existing
ones ([recording](https://tailscale.com/docs/features/tailscale-ssh/tailscale-ssh-session-recording)):

- `recorder: ["tag:x"]` on an `ssh` rule enables recording. `enforceRecorder:
  true` fails closed (refuses new sessions, ends active ones if no recorder is
  reachable); the default fails open. If rules disagree, the first in file order
  wins. A full recorder disk ends and refuses sessions.
- Recordings hold terminal output only; Kubernetes recordings omit stdin.

## Device Posture

([device posture](https://tailscale.com/docs/features/device-posture))

- `srcPosture` (grants, ACLs, `ssh`) is evaluated only on the SOURCE device and
  only for nodes in your own tailnet on clients >= 1.52.0
  ([troubleshooting](https://tailscale.com/docs/reference/troubleshooting/grants)).
  Shared-in nodes and devices behind subnet routers are not posture-checked; they
  pass on IP match. To enforce posture on outsiders, invite them. Tailscale SSH
  Console (browser) sessions are checked; allow `node:os == 'js'`.
- `postures` entries are `posture:<name>`: a list of assertions that must ALL
  match. A `srcPosture` list matches if ANY named posture matches.
  `defaultSrcPosture` applies only to rules without their own `srcPosture`; a
  rule that sets one replaces the default.
- A missing attribute makes a posture fail even with `!=` or `NOT IN`; test
  presence with `IS SET`/`NOT SET`. Operators: `==`, `!=`, `IN`, `NOT IN`,
  `IS SET`, `NOT SET`; `<`, `<=`, `>=`, `>` only for numbers and versions
  (`node:osVersion`, `node:tsVersion`).

```hujson
"postures": {
  "posture:managed": ["node:os IN ['macos','linux']", "node:tsVersion >= '1.40'"],
},
"defaultSrcPosture": ["posture:managed"],
```

- Built-in attributes: `node:os`, `node:osVersion`, `node:tsVersion`,
  `node:tsReleaseTrack`, `node:tsAutoUpdate` (true only for built-in
  auto-update), `node:tsStateEncrypted` (client 1.86+), `ip:country`,
  `ip:publicAddress` (beta), and `custom:<name>` set via the API. Integrations:
  CrowdStrike Falcon, SentinelOne, 1Password XAM (Kolide), Fleet, Huntress, Iru,
  Jamf Pro, Microsoft Intune. Custom and third-party attributes are plan-gated.
- Collection flag: the identity-collection page says `tailscale set
  --posture-checking=true`
  ([docs](https://tailscale.com/docs/features/access-control/device-management/how-to/manage-identity)),
  but `tailscale up|login|set` in 1.102.4 expose `--report-posture` only. Check
  `tailscale set --help` on the target version before scripting. MDM can opt in
  with the `PostureChecking` key (`always`).
- Custom attributes can carry an expiry for just-in-time access: POST
  `/api/v2/device/{deviceID}/attributes/custom:<key>` with `{"value": ...,
  "expiry": "<RFC3339 future time>", "comment": "..."}`. A key's value type is
  fixed tailnet-wide by the first value written
  ([JIT](https://tailscale.com/docs/features/tailscale-accessbot-jit)).
- An external EDR/MDM can authorize or deauthorize devices with POST
  `/api/v2/device/{id}/authorized`.
- Community lead (2026-07-22, open, no staff response): `tailscale exit-node
  suggest` and `--exit-node=auto:any` ignore `srcPosture` on `via` grants and may
  pick a forbidden exit node
  (https://github.com/tailscale/tailscale/issues/20569). Pick one explicitly.

## App Capabilities

([app capabilities](https://tailscale.com/docs/features/access-control/grants/grants-app-capabilities),
[placement](https://tailscale.com/docs/reference/node-attributes-vs-app-capabilities))

The `app` map has the same shape in `nodeAttrs` and `grants[].app`; choose by
placement:

- `nodeAttrs`: true of the device regardless of peer (Funnel,
  `tailscale.com/app-connectors`, `tailscale.com/visible-groups`, Taildrive
  `drive:share`/`drive:access`).
- `grants[].app`: a src-to-dst relationship (peer relay `tailscale.com/cap/relay`,
  Taildrive `tailscale.com/cap/drive`, Kubernetes, secrets, PAM).

Rules:

- Names are `<domain>/<path>`; `tailscale.com` and `tailscale.io` are reserved,
  so use a domain you control. Parameters are opaque JSON checked only for
  validity, so a typo silently grants nothing.
- dst cannot be `autogroup:internet`, `autogroup:shared`, `autogroup:danger-all`,
  or administrative autogroups. With `autogroup:self` as dst, src must be a user,
  group, or role autogroup.
- Read granted capabilities with `tailscale whois <ip>` (debugging) or LocalAPI/
  tsnet (code). `tailscale whoami` shows the local machine.
- Peer relay (`tailscale.com/cap/relay`): needs no network grant; grant shape and
  scoping are in [routing-connectors.md](routing-connectors.md#peer-relays).
- Taildrive (`tailscale drive`, alpha): nodeAttrs `drive:share` to share,
  `drive:access` to access, plus a `cap/drive` grant (`shares`, `access`
  `ro`|`rw`). The macOS CLI was removed in 1.90.1; use the GUI.

## Tailnet Lock

([Tailnet Lock](https://tailscale.com/docs/features/tailnet-lock),
[CLI](https://tailscale.com/docs/reference/tailscale-cli/lock))

Nodes must carry a signature from a trusted signing node. It has unrecoverable
failure modes; confirm who holds signing keys and disablement secrets before
recommending it.

- Init needs >= 2 signing nodes (max 20) and clients >= 1.46.1. The console
  command prints disablement secrets ONCE (`tailscale lock init
  --gen-disablements N`; `--gen-disablement-for-support` gives one to Tailscale
  support). One secret disables Lock; if all are lost and none went to support,
  the tailnet cannot be recovered. `tailscale lock local-disable` affects one node.
- Lock and device approval are mutually exclusive. Lock keys rotate at most once
  a year. An Android device cannot be a signing node.
- Always give `tailscaled` a state directory (`--state`/`--statedir`, or
  `TS_STATE_DIR` in containers). Before 1.90.8, nodes without one did not enforce
  signing (TS-2025-008); since then they enforce but re-fetch the authority on
  every start. `tailscale lock status` on a non-enforcing node says Lock is NOT
  enabled.
- Sign a node: `tailscale lock sign nodekey:<key> [tlpub:<key>]` on a signing
  node (the unsigned node's `tailscale lock status` prints it; console filter
  `property:locked-out`). For automation, create a pre-approved auth key, run
  `tailscale lock sign $AUTH_KEY`, and provision with the result. Re-auth
  rotates a signed node's signature, so key expiry needs no re-signing.
- `tailscale lock remove` re-signs nodes signed by the removed key unless
  `--re-sign=false`. Revoke a compromised key with `tailscale lock revoke-keys
  <tlpub...>`, then `--cosign` on other signing nodes (repeat with each new
  output until cosigns exceed revoked keys), then `--finish`.
- A node shared into a locked tailnet needs the accepting user's nodes signed
  there. Community lead (2023-12): a Kubernetes-operator node reportedly could
  not be shared out of a locked tailnet even with all nodes signed
  (https://github.com/tailscale/tailscale/issues/10633, closed as a duplicate of
  open https://github.com/tailscale/tailscale/issues/9103). A Tailscale
  contributor judged it a general shared-nodes plus Lock problem, not
  operator-specific. Test before rollout.
- For the GitHub Action with Lock, see
  [automation-api.md](automation-api.md#github-action-v4).

## Approval, Key Expiry, And Identity Lifecycle

- Device approval
  ([docs](https://tailscale.com/docs/features/access-control/device-management/device-approval)):
  new devices pass no traffic until an Owner, Admin, or IT admin approves;
  pre-approved auth keys exist only when it is on. Automate with a
  `nodeNeedsApproval` webhook, then POST `/api/v2/device/{id}/authorized`
  `{"authorized": true}`.
- User approval
  ([docs](https://tailscale.com/docs/features/access-control/user-approval)):
  on by default for tailnets created on or after 2025-05-22, off for older ones,
  and mutually exclusive with SCIM provisioning. If an invited user's devices
  cannot connect, look for "Needs approval" on the Users page.
- Key expiry
  ([docs](https://tailscale.com/docs/features/access-control/key-expiry)): node
  keys default to 180 days, configurable 1-180, applied only to devices that log
  in afterward. An expired key drops connections to and from the node. Expiry is
  disabled the first time a device authenticates with a tag and later tag
  changes do not alter it, so untagged (user-owned) routers and servers still
  expire unless expiry is disabled (all plans, console or update-device-key
  API). Renew with `tailscale up --force-reauth`, never over a tailnet-only
  SSH/RDP session; an admin's "Temporarily extend key" (Machines page, expired
  keys only) gives 30 minutes. Renewal has been seamless since 1.90.1: existing
  connections survive re-authentication. Console browser sessions expire
  separately (30 days). Auth-key expiry is a different mechanism
  ([automation-api.md](automation-api.md#auth-keys)).
- Auth keys and API tokens belong to the user who created them. Deleting the user
  permanently revokes them and deletes their devices; suspending suspends them;
  they cannot be reassigned. Fleets enrolled with an engineer's personal key, or
  scripts using their token, break on offboarding. Use tailnet-owned trust
  credentials (OAuth client or federated identity) and tagged devices, and audit
  long-lived keys made by departing users
  ([docs](https://tailscale.com/docs/features/sharing/how-to/remove-team-members)).
- SCIM offboarding differs by IdP
  ([docs](https://tailscale.com/docs/features/user-group-provisioning)): Okta
  suspends in Tailscale only on deactivate; Entra soft delete suspends; Google
  suspend or delete both suspend. A user suspended only in the IdP stays
  authenticated until node keys expire, so also suspend or delete them in
  Tailscale or remove their devices. Synced groups cannot assign roles.
- Roles ([docs](https://tailscale.com/docs/reference/user-roles)): IT admin
  can read but not write policy, cannot accept subnet routes, and can grant any
  role, including Admin. Network admin writes policy and credentials but not machines
  or users.
- Secret prefixes: `tskey-api`, `tskey-auth`, `tskey-client`, `tskey-scim`,
  `tskey-webhook`. GitHub secret scanning has Tailscale auto-revoke live matches
  and email the security contact, so a key committed publicly can silently break
  CI or enrolment. Revoking an auth key does not remove nodes it enrolled
  ([docs](https://tailscale.com/docs/integrations/secret-scanning)).

## Node Sharing

([sharing](https://tailscale.com/docs/features/sharing),
[invite vs share](https://tailscale.com/docs/reference/inviting-vs-sharing))

- Shared nodes are quarantined: they answer the recipient but cannot initiate
  connections unless a node is shared back. The recipient uses the full name
  `<host>.<sharer-tailnet>.ts.net` or the IP. Tags, groups, and subnet routes are
  stripped. Only Owner/Admin/IT admin can share or accept.
- Unused invite links expire after 30 days. Write outsider rules with the
  recipient's email or `autogroup:shared`, never `*`. Sharing an exit node needs
  "Allow use as an exit node" at share time plus advertise and approve.
- Invite (seat, roles, subnet routers, Taildrop, per-user policy) when access is
  broad or changing; share a device for a small fixed set. Both tailnets'
  policies must allow the connection.
- Declarative sharing is alpha and waitlisted
  ([docs](https://tailscale.com/docs/features/declarative-node-sharing)): both
  policies declare `externalTailnets.<alias>`; grants use `group://<alias>/<group>`
  or `tag://<alias>/<tag>`; grants naming groups absent from the receiver's
  `allowExternalReferencesTo` are silently ignored.

## Tailscale PAM (Beta)

Beta, waitlisted; do not present it as GA. Brokers identity-aware access, with
session recording where applicable, to SSH, databases, Kubernetes, RDP, VNC,
HTTP(S), S3, and TCP ports through connectors in your infrastructure
([get started](https://tailscale.com/docs/privileged-access-management/get-started)).
Just-in-time requests are approved in Slack
([launch post](https://tailscale.com/blog/tailscale-pam-beta)).

- Enabling it in the admin console auto-creates `tag:border0-managed`, an
  `autoApprovers` rule, an initial `autogroup:admin` grant, and an OIDC trust
  credential. Do not remove them.
- Access is a `tailscale.com/cap/pam` grant on a `svc:` service
  ([control access](https://tailscale.com/docs/privileged-access-management/how-to/control-access)):

```hujson
{"src": ["group:platform"], "dst": ["svc:production-database"], "ip": ["*"],
 "app": {"tailscale.com/cap/pam": [{"version": "v1", "permissions": {
   "database": {"allowed_databases": [
     {"database": "*", "allowed_query_types": ["ReadOnly"]}]}}}]}}
```

- Permission keys: `database`, `ssh`, `kubernetes`, `aws_s3`, `http`, `rdp`,
  `vnc`, `tcp`. Editing PAM grants needs Owner, Admin, or Network admin.

## GitOps

Policy-as-code (the GitOps action, `gitops-pusher`, Terraform), its credentials
and scopes, and console-edit locking are in
[automation-api.md](automation-api.md#gitops).

## Hardening

([best practices](https://tailscale.com/docs/reference/best-practices/security))

- MFA at the IdP; groups and tags in rules; `tests` on every change; check mode
  for high-risk SSH; device approval; short key expiry; device posture; delete
  unused OAuth clients, API keys, and auth keys; suspend users on offboarding;
  review configuration audit logs and network flow logs.
- Validate the `Host` header on HTTP-only tailnet services to prevent DNS
  rebinding.
- Reusable auth keys in CI are the weak point: in a 2026 intrusion an agent
  copied one and enrolled 181 tagged nodes with no Tailscale vulnerability
  involved ([post-mortem](https://tailscale.com/blog/hugging-face-intrusion)).
  Prefer workload identity federation; otherwise one-off keys, short expiry,
  narrow tags, and an audit of what each tag can reach. With flow logs enabled,
  both ends of a connection report it, so a node using `--no-logs-no-support`
  still shows in its peers' logs.
