"""Dry-run change planning and fingerprint-based drift detection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PlanAction:
    resource_id: str
    action: str
    current_fingerprint: str | None
    desired_fingerprint: str | None
    reason: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "resource_id": self.resource_id,
            "action": self.action,
            "current_fingerprint": self.current_fingerprint,
            "desired_fingerprint": self.desired_fingerprint,
            "reason": self.reason,
        }


def load_actual_state(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        actual = json.load(handle)
    if not isinstance(actual, dict) or not isinstance(actual.get("resources"), dict):
        raise ValueError("actual state must contain a resources object")
    return actual


def build_plan(
    desired_bundle: dict[str, Any],
    actual_state: dict[str, Any],
) -> tuple[PlanAction, ...]:
    desired = desired_bundle["resources"]
    actual = actual_state["resources"]
    actions: list[PlanAction] = []

    for resource_id in sorted(desired):
        desired_fingerprint = desired[resource_id]["fingerprint"]
        current = actual.get(resource_id)
        if current is None:
            actions.append(
                PlanAction(
                    resource_id,
                    "create",
                    None,
                    desired_fingerprint,
                    "resource is absent from actual state",
                )
            )
        elif current.get("fingerprint") != desired_fingerprint:
            actions.append(
                PlanAction(
                    resource_id,
                    "update",
                    current.get("fingerprint"),
                    desired_fingerprint,
                    "actual fingerprint differs from desired manifest",
                )
            )
        else:
            actions.append(
                PlanAction(
                    resource_id,
                    "no_change",
                    desired_fingerprint,
                    desired_fingerprint,
                    "actual fingerprint matches desired manifest",
                )
            )

    for resource_id in sorted(set(actual) - set(desired)):
        actions.append(
            PlanAction(
                resource_id,
                "orphan",
                actual[resource_id].get("fingerprint"),
                None,
                "actual resource is unmanaged; this demo never auto-deletes",
            )
        )
    return tuple(actions)


def plan_report(actions: tuple[PlanAction, ...]) -> dict[str, Any]:
    counts = {
        action: sum(item.action == action for item in actions)
        for action in ("create", "update", "no_change", "orphan")
    }
    return {
        "dry_run": True,
        "destructive_actions": False,
        "summary": counts,
        "actions": [action.to_dict() for action in actions],
    }


def drift_report(actions: tuple[PlanAction, ...]) -> dict[str, Any]:
    drifted = [item for item in actions if item.action != "no_change"]
    return {
        "has_drift": bool(drifted),
        "drift_count": len(drifted),
        "created": [
            item.resource_id for item in actions if item.action == "create"
        ],
        "changed": [
            item.resource_id for item in actions if item.action == "update"
        ],
        "orphaned": [
            item.resource_id for item in actions if item.action == "orphan"
        ],
    }

