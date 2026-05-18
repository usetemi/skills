# Tailscale Kubernetes

Official docs:

- Kubernetes Operator: https://tailscale.com/docs/features/kubernetes-operator
- OAuth clients: https://tailscale.com/docs/features/oauth-clients
- Kubernetes Operator API server proxy: https://tailscale.com/kb/1437/kubernetes-operator-api-server-proxy
- Kubernetes Operator connectors: https://tailscale.com/kb/1441/kubernetes-operator-connector
- Kubernetes Operator ingress: https://tailscale.com/kb/1439/kubernetes-operator-ingress
- Kubernetes Operator egress: https://tailscale.com/kb/1438/kubernetes-operator-egress
- App connectors: https://tailscale.com/kb/1281/app-connectors

## Decision Path

1. Identify the Kubernetes pattern:
   - expose in-cluster services to the tailnet
   - let pods reach tailnet resources
   - expose the Kubernetes API server through Tailscale
   - run subnet routers or app connectors from the cluster
   - record kubectl sessions
2. Check operator version, CRD availability, and required Tailscale tags before
   writing manifests.
3. Prefer OAuth client credentials scoped to the operator's tags.
4. Keep tailnet policy and Kubernetes RBAC separate in explanations.

Read-only checks:

```bash
kubectl get pods -n tailscale
kubectl get crd | rg 'tailscale'
kubectl get ingress,svc -A
kubectl get proxygroup,proxyclass,connector,recorder -A 2>/dev/null
tailscale status
```

## Operator Prerequisites

- The operator needs Tailscale credentials, normally an OAuth client, and tag
  ownership for the tags it will assign.
- The tailnet policy must allow the operator and proxy tags to do their jobs.
- Kubernetes RBAC controls what the operator can do inside the cluster; tailnet
  policy controls who can reach Tailscale identities.
- Version compatibility matters. Check the current operator docs before using a
  CRD field from memory.

Policy shape:

```hujson
{
  "tagOwners": {
    "tag:k8s-operator": ["autogroup:admin"],
    "tag:k8s": ["tag:k8s-operator"],
  },
  "grants": [
    {
      "src": ["group:platform"],
      "dst": ["tag:k8s"],
      "ip": ["tcp:443"],
    },
  ],
}
```

## Ingress

- Tailscale ingress exposes a Kubernetes service to tailnet clients under a
  Tailscale identity.
- Use it for private admin tools, internal APIs, preview environments, and
  services that should not have a public load balancer.
- Do not assume Kubernetes NetworkPolicy or service annotations replace
  tailnet policy. Use both where needed.

Inspection:

```bash
kubectl describe ingress <name> -n <namespace>
kubectl get svc -n <namespace>
tailscale status
```

## Egress

- Egress patterns let in-cluster workloads reach tailnet resources.
- Restrict which namespaces, workloads, or proxy resources can use egress.
- Write grants from the relevant Kubernetes proxy tag to only the destinations
  and ports the workload needs.
- For production, include DNS behavior and failure mode in the design.

## API Server Proxy

- The API server proxy exposes Kubernetes API access over Tailscale.
- Treat it as sensitive infrastructure. Tailnet access is not a substitute for
  Kubernetes authentication and RBAC.
- Require narrow grants and clear operator ownership before exposing API server
  access to a shared tailnet.

## Connector, ProxyGroup, ProxyClass, And Recorder

- `Connector` resources cover cluster-managed connector patterns such as subnet
  routers or app connectors.
- `ProxyGroup` and `ProxyClass` control how proxy resources are grouped and
  customized. Use them when defaults are not enough for HA, scheduling, or
  configuration.
- `Recorder` supports session recording workflows. Treat recordings as
  sensitive audit material and confirm retention and access controls.
- CRD names, fields, and maturity can change. Always inspect installed CRDs and
  current docs before generating manifests:

  ```bash
  kubectl explain connector.spec
  kubectl explain proxygroup.spec
  kubectl explain proxyclass.spec
  kubectl explain recorder.spec
  ```

## Subnet Routers And App Connectors In Clusters

- Cluster-run subnet routers and app connectors are production infrastructure,
  not just pods. Plan node placement, failover, upgrades, and credential
  rotation.
- Keep advertised routes and connector domains narrow.
- Ensure the cluster network can actually reach the routed subnet or SaaS
  destination.
- For HA, use multiple replicas or operator-supported grouping patterns only
  after checking current docs for the chosen CRD.

## CNI Notes

- CNI, NetworkPolicy, service mesh, and eBPF behavior can affect pod routing and
  DNS. Do not debug Tailscale in isolation when packets cross the cluster data
  plane.
- Collect both Kubernetes state and Tailscale state before changing manifests:

  ```bash
  kubectl get pods,svc,endpoints,endpointslice -A
  kubectl describe pod <pod> -n <namespace>
  kubectl logs -n tailscale -l app=tailscale-operator
  tailscale netcheck
  tailscale status --json
  ```
