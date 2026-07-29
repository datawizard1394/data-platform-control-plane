# ADR 0001: Compile and plan intent before any mutation

- **Status:** Accepted for this synthetic demo
- **Date:** 2026-07-28
- **Scope:** Offline reference implementation, not a production control plane

## Context

Dataset onboarding spans catalog metadata, storage, IAM, orchestration, quality,
lineage, retention, and monitoring. Directly mutating providers while discovering
missing intent creates partial resources and inconsistent policy.

The demo must show the control boundary clearly without requiring cloud credentials
or implying that fictional manifests were deployed.

## Decision

1. Accept versioned dataset intent as declarative specs.
2. Apply all local and cross-dataset policy gates before compilation.
3. Validate dependencies as a DAG and derive deterministic deployment order.
4. Compile one spec into catalog, pipeline, storage, and monitor resource intents.
5. Hash canonical resources and bundles without volatile timestamps.
6. Compare desired fingerprints with a supplied read-only actual-state snapshot.
7. Report create, update, no-change, and orphan actions as a dry-run plan.
8. Provide no apply command and never turn an orphan into an automatic delete.
9. Require all demo specs to declare synthetic provenance and deny production claims.

## Consequences

### Positive

- Invalid ownership, security, retention, SLO, or dependency intent fails early.
- Desired state is deterministic and reviewable.
- Drift and no-op behavior are easy to test offline.
- Destructive behavior is absent by construction.

### Negative

- Provider-native defaults and eventual consistency are not modeled.
- Fingerprints only detect differences represented in the supplied snapshot.
- Provider-neutral manifests need adapters before they can be deployed.
- Policies are local code rather than an independently governed policy service.

## Alternatives considered

### Generate resources while validating

Rejected because failure midway can leave partial state and unclear rollback.

### Automatically delete orphans

Rejected. Ownership ambiguity, imports, renamed resources, and discovery lag make
automatic deletion unsafe without explicit lifecycle and approval semantics.

### Embed provider SDKs

Deferred. External providers would reduce offline reproducibility and could imply
a level of deployment completeness the demo does not have.

### Use timestamps in manifests

Rejected because volatile fields create perpetual drift and undermine no-op plans.

## Production follow-up

- Authenticate spec authors and authorize changes by domain.
- Store immutable spec, policy, plan, approval, and execution audit events.
- Sign compiled artifacts and bind approvals to their fingerprint.
- Add provider discovery/import/move semantics and consistency windows.
- Implement locked, resumable, idempotent apply with scoped credentials.
- Require explicit delete intent, blast-radius preview, and multi-party approval.
- Add provider adapters, conformance tests, rollback, and disaster recovery.

