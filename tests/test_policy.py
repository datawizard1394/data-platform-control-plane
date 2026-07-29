from __future__ import annotations

import unittest
from dataclasses import replace

from control_plane.graph import DependencyCycleError, DependencyGraph
from control_plane.models import PolicyConfig, load_specs
from control_plane.policy import validate_specs


class PolicyGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = load_specs("examples/specs")
        self.policy = PolicyConfig.load("config/policy.json")

    def test_synthetic_examples_pass_every_gate(self) -> None:
        self.assertEqual(validate_specs(self.specs, self.policy), ())

    def test_missing_accountable_owner_fails(self) -> None:
        specs = dict(self.specs)
        specs["raw_orders"] = replace(specs["raw_orders"], owner="")
        codes = {item.code for item in validate_specs(specs, self.policy)}
        self.assertIn("ownership", codes)

    def test_pii_rolls_up_to_dataset_classification(self) -> None:
        specs = dict(self.specs)
        specs["raw_orders"] = replace(
            specs["raw_orders"],
            classification="internal",
        )
        codes = {item.code for item in validate_specs(specs, self.policy)}
        self.assertIn("classification_rollup", codes)
        self.assertIn("pii_classification", codes)

    def test_retention_cap_is_enforced_by_classification(self) -> None:
        specs = dict(self.specs)
        specs["raw_orders"] = replace(specs["raw_orders"], retention_days=731)
        violations = validate_specs(specs, self.policy)
        self.assertIn("retention", {item.code for item in violations})

    def test_unknown_dependency_fails_closed(self) -> None:
        specs = dict(self.specs)
        specs["curated_orders"] = replace(
            specs["curated_orders"],
            dependencies=("missing_dataset",),
            source_uri="dataset://missing_dataset",
        )
        codes = {item.code for item in validate_specs(specs, self.policy)}
        self.assertIn("unknown_dependency", codes)

    def test_partition_key_must_exist_in_schema(self) -> None:
        specs = dict(self.specs)
        specs["daily_revenue"] = replace(
            specs["daily_revenue"],
            partition_by=("missing_field",),
        )
        codes = {item.code for item in validate_specs(specs, self.policy)}
        self.assertIn("partition_field", codes)

    def test_demo_spec_cannot_claim_production(self) -> None:
        specs = dict(self.specs)
        specs["daily_revenue"] = replace(
            specs["daily_revenue"],
            production_deployment=True,
        )
        codes = {item.code for item in validate_specs(specs, self.policy)}
        self.assertIn("demo_provenance", codes)


class DependencyGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = load_specs("examples/specs")

    def test_topological_order_is_stable(self) -> None:
        self.assertEqual(
            DependencyGraph(self.specs).topological_order(),
            ("raw_orders", "curated_orders", "daily_revenue"),
        )

    def test_cycle_is_detected(self) -> None:
        specs = dict(self.specs)
        specs["raw_orders"] = replace(
            specs["raw_orders"],
            dependencies=("daily_revenue",),
        )
        with self.assertRaises(DependencyCycleError):
            DependencyGraph(specs).topological_order()

    def test_mermaid_graph_contains_dependency_edges(self) -> None:
        mermaid = DependencyGraph(self.specs).to_mermaid()
        self.assertTrue(mermaid.startswith("flowchart LR"))
        self.assertIn("raw_orders --> curated_orders", mermaid)
        self.assertIn("curated_orders --> daily_revenue", mermaid)


if __name__ == "__main__":
    unittest.main()

