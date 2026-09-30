# Tailscale Policy And Security

A grant never approves or advertises a route; the route gates are in
[routing-connectors.md](routing-connectors.md#route-injection). Funnel is gated
by `nodeAttrs` ([expose-services.md](expose-services.md#funnel-public)).

## Grants vs ACLs

Grants get all new features. ACLs stay supported and can coexist with grants in
one file, so do not rewrite an ACL-only policy just to modernize it. `via` and
`app` exist only in grants
([grants vs ACLs](https://tailscale.com/docs/reference/grants-vs-acls)). The file
is HuJSON; `autogroup:members` aliases `autogroup:member` (not both in one file).

- Deny by default; no `action` field. Each grant needs `src`, `dst`, and `ip`
  and/or `app`.
- Matching grants UNION. A more specific grant never narrows a broader one; to
  narrow access, remove the broader grant.
- An `app` capability applies only if src also has network access to dst
  (exception: peer relay `tailscale.com/cap/relay`).
- `ip`: `*` (all ports), `<port>` or `<lo>-<hi>` (both TCP/UDP/ICMP), `<proto>:*`
  for portless protocols (`icmp:*`), `<proto>:<port|range>` (`tcp:443`). Only
  TCP, UDP, and SCTP have ports.
- `*` as src includes devices, approved subnets, and `autogroup:shared`.
  `autogroup:self` covers only user-owned devices and cannot combine with
  `autogroup:tagged`. `autogroup:member` includes invited users, not users of
  shared devices.
- `user:*@domain` and `localpart:*@domain` take no partial wildcards or shared
  domains such as gmail.com.
- Exit nodes need `dst: autogroup:internet`, not the exit-node device
  ([routing-connectors.md](routing-connectors.md#exit-nodes)).
- `via` ([docs](https://tailscale.com/docs/features/access-control/grants/grants-via)):
  values must be tags of routers the source can already reach. Omitting it
  allows any exit node, subnet router, or app connector, so a broader grant
  without `via` still allows the paths a narrower `via` grant meant to pin.
- `ipsets`: `ipset:<name>` lists of `add`/`remove <target>` processed in order
  (no tags). Subtract private ranges from `autogroup:internet` to limit exit-node
  reach ([IP sets](https://tailscale.com/docs/features/tailnet-policy-file/ip-sets)).

### Migrating ACLs to grants

([docs](https://tailscale.com/docs/reference/migrate-acls-grants)) Drop
`action`; port/`proto` move into `ip`; `srcPosture` copies; `ssh` is not
migrated. Split an ACL `dst` mixing ports across targets
(`["tag:web:80","tag:dev:22"]`) into one grant per target; a merged grant
silently widens access. The console's "Convert to grants" rewrites `acls` with
no confirmation; review the diff first.

## Validation

- Undefined groups/tags are rejected on save; an empty one passes and matches
  nothing. A failing `tests`/`sshTests` entry rejects the policy
  ([troubleshooting](https://tailscale.com/docs/reference/troubleshooting/grants)).
- `tests`: `src` (no wildcards), `accept`/`deny` as `host:port` with one numeric
  port, optional `proto` (ICMP: `"proto":"icmp"`, port 0), `srcPostureAttrs`.
  Destinations: IP, host, user, group, tag, `svc:` name; never CIDRs. They do
  not cover app capabilities.
- `sshTests`: `src`, `dst`, `accept`/`check`/`deny` username lists.

## Tags

- A device is user-owned OR tagged: applying a tag removes the user identity,
  and authenticating as a user strips tags ([tags](https://tailscale.com/docs/features/tags)).
  Tags are not ANDed in rules; use a composite tag such as `tag:prod-database`.
  Tagged devices cannot SSH to user-owned devices.
- `tagOwners: []` means only Owners, Admins, and Network admins, who may apply
  any tag (IT admin may not).
- A credential (OAuth client or auth key) may request only its full tag set, or
  tags that one of its tags owns. Ownership is one hop: if `tag:a` owns `tag:b`
  and `tag:b` owns `tag:c`, `tag:a` cannot apply `tag:c`. A subset needs
  explicit ownership (make the tag its own owner).
- `--advertise-tags` cannot remove tags from an auth-key device; issue a new key.

## Tailscale SSH

Needs a grant/ACL letting src reach dst on port 22 plus an `ssh` rule
([docs](https://tailscale.com/docs/features/tailscale-ssh)).

- Fields: `action` (`accept`|`check`), `src` (not `*`), `dst`, `users`, optional
  `checkPeriod`, `acceptEnv`, `srcPosture`, `recorder`/`enforceRecorder`.
- `dst`: a tag, `autogroup:self` (when src is only users/groups), or the single
  named user matching src; not `*`, IPs, hostnames, or ports. Users in `users`
  must already exist on the host.
- Privilege trap: changing `dst` from `autogroup:self` to a tag while keeping
  `users: ["autogroup:nonroot"]` lets every permitted src SSH as ANY nonroot
  account on the tagged host. List explicit usernames for tag destinations.
- If check and accept rules both match, the check rule applies and only its
  `users` apply. A tagged src cannot use check mode.
- `checkPeriod`: 1 minute to 168h, default 12h, or `"always"` (breaks tools that
  open many connections, such as Ansible). A default-period check covers all
  check-mode destinations; a custom period covers that destination only.
- No client-side key: any OS user on a client machine can connect, limited only
  by server-side policy; mitigate with check mode and `"always"`.
- Server side: Linux and the open-source macOS `tailscaled` variant only, not
  Synology/QNAP or the macOS App Store/Standalone apps. `tailscale set --ssh`
  hangs existing SSH sessions to the node's Tailscale IP; restarting `tailscaled`
  ends sessions.
- Removing the `ssh` section disables Tailscale SSH tailnet-wide; removing a
  rule ends live sessions. `authorized_keys` access is separate.
- `acceptEnv` (wildcards `*`, `?`) needs host >= 1.76.0. Do not forward secrets
  through it: before 1.102.1 names and values appeared on a child command line
  and in session logs (TS-2026-010); rotate any credentials sent this way.
- Run >= 1.98.10 on SSH hosts. Earlier releases let numeric-UID (`0@host`) and
  leading-dash usernames bypass `autogroup:nonroot` or reach root, and Unix-socket
  forwarding followed symlinks to sockets such as `docker.sock` (TS-2026-004,
  -006, -009) ([bulletins](https://tailscale.com/security-bulletins)).

### Session recording

`tsrecorder` (SSH and the Kubernetes Recorder) is deprecated: not offered to new
users, support ends August 2027. Recording moves to Tailscale PAM below; do not
propose new deployments ([tsrecorder](https://tailscale.com/docs/features/tsrecorder)).
Existing: `recorder: ["tag:x"]` on an `ssh` rule enables recording;
`enforceRecorder: true` fails closed (refuses new sessions, ends active ones if
no recorder is reachable), the default fails open; if rules disagree, the first
in file order wins. A full recorder disk ends and refuses sessions. Recordings
hold terminal output only.

## Device Posture

- `srcPosture` (grants, ACLs, `ssh`) is evaluated only on the SOURCE device, and
  only for nodes in your own tailnet on clients >= 1.52.0. Shared-in nodes and
  devices behind subnet routers are not checked; they pass on IP match. Invite
  outsiders to enforce posture. Tailscale SSH Console (browser) sessions are
  checked; allow `node:os == 'js'`.
- `postures` entries are `"posture:<name>": ["node:os IN ['macos','linux']",
  "node:tsVersion >= '1.40'"]`; assertions must ALL match, while a `srcPosture`
  list matches if ANY named posture matches. `defaultSrcPosture` applies only to
  rules without their own `srcPosture`.
- A missing attribute makes a posture fail even with `!=` or `NOT IN`; test
  presence with `IS SET`/`NOT SET`. Operators: `==`, `!=`, `IN`, `NOT IN`,
  `IS SET`, `NOT SET`; `<`, `<=`, `>=`, `>` only for numbers and versions.

- Attributes: `node:os`, `node:osVersion`, `node:tsVersion`, `node:tsAutoUpdate`
  (true only for built-in auto-update), `node:tsStateEncrypted` (client 1.86+),
  API-set `custom:<name>`. Custom and third-party attributes are plan-gated.
- Collection flag: docs say `tailscale set --posture-checking=true`, but 1.102.4
  exposes `--report-posture` only; check `tailscale set --help` before
  scripting. MDM can opt in with the `PostureChecking` key (`always`).

## App Capabilities

The `app` map has the same shape in `nodeAttrs` and `grants[].app`
([placement](https://tailscale.com/docs/reference/node-attributes-vs-app-capabilities)).
`nodeAttrs`: true of the device regardless of peer (Funnel,
`tailscale.com/app-connectors`, Taildrive `drive:share`/`drive:access`).
`grants[].app`: a src-to-dst relationship (peer relay `tailscale.com/cap/relay`,
Taildrive `tailscale.com/cap/drive`, Kubernetes, secrets, PAM).

- Names are `<domain>/<path>`; `tailscale.com`/`tailscale.io` are reserved.
  Parameters are opaque JSON checked only for validity, so a typo silently
  grants nothing.
- dst cannot be `autogroup:internet`, `autogroup:shared`, `autogroup:danger-all`,
  or administrative autogroups. With `autogroup:self` as dst, src must be a user,
  group, or role autogroup.
- Read granted capabilities with `tailscale whois <ip>`.

## Tailnet Lock

Nodes must carry a signature from a trusted signing node
([docs](https://tailscale.com/docs/features/tailnet-lock)). It has unrecoverable
failure modes; confirm who holds signing keys and disablement secrets first.

- Init needs >= 2 signing nodes (max 20) and clients >= 1.46.1. The console
  command prints disablement secrets ONCE (`tailscale lock init
  --gen-disablements N`; `--gen-disablement-for-support` gives one to Tailscale
  support). One secret disables Lock; if all are lost and none went to support,
  the tailnet cannot be recovered. `tailscale lock local-disable` affects one node.
- Lock and device approval are mutually exclusive. Android cannot sign.
- Give `tailscaled` a state directory (`--state`/`--statedir`, or `TS_STATE_DIR`
  in containers). Before 1.90.8, nodes without one did not enforce signing
  (TS-2025-008); since then they enforce but re-fetch the authority on every
  start. `tailscale lock status` on a non-enforcing node says Lock is NOT enabled.
- Sign a node: `tailscale lock sign nodekey:<key> [tlpub:<key>]` on a signing
  node (the unsigned node's `tailscale lock status` prints it). For automation,
  run `tailscale lock sign $AUTH_KEY` on a pre-approved auth key. Re-auth rotates
  the signature, so key expiry needs no re-signing.
- `tailscale lock remove` re-signs nodes signed by the removed key unless
  `--re-sign=false`. Revoke a compromised key with `tailscale lock revoke-keys
  <tlpub...>`, then `--cosign` on other signing nodes (repeat with each new
  output until cosigns exceed revoked keys), then `--finish`.
- GitHub Action with Lock: [automation-api.md](automation-api.md#github-action-v4).

## Approval, Key Expiry, And Identity Lifecycle

- Device approval: new devices pass no traffic until an Owner, Admin, or IT
  admin approves; pre-approved auth keys exist only when it is on. Automate
  with a `nodeNeedsApproval` webhook, then POST `/api/v2/device/{id}/authorized`
  `{"authorized": true}`.
- User approval: on by default for tailnets created on or after 2025-05-22, off
  for older ones, and mutually exclusive with SCIM. Invited users who cannot
  connect: look for "Needs approval" on the Users page.
- Key expiry
  ([docs](https://tailscale.com/docs/features/access-control/key-expiry)): node
  keys default to 180 days, configurable 1-180, applied only to devices that log
  in afterward. An expired key drops connections to and from the node. Expiry is
  disabled the first time a device authenticates with a tag and later tag
  changes do not alter it, so untagged (user-owned) routers and servers still
  expire unless expiry is disabled (console or update-device-key API). Renew
  with `tailscale up --force-reauth`, never over a tailnet-only SSH/RDP session;
  since 1.90.1 existing connections survive re-authentication. Auth-key expiry is
  a different mechanism ([automation-api.md](automation-api.md#auth-keys)).
- Auth keys and API tokens belong to their creator. Deleting the user revokes
  them and deletes their devices; they cannot be reassigned, so fleets enrolled
  with a personal key break on offboarding. Use tailnet-owned credentials (OAuth
  client or federated identity) and tags.
- SCIM offboarding ([docs](https://tailscale.com/docs/features/user-group-provisioning)):
  Okta suspends in Tailscale only on deactivate; Entra soft delete suspends;
  Google suspend or delete both suspend. A user suspended only in the IdP stays
  authenticated until node keys expire, so also suspend or delete them in
  Tailscale or remove their devices.
- IT admin can read but not write policy and can grant any role, including Admin.
- GitHub secret scanning makes Tailscale auto-revoke publicly committed
  `tskey-{api,auth,client,scim,webhook}` keys, silently breaking CI or
  enrolment; revoking an auth key does not remove the nodes it enrolled.

## Node Sharing

- Shared nodes ([docs](https://tailscale.com/docs/features/sharing)) are
  quarantined: they answer the recipient but cannot initiate connections unless
  a node is shared back. The recipient uses
  `<host>.<sharer-tailnet>.ts.net` or the IP. Tags, groups, and subnet routes are
  stripped. Both tailnets' policies must allow the connection.
- Write outsider rules with the recipient's email or `autogroup:shared`, never
  `*`. Sharing an exit node needs "Allow use as an exit node" at share time
  plus advertise and approve.

## Tailscale PAM (Beta)

Beta, waitlisted; do not present it as GA. Brokers identity-aware access to SSH,
databases, Kubernetes, RDP, and more through connectors you run
([get started](https://tailscale.com/docs/privileged-access-management/get-started)).
Enabling it auto-creates `tag:border0-managed`, an `autoApprovers` rule, an
`autogroup:admin` grant, and an OIDC trust credential; do not remove them.
Access is a `tailscale.com/cap/pam` grant on a `svc:` service
([control access](https://tailscale.com/docs/privileged-access-management/how-to/control-access)).
Permission keys: `database`, `ssh`, `kubernetes`, `aws_s3`, `http`, `rdp`, `vnc`,
`tcp`. Editing PAM grants needs Owner, Admin, or Network admin.

## Hardening

- Reusable CI auth keys are the weak point: in a 2026 intrusion an agent copied
  one and enrolled 181 tagged nodes ([post-mortem](https://tailscale.com/blog/hugging-face-intrusion)).
  Prefer workload identity federation; else one-off keys, short expiry, narrow tags.
- `tailscale set --webclient` serves the device web interface on
  `<tailscale-ip>:5252` to anyone whose policy allows that port. Restrict with a
  grant on 5252, or disable everywhere with `nodeAttrs`
  `{"target":["autogroup:member"],"attr":["disable-web-client"]}`.
- Validate the `Host` header on HTTP-only tailnet services (DNS rebinding).
  Policy-as-code: [automation-api.md](automation-api.md#gitops).
