# Tailscale Kubernetes

Operator docs live under https://tailscale.com/docs/kubernetes-operator/
(quickstart, install-operator, concepts/, ingress/, egress/, connector/,
api-server-access/, recorder/, manage-and-configure/, reference/). Fetch a
page as Markdown by appending `.md`.

The operator ships CRDs that change between releases (Connector, DNSConfig,
PeerRelay, ProxyClass, ProxyGroupPolicy, ProxyGroup, Recorder, Tailnet). Run
`kubectl explain <kind>.spec` against the installed CRDs before writing
manifests; do not write fields from memory.

## Decision Path

1. Pick the pattern:
   - tailnet to cluster: L7 `Ingress` (HTTPS) or L3 `Service` (TCP/UDP)
   - cluster to tailnet: egress `ExternalName` Service
   - cluster subnet router, exit node, or app connector: `Connector`
   - kubectl over the tailnet: API server proxy
   - kubectl session recording: `Recorder` (needs the API server proxy)
   - one tailnet identity per pod, no operator: sidecar (last section)
2. Prefer a `ProxyGroup` over per-resource proxies when you need HA or many
   exposed services.
3. Keep tailnet policy (who can reach a device) and Kubernetes RBAC (what the
   operator or a caller may do in the cluster) separate in designs.
4. Read-only checks first:

   ```bash
   kubectl get pods -n tailscale
   kubectl get crd | rg tailscale
   kubectl get proxygroup,proxyclass,connector,recorder,dnsconfig -A
   kubectl logs deployment/operator --namespace tailscale
   ```

## Install And Prerequisites

Install page: https://tailscale.com/docs/kubernetes-operator/install-operator

```bash
helm repo add tailscale https://pkgs.tailscale.com/helmcharts
helm repo update
helm upgrade --install tailscale-operator tailscale/tailscale-operator \
  --namespace=tailscale --create-namespace \
  --set-string oauth.clientId=<id> --set-string oauth.clientSecret=<secret> \
  --wait
```

- Default install creates namespace `tailscale`, Deployment `operator`, RBAC,
  IngressClass `tailscale`, and the CRDs. `installCRDs` (default true) uses
  templates rather than Helm's `crds/` so `helm upgrade` updates them.
- Charts and images for a stable release land a few days after the client
  release. An unstable repo is at https://pkgs.tailscale.com/unstable/helmcharts.
- Useful values: `operatorConfig.{defaultTags,hostname,logging,podLabels}`,
  `proxyConfig.{defaultTags,firewallMode,defaultProxyClass}`,
  `apiServerProxyConfig.{mode,allowImpersonation}`, `loginServer`,
  `oauth.audience`. `proxyConfig.defaultProxyClass` does not apply to
  Connectors.
- Multiple default tags are one comma-separated string. Escape the comma with
  `--set` (`tag:a\,tag:b`) or use
  `--set-json 'proxyConfig.defaultTags=["tag:k8s","tag:prod"]'`.
- Do not set `nameOverride` or `fullnameOverride` on an existing install: the
  operator re-registers as a new device and `helm upgrade` fails on the
  immutable pod selector.
- Operator logs: `kubectl logs deployment/operator --namespace tailscale`.
  By default pods carry label `app: operator`, not `app=tailscale-operator`. Raise
  verbosity with `--set operatorConfig.logging=debug` (info|debug|dev).
  Source: https://tailscale.com/docs/kubernetes-operator/reference/troubleshooting
- Compatibility: Kubernetes v1.23.0 or later. The operator supports proxies up
  to four minor versions older than itself and does not support newer proxies;
  run the same version for both. A Tailscale contributor advised upgrading
  the operator incrementally rather than across many minors, for example
  1.94 to 1.102 (community-tier evidence:
  https://github.com/tailscale/tailscale/issues/20916).
  https://tailscale.com/docs/kubernetes-operator/reference/compatibility
- The quickstart ACL (allow-all, funnel for tagged proxies) and its
  cluster-admin ClusterRoleBinding are for test tailnets only. Do not copy
  them into a real policy.
  https://tailscale.com/docs/kubernetes-operator/quickstart

### OAuth client and tags

- Create an OAuth client with write scope on General/Services, Devices/Core,
  and Keys/Auth Keys, each restricted to `tag:k8s-operator`. The
  troubleshooting page lists only two scopes; follow the install page.
  The client must be allowed every tag the operator applies. After replacing
  a client, reinstall the operator so it mints a new key.
- Minimum tag policy; the operator tag must own every other tag it applies
  (`tailscale.com/tags`, `proxyConfig.defaultTags`, `spec.tags` on Connector,
  ProxyGroup, Recorder). Declare every tag explicitly in `tagOwners`; do not
  write pattern-based tag ownership:

  ```hujson
  "tagOwners": {
    "tag:k8s-operator": [],
    "tag:k8s": ["tag:k8s-operator"],
  },
  ```

- Tags apply only when a device is first provisioned. Changing
  `tailscale.com/tags` (or `tailscale.com/hostname`) on an exposed Service
  needs the Service recreated; Connector and ProxyGroup `spec.tags` are
  immutable. https://tailscale.com/docs/kubernetes-operator/reference/tags
  and .../reference/limitations

### Workload identity federation (beta, operator 1.92.3+)

The operator authenticates with its ServiceAccount OIDC token instead of a
long-lived secret. Page:
https://tailscale.com/docs/kubernetes-operator/manage-and-configure/workload-identity-federation

```bash
kubectl create clusterrolebinding oidc-discovery \
  --clusterrole=system:service-account-issuer-discovery \
  --group=system:unauthenticated
kubectl get --raw /.well-known/openid-configuration | jq .issuer
```

Create a federated identity in the admin console with that issuer, subject
`system:serviceaccount:tailscale:operator`, and the same three scopes on
`tag:k8s-operator`. Helm: `--set-string oauth.audience=<aud>` instead of
`oauth.clientSecret`. Static manifests: drop the `operator-oauth` Secret, add
a `CLIENT_ID` env var, mount a projected serviceAccountToken volume.

### Platform limits

- Since v1.78 both proxy containers run privileged. To reduce privilege, use a
  device plugin providing `/dev/net/tun` plus a ProxyClass limiting the
  container to `NET_ADMIN` and `NET_RAW`.
  https://tailscale.com/docs/kubernetes-operator/reference/rbac
- EKS Fargate supports only Tailscale Ingress (L7) and the API server proxy.
  GKE Autopilot and other platforms restricting privileged pods are not
  officially supported.
- Cilium in kube-proxy replacement mode bypasses the proxy pod's netfilter
  rules for pod-to-ClusterIP traffic. Enable "bypass socket load balancer in
  Pods' namespaces" when exposing via `loadBalancerClass: tailscale`,
  `tailscale.com/expose`, or a Service CIDR through a Connector. Pass Cilium
  `--devices` if you see bandwidth problems, so it does not take MTU from
  `tailscale0`. Most other CNIs work unchanged because proxying happens in
  the proxy pod's own namespace.

## Ingress (tailnet to cluster)

https://tailscale.com/docs/kubernetes-operator/ingress

| Layer | Resource | Notes |
|---|---|---|
| L7 | `Ingress` with `ingressClassName: tailscale` | Tailscale Serve, HTTPS only, needs MagicDNS and HTTPS enabled on the tailnet |
| L3 | `Service` with `tailscale.com/expose: "true"`, or `type: LoadBalancer` + `loadBalancerClass: tailscale` | TCP/UDP via DNAT to the ClusterIP, no HTTPS needed |

- L7 hostname comes from the first `spec.tls.hosts` entry. Only
  `pathType: Prefix` is supported. `tailscale.com/http-redirect` adds an
  HTTP-to-HTTPS redirect (1.92.3+). L7 proxies run tailscaled in userspace
  mode, so throughput can be below an L3 proxy (community-tier evidence, a
  2024 Tailscale member comment, with later userspace performance work
  reported in the thread: https://github.com/tailscale/tailscale/issues/12393;
  measure before assuming).
- Private (Serve) is the default. Public exposure is opt-in per Ingress with
  `tailscale.com/funnel: "true"` and needs the `funnel` nodeAttr on the proxy
  tag; `autogroup:member` does not include tagged devices
  ([expose-services.md](expose-services.md#funnel-public)).
  https://tailscale.com/docs/kubernetes-operator/ingress/expose-workload-to-internet
- Machine names: `tailscale.com/hostname` (Services), max 63 characters,
  letters/digits/hyphen, starting and ending with a letter; a `-1` style
  suffix is added on collision.
- Exposing a cloud service (for example RDS): an `ExternalName` Service with
  `tailscale.com/expose: "true"` and the DNS name in `spec.externalName`. The
  operator re-resolves every 10 minutes; nftables mode uses only the first IP.
  Use a Connector for CIDRs or names that do not resolve.
  https://tailscale.com/docs/kubernetes-operator/egress/expose-rds-to-tailnet

### Certificates

- L7 certs are Let's Encrypt certs for the MagicDNS name, issued lazily on the
  first client connection, so the first request can be slow or time out.
  Limits: 50 certs per week for unique hostnames per tailnet, 5 duplicates per
  week. Design ephemeral previews to reuse hostnames.
- Test with a ProxyClass `useLetsEncryptStagingEnvironment: true` (Ingress
  only; flipping back to false re-issues from production).
- Certs last 90 days and renew only while there is traffic. Chart
  `operatorConfig.sharedACMEAccountKey` (ProxyGroup annotation
  `tailscale.com/share-acme-account`) shares one ACME account key across
  restarts and recreation.
- Rate-limit errors on an older operator: 1.92.5 stopped default ACME ARI
  renewals, and 1.102.2 fixed renewal backoff and stopped issuing certs for
  Tailscale Services being torn down. Upgrade to 1.102.2 or later. See
  https://tailscale.com/changelog and
  https://github.com/tailscale/tailscale/issues/11119.

## Egress (cluster to tailnet)

https://tailscale.com/docs/kubernetes-operator/egress/access-tailnet-service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: db
  annotations:
    tailscale.com/tailnet-fqdn: db.example-tailnet.ts.net
spec:
  type: ExternalName
  externalName: placeholder # overwritten by the operator
```

- `type` must be `ExternalName`. Use exactly one of
  `tailscale.com/tailnet-fqdn` (preferred; follows IP changes) or
  `tailscale.com/tailnet-ip` (single IP, no ranges). The egress overview's
  `tailnet-target-ip` is a docs error; the operator reads `tailnet-ip`.
- Pods cannot reach tailnet devices by raw 100.x or ULA address; use the
  Service name.
- HA: add `tailscale.com/proxy-group: <egress ProxyGroup>`. `spec.ports` is
  then required (port, protocol, name), many Services share one ProxyGroup,
  traffic round-robins across replicas, and each port maps to a random
  10000-10999 port on an operator-created ClusterIP Service. Wait with
  `kubectl wait svc <name> --for=condition=TailscaleEgressSvcReady=true
  --timeout=5m`. Graceful drain works only if the ProxyClass does not set a
  custom `TS_LOCAL_ADDR_PORT` on the tailscale container.
- Egress proxies can target Tailscale Service VIPs (1.94.1+).
- Targets behind a subnet router or 4via6: attach a ProxyClass with
  `spec.tailscale.acceptRoutes: true` to the egress ProxyGroup, then use
  `tailnet-ip` (or a `10-1-0-5-via-7.<tailnet>.ts.net` FQDN). Generate the
  4via6 address with `tailscale debug via <siteID> <IPv4>`. 4via6 needs cluster
  IPv6 (dual-stack per the 1.102.2 changelog); egress ProxyGroups support IPv6
  from 1.102.2.
  https://tailscale.com/docs/kubernetes-operator/egress/access-ip-behind-subnet-router
  and .../reference/ipv6
- Egress still depends on tailnet policy: write grants from the proxy tag to
  the destinations and ports the workload needs.

### MagicDNS from pods (DNSConfig)

Pods do not resolve `*.ts.net` by default. `DNSConfig` is a cluster-scoped
singleton running a nameserver that answers only for Tailscale egress and
Ingress proxies in that cluster, not arbitrary tailnet devices. Wire it in as
a CoreDNS stub domain:

```bash
kubectl get dnsconfig ts-dns -o jsonpath='{.status.nameserver.ip}'
# CoreDNS: ts.net:53 { errors; cache 30; forward . <that-ip> }
```

https://tailscale.com/docs/kubernetes-operator/egress/enable-magicdns-resolution

To reach an Ingress's own MagicDNS name from inside the cluster, the
experimental annotation `tailscale.com/experimental-forward-cluster-traffic-via-ingress`
runs the proxy non-userspace with a privileged init container and exposes the
serve listener on the pod's other interfaces. Enable only where the pod
network is trusted.

## ProxyGroup, HA, And Tailscale Services

https://tailscale.com/docs/kubernetes-operator/concepts/proxygroup

- `spec.type`: `ingress`, `egress`, or `kube-apiserver` (immutable).
  `spec.replicas` defaults to 2. `spec.tags` defaults to `tag:k8s` and cannot
  change once devices exist. Also `spec.hostnamePrefix` and immutable
  `spec.tailnet`. The referenced ProxyClass must exist and be Ready first.
- HA ingress: annotate the Ingress or LoadBalancer Service with
  `tailscale.com/proxy-group: <name>`. The operator creates a Tailscale
  Service per exposed resource; the IP and DNS name belong to that Service,
  not to the proxy devices. Service tags come from the
  `tailscale.com/tags` annotation.
- Grants for HA ingress target the Tailscale Service tag, not the ProxyGroup
  device tag. Auto-approval maps the service tag to the device tag:

  ```hujson
  "autoApprovers": { "services": { "tag:monitoring": ["tag:eu-cluster"] } },
  ```

  Advertisement (proxy), approval (`autoApprovers.services`), and access
  (grants) are separate steps. You cannot add `tailscale.com/proxy-group` to an
  existing standalone L3 Service; create a new one.
  https://tailscale.com/docs/kubernetes-operator/reference/rbac and
  .../reference/limitations
- Multi-cluster ingress: apply the same Ingress (same `tls` host and
  proxy-group annotation) in each cluster; every ProxyGroup becomes a backend
  of one Tailscale Service. Use a unique `spec.hostnamePrefix` per ProxyGroup.
  Clients must accept routes. Geographic routing needs regional routing
  enabled for the tailnet; without it all clients use one backend.
  https://tailscale.com/docs/kubernetes-operator/ingress/multi-cluster
- Scheduling and resilience live on the ProxyClass
  (`spec.statefulSet.pod.{topologySpreadConstraints,affinity,tolerations}`).
  Create your own PodDisruptionBudget, selecting the pods by a label set with
  ProxyClass `spec.statefulSet.pod.labels`.
  https://tailscale.com/docs/kubernetes-operator/manage-and-configure/high-availability
- `ProxyGroupPolicy` (1.96+) restricts which ProxyGroups a namespace may
  name in `tailscale.com/proxy-group` (`spec.ingress`, `spec.egress`), enforced
  through a ValidatingAdmissionPolicy. No policy means allow-all, empty lists
  deny all, existing resources are not re-evaluated until modified.
  https://tailscale.com/docs/kubernetes-operator/manage-and-configure/proxy-group-policy

## ProxyClass

https://tailscale.com/docs/kubernetes-operator/concepts/proxyclass

- Cluster-scoped. Attach with annotation `tailscale.com/proxy-class: <name>`
  on an Ingress or Service, or `spec.proxyClass` on Connector, ProxyGroup, or
  PeerRelay. Cluster default: Helm `proxyConfig.defaultProxyClass` or env
  `PROXY_DEFAULT_CLASS` (not applied to Connectors).
- Fields: `statefulSet` (labels, annotations, pod), `metrics.enable`,
  `tailscale.acceptRoutes`, `useLetsEncryptStagingEnvironment`,
  `staticEndpoints.nodePort`.
- Metrics: `metrics.enable` serves `/metrics` on port 9002 and creates a
  `<statefulset>-metrics` Service; `metrics.serviceMonitor.enable` creates a
  Prometheus ServiceMonitor. Documented as unstable, debugging only, and
  unsupported for egress proxies. Since 1.82, metrics and debug endpoints
  default off independently; pprof and `/debug/metrics` need
  `statefulSet.pod.tailscaleContainer.debug.enable: true`.
- Static endpoints (1.86+, ProxyGroup only) create one NodePort Service per
  replica so tailnet clients connect directly rather than via DERP. Max two per
  ProxyGroup; selected Nodes need an ExternalIP; ports must sit in the NodePort
  range with inbound UDP open. Verify by exposing a test Service through the
  ProxyGroup (`tailscale.com/proxy-group`, `loadBalancerClass: tailscale`) and
  running `tailscale ping <its EXTERNAL-IP>`: `via <ip>:<port>` is direct,
  `via DERP(...)` means firewall or selector problems.
  https://tailscale.com/docs/kubernetes-operator/manage-and-configure/configure-static-endpoints

## Connector

Subnet router, exit node, or app connector run from the cluster. Sources:
https://tailscale.com/docs/kubernetes-operator/connector/deploy-subnet-router
and https://tailscale.com/docs/kubernetes-operator/connector/deploy-app-connector

- `spec.appConnector` is mutually exclusive with `subnetRouter` and `exitNode`;
  the latter two can combine. `advertiseRoutes` accepts IPv4/IPv6 CIDRs,
  including 4via6.
- `spec.replicas` (default 1, 1.88.2+) gives HA. Use `spec.hostname` only with
  an unset or single replica count, else `spec.hostnamePrefix`. `spec.tags` and `spec.tailnet`
  are immutable.
- Advertised routes still need approval (or an `autoApprovers` entry for the
  tag), and clients must accept them (`--accept-routes` on Linux). The
  route gates are listed in
  [routing-connectors.md](routing-connectors.md#route-injection).
- Ready check: `kubectl wait --for condition=ConnectorReady=true Connector <name>`.
- App connector on Kubernetes is only tested for public SaaS domains; a stable
  egress IP for allowlists requires your own static-IP NAT.

## API Server Proxy

https://tailscale.com/docs/kubernetes-operator/api-server-access/setup-api-over-tailscale

- Modes: `auth` (default; impersonates the caller) and `noauth` (forwards
  unmodified, for cloud IAM or an external authenticating proxy).
- Shapes: in-process in the operator (Helm `apiServerProxyConfig.mode`
  `"true"` or `"noauth"`; static manifests env `APISERVER_PROXY`), or a
  dedicated HA `ProxyGroup` with `spec.type: kube-apiserver`, `replicas`,
  `kubeAPIServer.mode`, optional `kubeAPIServer.hostname`. Prefer the
  ProxyGroup for production. Auth mode on a ProxyGroup needs
  `apiServerProxyConfig.allowImpersonation="true"`, grants on `tcp:80` and
  `tcp:443`, and `autoApprovers.services` for the ProxyGroup tag.
- Client setup (`configure kubeconfig` is ALPHA; `--http` uses HTTP):

  ```bash
  kubectl wait proxygroup <name> --for=condition=ProxyGroupReady=true
  tailscale configure kubeconfig <hostname-or-fqdn>
  ```

- Auth-mode identity: untagged devices impersonate as their login name; tagged
  devices as their node FQDN with each tag as a Kubernetes group. A grant with
  app capability `tailscale.com/cap/kubernetes`, `dst` the proxy's tag, and
  `{"impersonate":{"groups":["<name>"]}}` replaces the tag-derived groups.
  Groups need not pre-exist; bind with
  `kubectl create clusterrolebinding X --group=<name> --clusterrole=view`.
  Tailnet reachability grants no Kubernetes permissions by itself.
  https://tailscale.com/docs/kubernetes-operator/api-server-access/auth-and-rbac
- noauth: client certificates are not forwarded, so cert-authenticated
  distributions (for example k3s) need auth mode. Set the kubeconfig `server` to
  `https://<proxy>.<tailnet>.ts.net:443` and delete
  `certificate-authority-data`. HTTPS must be enabled on the tailnet; the
  first request can time out while the cert is issued.
  https://tailscale.com/docs/kubernetes-operator/api-server-access/noauth-mode

## Recorder

https://tailscale.com/docs/kubernetes-operator/recorder/kubectl-session-recording

`tsrecorder` is deprecated and not offered to new users; see
[policy-security.md](policy-security.md#session-recording). This section is for
existing deployments.

- `Recorder` needs the API server proxy. `spec.tags` must be owned by the
  operator tag. Storage defaults to an ephemeral local volume (lost with the
  pod); use `spec.storage.s3` for durability. `enableUI: true` serves the UI on
  443. `replicas` defaults to 1; more than one requires S3 (1.92.3+).
- Recording is enabled by grants with app capability `tailscale.com/cap/kubernetes`
  and `recorder: ["tag:tsrecorder"]`. Add `enforceRecorder: true` to block
  sessions when the recorder is unreachable. `enableEvents: true` (beta) also
  records API requests, not only exec/attach/debug. It replaces the removed
  `TS_EXPERIMENTAL_KUBE_API_EVENTS` (1.96.5).
- Treat recordings as sensitive audit material; confirm retention and access.

## Multi-Tailnet And Peer Relay

- Multi-tailnet (1.96+): a cluster-scoped `Tailnet` CRD (short name `tn`,
  condition `TailnetReady`) references a Secret with OAuth `client_id` and
  `client_secret`, or WIF `client_id` and `audience` (1.102.2+).
  ProxyGroup, Connector, and Recorder select it with immutable `spec.tailnet`.
  Each tailnet needs `tagOwners` for the operator tag. The docs example's
  `apiVersion: tailscale.com/v1alpha` is a typo; use `v1alpha1`.
  https://tailscale.com/docs/kubernetes-operator/manage-and-configure/multi-tailnet
- `PeerRelay` (operator 1.102.2+, `v1alpha1`): runs peer relays in-cluster, each replica
  behind its own LoadBalancer Service (cost scales with replicas). The
  operator writes each replica's address as the static endpoint; do not run
  `tailscale set --relay-server-static-endpoints` in the pods. Clients need a
  grant with app capability `tailscale.com/cap/relay` to the relay's tag. On
  AWS use 1.102.3 or later (HTTP health checks, since relays listen on UDP
  only). Verify with
  `kubectl wait --for=condition=PeerRelayReady=true peerrelay <name>` and
  `tailscale debug peer-relay-servers`.
  https://tailscale.com/docs/kubernetes-operator/peer-relay

## Troubleshooting

https://tailscale.com/docs/kubernetes-operator/reference/troubleshooting

- Proxies for Ingress, Service, and Connector are single-replica StatefulSets
  in namespace `tailscale`. Find pods and Secrets by labels
  `tailscale.com/parent-resource`, `tailscale.com/parent-resource-ns`, and
  `tailscale.com/parent-resource-type` (`ingress`, `svc`, `connector`,
  `proxygroup`).
- L7 proxy config: decode the Secret field `serve-config`, then
  `kubectl exec <pod> -n tailscale -- tailscale serve status`.
- Backend unreachable from the proxy pod: check for a NetworkPolicy blocking
  the `tailscale` namespace.
- TLS errors, in order: HTTPS not enabled on the tailnet, certificate still
  provisioning, Let's Encrypt rate limits.
- Pod connections stuck on DERP: CNI or cloud SNAT with port randomization
  (AWS VPC CNI by default; Azure SNATs in its default mode; Flannel
  `--random-fully` per a community-tier comment in
  https://github.com/tailscale/tailscale/issues/11427) and hard NAT prevent
  direct paths, and Tailscale does not guarantee direct connections on
  Kubernetes.
  Publish a reachable endpoint with ProxyGroup static endpoints, or run a
  manual pod with `hostNetwork: true`, fixed UDP `PORT`, and inbound UDP
  allowed. https://tailscale.com/blog/kubernetes-direct-connections
- Diagnostic lead (community, 2026-09-29, not a guarantee): after upgrading
  to 1.102.2, new egress ProxyGroup Services stuck unready or flapping with
  `TailscaleEgressSvcConfigured` False (a reconciler race a Tailscale
  contributor reproduced; the issue is closed, the fixing release is not
  confirmed); move to the newest patch release.
  https://github.com/tailscale/tailscale/issues/20916

## Sidecar Without The Operator

Use when a pod needs its own tailnet identity and the operator is not
installed. Source:
https://tailscale.com/docs/solutions/connect-kubernetes-pods-to-tailnet-using-sidecar

- Persist state. Never use `--state=mem:` or leave state unconfigured in
  production: each restart registers a new device, and under load the
  registration flood can cause sustained outages that do not self-heal.
- Use a StatefulSet with `TS_KUBE_SECRET=$(POD_NAME)` (containerboot then uses
  `--state=kube:<secret>`). A Deployment has unstable pod names and orphans
  Secrets. RBAC: a Role on `secrets` with `get, create, update, patch`;
  pre-created Secrets can be scoped with `resourceNames` for get/update/patch,
  but RBAC cannot restrict `create` by `resourceNames`. Alternative:
  `TS_KUBE_SECRET=""` with `TS_STATE_DIR` on a PVC (durable) or emptyDir
  (survives container crash, not pod restart). Avoid
  `podManagementPolicy: Parallel` at high replica counts.
- Auth: an OAuth client secret registers ephemeral nodes by default
  ([automation-api.md](automation-api.md#ephemeral-defaults-for-oauth-and-wif-registration)). For
  stable identity use `TS_CLIENT_ID` and
  `TS_CLIENT_SECRET='tskey-client-...?ephemeral=false&preauthorized=true'`
  (keep it quoted). Alternatives: a tagged `TS_AUTHKEY` from a Secret, or WIF
  via `TS_CLIENT_ID` + `TS_AUDIENCE`. Tag with
  `TS_EXTRA_ARGS=--advertise-tags=tag:k8s` and restrict inbound with policy.
  `--shields-up` blocks all inbound tailnet connections regardless of policy.
- DNS: `TS_ACCEPT_DNS=true` rewrites `/etc/resolv.conf` to `100.100.100.100`
  for every container in the pod. DNS fails until the sidecar connects (use a
  native sidecar container), and in-cluster names stop resolving unless split
  DNS for `svc.cluster.local` points at the CoreDNS ClusterIP
  (`kubectl get svc -n kube-system kube-dns -o jsonpath='{.spec.clusterIP}'`).
  Sidecars in several clusters need unique cluster DNS domains. If only
  tailnet IPs are needed, set `TS_ACCEPT_DNS=false`.
- `--accept-routes` has no overlap detection: it installs every advertised
  route into routing table 52. A tailnet route covering the pod or service
  CIDR hairpins in-cluster traffic into the tun device. Compare first:

  ```bash
  tailscale status --json | jq '.Peer[] | select(.PrimaryRoutes) | {name: .HostName, routes: .PrimaryRoutes}'
  kubectl cluster-info dump | grep -m 2 -E 'service-cluster-ip-range|cluster-cidr'
  ```

  Kernel-mode sidecars that accept routes, advertise routes, or proxy need a
  privileged initContainer setting `net.ipv4.ip_forward` and
  `net.ipv6.conf.all.forwarding`.
- Do not use `/healthz` (`TS_ENABLE_HEALTH_CHECK=true`) or a MagicDNS lookup
  as a livenessProbe: `/healthz` returns 503 when the node briefly has no
  tailnet IP, so restarts force re-registration and amplify outages. The
  operator configures no probes on its proxies. `/healthz` and metrics
  (`TS_ENABLE_METRICS`) share `TS_LOCAL_ADDR_PORT` (default `[::]:9002`).
