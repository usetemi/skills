# Tailscale Kubernetes

Docs: https://tailscale.com/docs/kubernetes-operator/ (append `.md`). CRDs
(Connector, DNSConfig, PeerRelay, ProxyClass, ProxyGroupPolicy, ProxyGroup,
Recorder, Tailnet) change between releases: run `kubectl explain <kind>.spec`
before writing manifests, not from memory.

## Decision Path

- tailnet to cluster: L7 `Ingress` (HTTPS) or L3 `Service` (TCP/UDP)
- cluster to tailnet: egress `ExternalName` Service
- subnet router, exit node, app connector: `Connector`
- kubectl over the tailnet: API server proxy; session recording: `Recorder`
- one tailnet identity per pod, no operator: sidecar (last section)
- Prefer a `ProxyGroup` for HA or many services.

## Install And Prerequisites

```bash
helm repo add tailscale https://pkgs.tailscale.com/helmcharts
helm upgrade --install tailscale-operator tailscale/tailscale-operator \
  --namespace=tailscale --create-namespace --wait \
  --set-string oauth.clientId=<id> --set-string oauth.clientSecret=<secret>
```

- Multiple default tags: `--set 'proxyConfig.defaultTags=tag:a\,tag:b'` or
  `--set-json` with an array.
- Do not set `nameOverride` or `fullnameOverride` on an existing install: the
  operator re-registers as a new device and `helm upgrade` fails.
- Kubernetes v1.23.0+. The operator supports proxies up to four minor versions
  older than itself, not newer; run the same version for both. Upgrade the
  operator incrementally, not across many minors (community-tier:
  https://github.com/tailscale/tailscale/issues/20916).

### OAuth client and tags

- OAuth client: write scope on General/Services, Devices/Core, and Keys/Auth
  Keys, each restricted to `tag:k8s-operator` (the troubleshooting page lists
  only two; follow the install page). After replacing a client, reinstall.
- The operator tag must own every other tag it applies (`tailscale.com/tags`,
  `proxyConfig.defaultTags`, `spec.tags` on Connector, ProxyGroup, Recorder).
  Declare each in `tagOwners` explicitly, no patterns:
  `"tag:k8s-operator": [], "tag:k8s": ["tag:k8s-operator"]`.
- Tags apply only at first provisioning. Changing `tailscale.com/tags` or
  `tailscale.com/hostname` on an exposed Service needs the Service recreated;
  Connector and ProxyGroup `spec.tags` are immutable.
- Workload identity federation (beta, 1.92.3+): federated identity with the
  cluster issuer, subject `system:serviceaccount:tailscale:operator`, the same
  scopes, and Helm `--set-string oauth.audience=<aud>` instead of
  `oauth.clientSecret`. Setup needs `kubectl create clusterrolebinding
  oidc-discovery --clusterrole=system:service-account-issuer-discovery
  --group=system:unauthenticated`.

### Platform limits

- Since v1.78 both proxy containers run privileged. EKS Fargate supports only
  Ingress (L7) and the API server proxy; GKE Autopilot and other platforms
  restricting privileged pods are not officially supported.
- Cilium in kube-proxy replacement mode bypasses the proxy pod's netfilter
  rules: enable "bypass socket load balancer in Pods' namespaces" for
  `loadBalancerClass: tailscale`, `tailscale.com/expose`, or a Service CIDR
  through a Connector.

## Ingress (tailnet to cluster)

| Layer | Resource | Notes |
|---|---|---|
| L7 | `Ingress`, `ingressClassName: tailscale` | Serve, HTTPS only, needs MagicDNS and HTTPS on the tailnet |
| L3 | `Service` with `tailscale.com/expose: "true"`, or `loadBalancerClass: tailscale` | TCP/UDP via DNAT to the ClusterIP |

- L7 hostname is the first `spec.tls.hosts` entry. Only `pathType: Prefix`.
  `tailscale.com/http-redirect` adds HTTP-to-HTTPS (1.92.3+). L7 runs tailscaled
  in userspace mode, so throughput can trail L3 (community-tier:
  https://github.com/tailscale/tailscale/issues/12393).
- Public exposure is per-Ingress `tailscale.com/funnel: "true"` and needs the
  `funnel` nodeAttr on the proxy tag; `autogroup:member` excludes tagged
  devices ([expose-services.md](expose-services.md#funnel-public)).
- Cloud service (for example RDS): `ExternalName` Service with
  `tailscale.com/expose: "true"` and the DNS name in `spec.externalName`;
  nftables mode uses only the first resolved IP. Use a Connector for CIDRs or
  names that do not resolve.

### Certificates

- L7 certs are Let's Encrypt certs for the MagicDNS name, issued on the first
  client connection, so the first request can be slow or time out. Limits: 50
  certs per week for unique hostnames per tailnet, 5 duplicates per week;
  ephemeral previews should reuse hostnames. ProxyClass
  `useLetsEncryptStagingEnvironment: true` tests without spending limits
  (Ingress only).
- Certs renew only while there is traffic. Use 1.102.2+ to avoid renewal
  backoff rate limits.

## Egress (cluster to tailnet)

Service with `type: ExternalName`, `externalName: placeholder` (overwritten by
the operator), and exactly one of `tailscale.com/tailnet-fqdn` (preferred;
follows IP changes) or `tailscale.com/tailnet-ip` (single IP). The egress
overview's `tailnet-target-ip` is a docs error.

- Pods cannot reach tailnet devices by raw 100.x or ULA address. Grant the proxy
  tag the destinations and ports.
- HA: add `tailscale.com/proxy-group: <egress ProxyGroup>`. `spec.ports` is
  then required (port, protocol, name); many Services share one ProxyGroup and
  traffic round-robins. Wait for condition `TailscaleEgressSvcReady`. Graceful
  drain fails if the ProxyClass sets a custom `TS_LOCAL_ADDR_PORT`.
- Behind a subnet router or 4via6: attach a ProxyClass with
  `spec.tailscale.acceptRoutes: true` to the egress ProxyGroup, then use
  `tailnet-ip` (or a `10-1-0-5-via-7.<tailnet>.ts.net` FQDN); generate the
  address with `tailscale debug via <siteID> <IPv4>` (needs cluster IPv6;
  egress ProxyGroups support IPv6 from 1.102.2).

### MagicDNS from pods (DNSConfig)

Pods do not resolve `*.ts.net` by default. `DNSConfig` is a cluster-scoped
singleton nameserver answering only for this cluster's egress and Ingress
proxies, not arbitrary tailnet devices. Add a CoreDNS stub domain
(`ts.net:53 { errors; cache 30; forward . <ip> }`) with the IP from
`kubectl get dnsconfig ts-dns -o jsonpath='{.status.nameserver.ip}'`.

## ProxyGroup, HA, And Tailscale Services

- `spec.type`: `ingress`, `egress`, or `kube-apiserver` (immutable).
  `spec.replicas` defaults to 2. `spec.tags` defaults to `tag:k8s` and is
  fixed once devices exist. The referenced ProxyClass must be Ready first.
- HA ingress: annotate the Ingress or LoadBalancer Service with
  `tailscale.com/proxy-group: <name>`. The operator creates a Tailscale
  Service per exposed resource; the IP and DNS name belong to that Service,
  not the proxy devices. `tailscale.com/proxy-group` cannot be added to an
  existing standalone L3 Service; create a new one.
- Grants target the Tailscale Service tag (from `tailscale.com/tags`), not the
  ProxyGroup device tag. Auto-approval maps the service tag to the device tag:
  `"autoApprovers": {"services": {"tag:monitoring": ["tag:eu-cluster"]}}`.
  Advertisement, approval, and grants are separate steps.
- Multi-cluster ingress: apply the same Ingress (same `tls` host and
  proxy-group annotation) in each cluster, with a unique `spec.hostnamePrefix`
  per ProxyGroup; clients must accept routes. Without regional routing all
  clients use one backend.
- `ProxyGroupPolicy` (1.96+) restricts which ProxyGroups a namespace may name;
  no policy means allow-all, empty lists deny all, and existing resources are
  not re-evaluated until modified.

## ProxyClass

- Cluster-scoped. Attach with annotation `tailscale.com/proxy-class: <name>`
  on an Ingress or Service, or `spec.proxyClass` on Connector, ProxyGroup, or
  PeerRelay. Cluster default: Helm `proxyConfig.defaultProxyClass` or env
  `PROXY_DEFAULT_CLASS` (not applied to Connectors).
- Static endpoints (`staticEndpoints.nodePort`, 1.86+, ProxyGroup only): one
  NodePort Service per replica so clients connect directly, not via DERP. Max
  two per ProxyGroup; Nodes need an ExternalIP and inbound UDP open. Verify
  with `tailscale ping` on a test Service's EXTERNAL-IP: `via <ip>:<port>` is
  direct, `via DERP(...)` means firewall or selector problems.

## Connector

- `spec.appConnector` is mutually exclusive with `subnetRouter` and `exitNode`;
  those two can combine. `advertiseRoutes` accepts 4via6 CIDRs.
- `spec.replicas` (default 1, 1.88.2+) gives HA. `spec.hostname` only with an
  unset or single replica count, else `spec.hostnamePrefix`.
- Routes still need approval (or `autoApprovers`) and client `--accept-routes`
  on Linux; see [routing-connectors.md](routing-connectors.md#route-injection).

## API Server Proxy

- Modes: `auth` (default; impersonates the caller), `noauth` (forwards as is).
- Shapes: in-process in the operator (Helm `apiServerProxyConfig.mode`
  `"true"` or `"noauth"`), or a dedicated HA `ProxyGroup` (`spec.type:
  kube-apiserver`, `kubeAPIServer.mode`; preferred). Auth mode on a
  ProxyGroup needs `apiServerProxyConfig.allowImpersonation="true"`, grants on
  `tcp:80` and `tcp:443`, and `autoApprovers.services` for its tag.
- Client: `tailscale configure kubeconfig <hostname-or-fqdn>` (ALPHA).
- Auth-mode identity: untagged devices impersonate as their login name; tagged
  devices as their node FQDN with each tag as a Kubernetes group. A grant with
  app capability `tailscale.com/cap/kubernetes`, `dst` the proxy's tag, and
  `{"impersonate":{"groups":["<name>"]}}` replaces the tag-derived groups.
  Tailnet reachability grants no Kubernetes permissions; bind groups with RBAC.
- noauth does not forward client certificates, so cert-authenticated
  distributions (for example k3s) need auth mode. In noauth mode set the
  kubeconfig `server` to `https://<proxy>.<tailnet>.ts.net:443` and delete
  `certificate-authority-data`; the first request can time out on cert issuance.

## Recorder

`tsrecorder` is deprecated and not offered to new users; see
[policy-security.md](policy-security.md#session-recording). Existing
deployments: `Recorder` needs the API server proxy; storage defaults to an
ephemeral volume (use `spec.storage.s3`; `replicas` above 1 requires S3,
1.92.3+); enable it with grants carrying `tailscale.com/cap/kubernetes` and
`recorder: ["tag:tsrecorder"]`; `enforceRecorder: true` blocks sessions when
the recorder is unreachable. Treat recordings as sensitive audit material.

## Multi-Tailnet And Peer Relay

- Multi-tailnet (1.96+): a cluster-scoped `Tailnet` CRD references a Secret
  with OAuth `client_id` and `client_secret`, or WIF `client_id` and
  `audience` (1.102.2+). ProxyGroup, Connector, and Recorder select it with
  immutable `spec.tailnet`. Each tailnet needs `tagOwners` for the operator
  tag. The docs example's `tailscale.com/v1alpha` is a typo: use `v1alpha1`.
- `PeerRelay` (operator 1.102.2+, `v1alpha1`): each replica sits behind its own
  LoadBalancer Service. The operator writes the static endpoint; do not run
  `tailscale set --relay-server-static-endpoints` in the pods. Clients need a
  grant with app capability `tailscale.com/cap/relay` to the relay's tag. On
  AWS use 1.102.3+ (HTTP health checks; relays listen on UDP only).

## Troubleshooting

- Proxies are StatefulSets in namespace `tailscale`; find pods and Secrets by
  labels `tailscale.com/parent-resource`, `-ns`, and `-type` (`ingress`, `svc`,
  `connector`, `proxygroup`).
- Backend unreachable from the proxy pod: check NetworkPolicy. TLS errors, in
  order: HTTPS not enabled, certificate provisioning, Let's Encrypt limits.
- Stuck on DERP: CNI or cloud SNAT with port randomization (AWS VPC CNI by
  default; Azure default mode) and hard NAT prevent direct paths. Use
  ProxyGroup static endpoints, or a manual pod with `hostNetwork: true`, fixed
  UDP `PORT`, and inbound UDP allowed (https://tailscale.com/blog/kubernetes-direct-connections).

## Sidecar Without The Operator

https://tailscale.com/docs/solutions/connect-kubernetes-pods-to-tailnet-using-sidecar

- Persist state. Never use `--state=mem:` in production: each restart registers
  a new device, and under load the flood can cause sustained outages that do
  not self-heal.
- Use a StatefulSet with `TS_KUBE_SECRET=$(POD_NAME)` (a Deployment has
  unstable pod names and orphans Secrets). RBAC: a Role on `secrets` with
  `get, create, update, patch`. Alternative: `TS_KUBE_SECRET=""` with
  `TS_STATE_DIR` on a PVC (durable) or emptyDir (survives a container crash,
  not a pod restart).
- Auth: an OAuth client secret registers ephemeral nodes by default
  ([automation-api.md](automation-api.md#ephemeral-defaults-for-oauth-and-wif-registration)).
  For stable identity use `TS_CLIENT_ID` and
  `TS_CLIENT_SECRET='tskey-client-...?ephemeral=false&preauthorized=true'`
  (keep quoted), a tagged `TS_AUTHKEY`, or WIF via `TS_CLIENT_ID` +
  `TS_AUDIENCE`. Tag with `TS_EXTRA_ARGS=--advertise-tags=tag:k8s`.
  `--shields-up` blocks all inbound tailnet connections regardless of policy.
- DNS: `TS_ACCEPT_DNS=true` rewrites `/etc/resolv.conf` to `100.100.100.100`
  for every container in the pod. DNS fails until the sidecar connects (use a
  native sidecar container), and in-cluster names stop resolving unless split
  DNS for `svc.cluster.local` points at the CoreDNS ClusterIP.
- `--accept-routes` has no overlap detection and installs every advertised
  route into routing table 52: a tailnet route covering the pod or service CIDR
  hairpins in-cluster traffic into the tun device. Compare peer `PrimaryRoutes`
  in `tailscale status --json` with the cluster's service and pod CIDRs first.
  Kernel-mode sidecars that accept routes, advertise routes, or proxy need a
  privileged initContainer setting `net.ipv4.ip_forward` and
  `net.ipv6.conf.all.forwarding`.
- Do not use `/healthz` (`TS_ENABLE_HEALTH_CHECK=true`) or a MagicDNS lookup
  as a livenessProbe: `/healthz` returns 503 when the node briefly has no
  tailnet IP, so restarts force re-registration and amplify outages.
