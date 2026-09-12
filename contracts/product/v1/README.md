# Reactor Product contract v1

Status: `REFERENCE_MVP_READY`; the subprocess/HTTP adapter proves the Product
boundary, not production vLLM, KServe, GPU, or distributed reconciliation.

Reactor owns durable `Deployment` intent/observation and distinct `Endpoint`
resources. A serving engine owns model loading and request execution; it cannot
publish Product `READY` state. A Kernel operation or Node Agent report may be
evidence for reconciliation, but neither is the Deployment source of truth.

## Non-negotiable split

- `Deployment` is desired and observed Product lifecycle.
- `Endpoint` is an addressable serving surface with its own lifecycle. A ready
  Deployment may temporarily have an unhealthy Endpoint, and a stopped
  Deployment retains a retired Endpoint record for audit.
- `execution.engine.v1` is a Plugins-owned capability type. `servingBindingId` selects a bound
  capability instance; it is not a provider/package identity.
- Runtime execution evidence is stored in an internal adapter table and never
  appears in the public Deployment schema. It is not Product identity or state.
- Artifact bytes remain in the Artifact Plane; Deployment persists a model
  `ArtifactRef` only.
- `ModelVersion` is the Yield-owned immutable content identity. Reactor
  accepts `FULL_MODEL` compatibility requests and the V1 `BASE_PLUS_LORA`
  composition with exactly one base and one adapter; a composed Deployment's
  `modelArtifact` is only the base projection and `modelVersion.id` remains the
  serving identity.
- Events are notifications after Product commits, never the source of truth.

## Notifications

After durable commits, Reactor may publish created/updated notifications for
`deployment` and `endpoint`, using types such as
`dev.cyrene.reactor.deployment.updated.v1`. The common Product event envelope
contains only resource URI/version and change kind; consumers re-read Reactor
and tolerate duplicates, reordering, and newer versions. The local-process MVP
does not claim a durable outbox publisher.

## State

`Deployment.observedState`: `STARTING -> READY | FAILED`, `READY -> DEGRADED`,
and `READY | DEGRADED | FAILED -> STOPPING -> STOPPED`.

`Endpoint.state`: `PROVISIONING -> READY | UNHEALTHY -> RETIRED`.

On restart, Reactor validates persisted internal execution evidence and endpoint
identity through its local application port. It never infers `READY` from a
package, binding, PID, or Kernel lease alone. `serving-execution-port.md` maps
that local port to the Plugins-owned `execution.engine.v1` contract without
redefining it or proxying payloads through Platform.

## Compatibility

The API root is `/api/v1` and consumes the Workspace `product-http-v1`
compatibility profile, including deprecation and removal policy. OpenAPI is
3.1.2; JSON Schema is Draft 2020-12; errors follow RFC 9457.

The MVP is synchronous and returns `201`. A production reconciler may honor RFC
7240 and return `202` with `Location` naming the Product-owned Deployment. It
must not expose or create a second Kernel Operation API.

`Idempotency-Key` maps a create command to its durable Deployment before engine
startup. Replaying the same canonical body returns that Deployment's current
state, including `FAILED`; conflicting body reuse returns
`REACTOR_IDEMPOTENCY_CONFLICT`.
