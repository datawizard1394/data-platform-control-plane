from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout

from control_plane.cli import main


BASE_ARGS = [
    "--spec-dir",
    "examples/specs",
    "--policy",
    "config/policy.json",
]


class CliTests(unittest.TestCase):
    def test_validate_reports_honest_provenance(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([*BASE_ARGS, "validate"])
        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(result["valid"])
        self.assertTrue(result["synthetic"])
        self.assertFalse(result["production_deployment"])

    def test_compile_writes_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [*BASE_ARGS, "compile", "--output", temporary_directory]
                )
            result = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(result["resource_count"], 12)
            self.assertEqual(result["files_written"], 7)

    def test_drift_returns_nonzero_for_intentional_sample_drift(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    *BASE_ARGS,
                    "drift",
                    "--actual",
                    "examples/actual_state.json",
                ]
            )
        result = json.loads(output.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertTrue(result["has_drift"])


if __name__ == "__main__":
    unittest.main()

