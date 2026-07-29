"""CLI for policy validation, manifest compilation, plans, and drift."""

from __future__ import annotations

import argparse
import json

from .compiler import ManifestCompiler
from .graph import DependencyGraph
from .models import PolicyConfig, load_specs
from .planner import build_plan, drift_report, load_actual_state, plan_report
from .policy import validate_specs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile synthetic dataset intents into dry-run platform manifests."
    )
    parser.add_argument("--spec-dir", default="examples/specs")
    parser.add_argument("--policy", default="config/policy.json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")

    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("--output", default="artifacts")

    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--actual", required=True)

    drift_parser = subparsers.add_parser("drift")
    drift_parser.add_argument("--actual", required=True)

    graph_parser = subparsers.add_parser("graph")
    graph_parser.add_argument("--format", choices=("json", "mermaid"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    specs = load_specs(args.spec_dir)
    policy = PolicyConfig.load(args.policy)

    if args.command == "validate":
        violations = validate_specs(specs, policy)
        print(
            json.dumps(
                {
                    "valid": not violations,
                    "dataset_count": len(specs),
                    "violation_count": len(violations),
                    "violations": [item.to_dict() for item in violations],
                    "synthetic": all(spec.synthetic for spec in specs.values()),
                    "production_deployment": any(
                        spec.production_deployment for spec in specs.values()
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if not violations else 1

    if args.command == "graph":
        graph = DependencyGraph(specs)
        if args.format == "mermaid":
            print(graph.to_mermaid())
        else:
            print(json.dumps(graph.to_dict(), indent=2, sort_keys=True))
        return 0

    compiler = ManifestCompiler(specs, policy)
    if args.command == "compile":
        written = compiler.write(args.output)
        bundle = compiler.compile()
        print(
            json.dumps(
                {
                    "output": args.output,
                    "files_written": len(written),
                    "resource_count": len(bundle["resources"]),
                    "bundle_fingerprint": bundle["bundle_fingerprint"],
                    "synthetic": True,
                    "production_deployment": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    bundle = compiler.compile()
    actions = build_plan(bundle, load_actual_state(args.actual))
    if args.command == "plan":
        print(json.dumps(plan_report(actions), indent=2, sort_keys=True))
        return 0
    if args.command == "drift":
        report = drift_report(actions)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2 if report["has_drift"] else 0
    raise RuntimeError(f"unsupported command: {args.command}")  # pragma: no cover

