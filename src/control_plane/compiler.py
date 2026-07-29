"""Deterministic compiler from onboarding specs to platform-style manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .graph import DependencyGraph
from .models import DatasetSpec, PolicyConfig
from .policy import require_policy_pass


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class ManifestCompiler:
    """Compile validated intent without calling a cloud or orchestration API."""

    def __init__(self, specs: dict[str, DatasetSpec], policy: PolicyConfig) -> None:
        require_policy_pass(specs, policy)
        self.specs = specs
        self.policy = policy

    def compile(self) -> dict[str, Any]:
        order = DependencyGraph(self.specs).topological_order()
        resources: dict[str, dict[str, Any]] = {}
        for name in order:
            spec = self.specs[name]
            spec_fingerprint = fingerprint(spec.to_dict())
            candidates = {
                f"dataset.{name}": self._dataset_resource(spec, spec_fingerprint),
                f"pipeline.{name}": self._pipeline_resource(spec, spec_fingerprint),
                f"storage.{name}": self._storage_resource(spec, spec_fingerprint),
                f"monitor.{name}": self._monitor_resource(spec, spec_fingerprint),
            }
            for resource_id, resource in candidates.items():
                resource["fingerprint"] = fingerprint(resource)
                resources[resource_id] = resource

        ordered_resources = dict(sorted(resources.items()))
        bundle = {
            "api_version": "compiled.platform.demo/v1",
            "metadata": {
                "synthetic": True,
                "production_deployment": False,
                "policy_version": self.policy.policy_version,
                "deployment_order": list(order),
            },
            "resources": ordered_resources,
        }
        bundle["bundle_fingerprint"] = fingerprint(bundle)
        return bundle

    def write(self, output_directory: str | Path) -> tuple[Path, ...]:
        bundle = self.compile()
        root = Path(output_directory)
        pipeline_directory = root / "pipelines"
        infrastructure_directory = root / "infrastructure"
        pipeline_directory.mkdir(parents=True, exist_ok=True)
        infrastructure_directory.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        bundle_path = root / "bundle.json"
        self._write_json(bundle_path, bundle)
        written.append(bundle_path)
        for name in bundle["metadata"]["deployment_order"]:
            pipeline_path = pipeline_directory / f"{name}.json"
            self._write_json(
                pipeline_path,
                bundle["resources"][f"pipeline.{name}"],
            )
            written.append(pipeline_path)

            infrastructure_path = infrastructure_directory / f"{name}.json"
            infrastructure = {
                "dataset": bundle["resources"][f"dataset.{name}"],
                "storage": bundle["resources"][f"storage.{name}"],
                "monitor": bundle["resources"][f"monitor.{name}"],
            }
            self._write_json(infrastructure_path, infrastructure)
            written.append(infrastructure_path)
        return tuple(written)

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")

    @staticmethod
    def _dataset_resource(
        spec: DatasetSpec,
        spec_fingerprint: str,
    ) -> dict[str, Any]:
        return {
            "kind": "catalog_dataset",
            "name": spec.name,
            "domain": spec.domain,
            "owner": spec.owner,
            "description": spec.description,
            "classification": spec.classification,
            "schema": [field.to_dict() for field in spec.schema],
            "depends_on": [f"dataset.{name}" for name in spec.dependencies],
            "tags": list(spec.tags),
            "spec_fingerprint": spec_fingerprint,
        }

    @staticmethod
    def _pipeline_resource(
        spec: DatasetSpec,
        spec_fingerprint: str,
    ) -> dict[str, Any]:
        return {
            "kind": "batch_pipeline",
            "name": f"build_{spec.name}",
            "source": {
                "type": spec.source_type,
                "uri": spec.source_uri,
                "format": spec.source_format,
            },
            "target": f"dataset.{spec.name}",
            "depends_on": [f"pipeline.{name}" for name in spec.dependencies],
            "quality_gates": [rule.to_dict() for rule in spec.quality],
            "slo": {
                "freshness_minutes": spec.freshness_minutes,
                "availability_percentage": spec.availability_percentage,
            },
            "spec_fingerprint": spec_fingerprint,
        }

    @staticmethod
    def _storage_resource(
        spec: DatasetSpec,
        spec_fingerprint: str,
    ) -> dict[str, Any]:
        return {
            "kind": "object_storage",
            "name": spec.name,
            "location": (
                f"synthetic://managed/{spec.domain}/{spec.layer}/{spec.name}"
            ),
            "encryption": {"enabled": True, "key_management": "provider_managed_demo"},
            "access": {"owner_principal": spec.owner, "public_access": False},
            "lifecycle": {"retention_days": spec.retention_days},
            "partition_by": list(spec.partition_by),
            "spec_fingerprint": spec_fingerprint,
        }

    @staticmethod
    def _monitor_resource(
        spec: DatasetSpec,
        spec_fingerprint: str,
    ) -> dict[str, Any]:
        return {
            "kind": "dataset_monitor",
            "name": spec.name,
            "target": f"dataset.{spec.name}",
            "owner": spec.owner,
            "checks": {
                "freshness_minutes": spec.freshness_minutes,
                "availability_percentage": spec.availability_percentage,
                "quality_gate_count": len(spec.quality),
            },
            "spec_fingerprint": spec_fingerprint,
        }

