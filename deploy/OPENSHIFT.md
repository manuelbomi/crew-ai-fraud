# Notes on OpenShift Compatibility

A number of large regulated institutions run Red Hat OpenShift rather than
vanilla Kubernetes. The manifests in `deploy/k8s/` are written to be
OpenShift-compatible with no changes required, for a few specific reasons:

1. **No hardcoded UID/GID.** `deployment.yaml` sets `runAsUser: 1000` /
   `runAsGroup: 1000` to match the Dockerfile's `appuser`, but OpenShift's
   default `restricted` (or `restricted-v2`) Security Context Constraint
   (SCC) assigns an arbitrary UID from the namespace's allocated range at
   admission time and generally overrides a pod-specified `runAsUser`
   unless the namespace/SCC explicitly permits it. The application does
   not assume a specific UID anywhere in its own code -- it only needs
   *some* non-root, writable-`/tmp` identity, which the Dockerfile's
   `chmod`-free, group-writable-nothing setup already tolerates.
2. **`readOnlyRootFilesystem: true` with an explicit `/tmp` `emptyDir`.**
   OpenShift's restricted SCC forbids writable root filesystems by
   default; the Deployment already mounts a writable `/tmp` volume, which
   is where the audit log JSONL file would need to be redirected via
   `AUDIT_LOG_PATH=/tmp/audit_log.jsonl` in a real OpenShift deployment
   (the default `audit_log.jsonl` is a relative path under the working
   directory, which is not guaranteed writable under an arbitrary UID).
3. **No `NET_RAW`/other elevated capabilities requested**, and
   `allowPrivilegeEscalation: false` + `capabilities.drop: ["ALL"]` are
   already set, which satisfies the restricted SCC's requirements without
   needing a custom SCC.
4. **Route vs. Ingress.** `service.yaml` is a plain `ClusterIP` Service;
   OpenShift users would front it with a `Route` (`oc expose service
   fraud-aml-investigation-crew`) instead of a Kubernetes `Ingress` --
   not included here since it's a one-line `oc` command and Route specifics
   vary by cluster (TLS termination policy, custom domains, etc.).

## Suggested apply order

```bash
oc apply -f deploy/k8s/configmap.yaml
oc apply -f deploy/k8s/deployment.yaml
oc apply -f deploy/k8s/service.yaml
oc expose service fraud-aml-investigation-crew
```

If you want to point the deployment at a real LLM provider, create a
Secret named `fraud-crew-secrets` with `OPENAI_API_KEY` and/or
`ANTHROPIC_API_KEY` keys before applying the Deployment -- it's referenced
as `optional: true`, so the app runs fine (using MockLLM) without it too.
