from __future__ import annotations

import unittest

from control_plane.compiler import ManifestCompiler
from control_plane.models import PolicyConfig, load_specs
from control_plane.planner import build_plan, drift_report, plan_report


class DriftPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = ManifestCompiler(
            load_specs("examples/specs"),
            PolicyConfig.load("config/policy.json"),
        ).compile()

    def matching_actual_state(self) -> dict[str, object]:
        return {
            "resources": {
                resource_id: {"fingerprint": resource["fingerprint"]}
                for resource_id, resource in self.bundle["resources"].items()
            }
        }

    def test_matching_state_has_no_drift(self) -> None:
        actions = build_plan(self.bundle, self.matching_actual_state())
        report = drift_report(actions)
        self.assertFalse(report["has_drift"])
        self.assertTrue(all(item.action == "no_change" for item in actions))

    def test_plan_distinguishes_create_update_and_orphan(self) -> None:
        actual = self.matching_actual_state()
        actual["resources"]["dataset.raw_orders"]["fingerprint"] = "stale"
        del actual["resources"]["monitor.daily_revenue"]
        actual["resources"]["dataset.legacy"] = {"fingerprint": "orphan"}

        actions = build_plan(self.bundle, actual)
        report = plan_report(actions)
        drift = drift_report(actions)

        self.assertEqual(report["summary"]["update"], 1)
        self.assertEqual(report["summary"]["create"], 1)
        self.assertEqual(report["summary"]["orphan"], 1)
        self.assertIn("dataset.raw_orders", drift["changed"])
        self.assertIn("monitor.daily_revenue", drift["created"])
        self.assertIn("dataset.legacy", drift["orphaned"])
        self.assertFalse(report["destructive_actions"])


if __name__ == "__main__":
    unittest.main()

