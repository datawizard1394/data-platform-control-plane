"""Typed dataset onboarding specs and policy configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    data_type: str
    nullable: bool
    classification: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.data_type,
            "nullable": self.nullable,
            "classification": self.classification,
        }


@dataclass(frozen=True, slots=True)
class QualityRule:
    rule_type: str
    columns: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.rule_type, "columns": list(self.columns)}


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    api_version: str
    kind: str
    name: str
    owner: str
    domain: str
    description: str
    synthetic: bool
    production_deployment: bool
    tags: tuple[str, ...]
    source_type: str
    source_uri: str
    source_format: str
    schema: tuple[Field, ...]
    classification: str
    pii_fields: tuple[str, ...]
    retention_days: int
    retention_reason: str
    freshness_minutes: int
    availability_percentage: float
    dependencies: tuple[str, ...]
    layer: str
    partition_by: tuple[str, ...]
    quality: tuple[QualityRule, ...]

    @classmethod
    def load(cls, path: str | Path) -> DatasetSpec:
        with Path(path).open(encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError(f"spec must be a JSON object: {path}")
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DatasetSpec:
        metadata = raw.get("metadata", {})
        source = raw.get("source", {})
        classification = raw.get("classification", {})
        retention = raw.get("retention", {})
        slo = raw.get("slo", {})
        delivery = raw.get("delivery", {})
        return cls(
            api_version=str(raw.get("api_version", "")),
            kind=str(raw.get("kind", "")),
            name=str(metadata.get("name", "")),
            owner=str(metadata.get("owner", "")),
            domain=str(metadata.get("domain", "")),
            description=str(metadata.get("description", "")),
            synthetic=bool(metadata.get("synthetic", False)),
            production_deployment=bool(metadata.get("production_deployment", False)),
            tags=tuple(metadata.get("tags", [])),
            source_type=str(source.get("type", "")),
            source_uri=str(source.get("uri", "")),
            source_format=str(source.get("format", "")),
            schema=tuple(
                Field(
                    name=str(field.get("name", "")),
                    data_type=str(field.get("type", "")),
                    nullable=bool(field.get("nullable", False)),
                    classification=str(field.get("classification", "")),
                )
                for field in raw.get("schema", [])
            ),
            classification=str(classification.get("level", "")),
            pii_fields=tuple(classification.get("pii_fields", [])),
            retention_days=int(retention.get("days", 0)),
            retention_reason=str(retention.get("reason", "")),
            freshness_minutes=int(slo.get("freshness_minutes", 0)),
            availability_percentage=float(slo.get("availability_percentage", 0)),
            dependencies=tuple(raw.get("dependencies", [])),
            layer=str(delivery.get("layer", "")),
            partition_by=tuple(delivery.get("partition_by", [])),
            quality=tuple(
                QualityRule(
                    rule_type=str(rule.get("type", "")),
                    columns=tuple(rule.get("columns", [])),
                )
                for rule in raw.get("quality", [])
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "api_version": self.api_version,
            "kind": self.kind,
            "metadata": {
                "name": self.name,
                "owner": self.owner,
                "domain": self.domain,
                "description": self.description,
                "synthetic": self.synthetic,
                "production_deployment": self.production_deployment,
                "tags": list(self.tags),
            },
            "source": {
                "type": self.source_type,
                "uri": self.source_uri,
                "format": self.source_format,
            },
            "schema": [field.to_dict() for field in self.schema],
            "classification": {
                "level": self.classification,
                "pii_fields": list(self.pii_fields),
            },
            "retention": {
                "days": self.retention_days,
                "reason": self.retention_reason,
            },
            "slo": {
                "freshness_minutes": self.freshness_minutes,
                "availability_percentage": self.availability_percentage,
            },
            "dependencies": list(self.dependencies),
            "delivery": {
                "layer": self.layer,
                "partition_by": list(self.partition_by),
            },
            "quality": [rule.to_dict() for rule in self.quality],
        }


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    policy_version: str
    required_api_version: str
    owner_pattern: str
    allowed_source_types: tuple[str, ...]
    allowed_formats: tuple[str, ...]
    classification_rank: dict[str, int]
    max_retention_days: dict[str, int]
    max_freshness_minutes: int
    minimum_availability_percentage: float

    @classmethod
    def load(cls, path: str | Path) -> PolicyConfig:
        with Path(path).open(encoding="utf-8") as handle:
            raw = json.load(handle)
        return cls(
            policy_version=str(raw.get("policy_version", "")),
            required_api_version=str(raw.get("required_api_version", "")),
            owner_pattern=str(raw.get("owner_pattern", "")),
            allowed_source_types=tuple(raw.get("allowed_source_types", [])),
            allowed_formats=tuple(raw.get("allowed_formats", [])),
            classification_rank={
                str(name): int(rank)
                for name, rank in raw.get("classification_rank", {}).items()
            },
            max_retention_days={
                str(name): int(days)
                for name, days in raw.get("max_retention_days", {}).items()
            },
            max_freshness_minutes=int(raw.get("max_freshness_minutes", 0)),
            minimum_availability_percentage=float(
                raw.get("minimum_availability_percentage", 0)
            ),
        )


def load_specs(directory: str | Path) -> dict[str, DatasetSpec]:
    specs: dict[str, DatasetSpec] = {}
    paths = sorted(Path(directory).glob("*.json"))
    if not paths:
        raise ValueError(f"no JSON specs found in {directory}")
    for path in paths:
        spec = DatasetSpec.load(path)
        if spec.name in specs:
            raise ValueError(f"duplicate dataset name {spec.name!r}")
        specs[spec.name] = spec
    return dict(sorted(specs.items()))

