from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from control_plane.compiler import ManifestCompiler
from control_plane.models import PolicyConfig, load_specs


class ManifestCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = ManifestCompiler(
            load_specs("examples/specs"),
            PolicyConfig.load("config/policy.json"),
        )

    def test_compilation_is_deterministic(self) -> None:
        first = self.compiler.compile()
        second = self.compiler.compile()
        self.assertEqual(first, second)
        self.assertEqual(first["metadata"]["deployment_order"][0], "raw_orders")
        self.assertEqual(len(first["resources"]), 12)

    def test_infrastructure_defaults_fail_secure(self) -> None:
        storage = self.compiler.compile()["resources"]["storage.curated_orders"]
        self.assertTrue(storage["encryption"]["enabled"])
        self.assertFalse(storage["access"]["public_access"])
        self.assertEqual(storage["lifecycle"]["retention_days"], 730)

    def test_pipeline_manifest_retains_policy_and_dependency_intent(self) -> None:
        pipeline = self.compiler.compile()["resources"]["pipeline.curated_orders"]
        self.assertEqual(pipeline["depends_on"], ["pipeline.raw_orders"])
        self.assertEqual(pipeline["target"], "dataset.curated_orders")
        self.assertEqual(len(pipeline["quality_gates"]), 2)

    def test_write_creates_reviewable_split_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self.compiler.write(temporary_directory)
            root = Path(temporary_directory)
            bundle = json.loads((root / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(len(paths), 7)
            self.assertTrue((root / "pipelines" / "raw_orders.json").is_file())
            self.assertTrue(
                (root / "infrastructure" / "daily_revenue.json").is_file()
            )
            self.assertEqual(len(bundle["resources"]), 12)


if __name__ == "__main__":
    unittest.main()

