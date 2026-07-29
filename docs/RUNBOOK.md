# Dataset onboarding and drift runbook

> This is a production-minded procedure for a synthetic demo. The CLI cannot
> create, update, or delete real resources.

## New dataset review

1. Create a spec with a unique dataset name, accountable team owner, domain, and
   useful description.
2. Classify every field; enumerate PII fields; choose dataset classification at
   least as restrictive as its most sensitive field.
3. Justify retention and keep it below the classification policy cap.
4. Define measurable freshness and availability objectives.
5. Declare dependencies, partitions, and schema-backed quality gates.
6. Run validation and inspect the dependency graph.
7. Compile manifests and review the full dry-run plan.
8. In a future production system, bind human approval to the bundle fingerprint.

## Commands

```bash
make check

PYTHONPATH=src python -m control_plane \
  --spec-dir examples/specs --policy config/policy.json validate

PYTHONPATH=src python -m control_plane \
  --spec-dir examples/specs --policy config/policy.json graph --format mermaid

PYTHONPATH=src python -m control_plane \
  --spec-dir examples/specs --policy config/policy.json \
  plan --actual examples/actual_state.json
```

## Plan review gates

- [ ] Every create/update is expected and has an owner
- [ ] No policy violation was waived implicitly
- [ ] Dependency order matches data availability semantics
- [ ] Classification and retention are no less restrictive than before
- [ ] Encryption remains enabled and public access remains disabled
- [ ] Quality and SLO monitors are present
- [ ] Orphans are investigated; none are treated as automatic deletions
- [ ] Bundle fingerprint matches the artifact under review

## Drift response

1. Re-run discovery using read-only credentials and account for provider
   eventual-consistency windows.
2. Classify drift as approved emergency change, manual mistake, imported resource,
   rename/move, stale snapshot, or control-plane defect.
3. Do not overwrite security-sensitive drift until intent and ownership are verified.
4. Import or move resources explicitly where possible; avoid delete-and-recreate.
5. Regenerate and reapprove the plan after desired state changes.
6. Preserve actual snapshot, desired bundle, plan, decision, and outcome for audit.

## Cycle response

Do not bypass the DAG gate. Determine whether the cycle represents:

- a modeling error;
- a shared upstream dataset that should be extracted;
- an iterative algorithm requiring a different execution contract; or
- an invalid cross-layer dependency.

Change the model, then rerun validation and graph review.

## Production signals

Monitor policy failure rate by code, compile and discovery latency, plan size,
unexpected update/orphan counts, apply success and rollback rate, lock contention,
provider throttling, stale actual-state age, and SLO/quality resources missing from
otherwise onboarded datasets.

## Emergency principle

Break-glass changes must be time-bound, attributable, and reconciled back into
declarative intent. An emergency is not a reason to make drift permanent.

