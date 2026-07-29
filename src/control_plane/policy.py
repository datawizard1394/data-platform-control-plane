"""Fail-closed onboarding policy gates across all dataset specs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .graph import DependencyCycleError, DependencyGraph
from .models import DatasetSpec, PolicyConfig

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
ALLOWED_FIELD_TYPES = {
    "string",
    "integer",
    "decimal",
    "boolean",
    "date",
    "timestamp",
}
ALLOWED_LAYERS = {"bronze", "silver", "gold"}
ALLOWED_QUALITY_RULES = {"not_null", "unique"}


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class PolicyGateError(ValueError):
    def __init__(self, violations: tuple[PolicyViolation, ...]) -> None:
        self.violations = violations
        super().__init__(f"{len(violations)} policy gate violation(s)")


def validate_specs(
    specs: dict[str, DatasetSpec],
    policy: PolicyConfig,
) -> tuple[PolicyViolation, ...]:
    violations: list[PolicyViolation] = []
    owner_pattern = re.compile(policy.owner_pattern)

    for name, spec in sorted(specs.items()):
        path = f"datasets.{name}"
        if spec.api_version != policy.required_api_version:
            violations.append(
                PolicyViolation(
                    "api_version",
                    f"{path}.api_version",
                    f"expected {policy.required_api_version!r}",
                )
            )
        if spec.kind != "Dataset":
            violations.append(
                PolicyViolation("kind", f"{path}.kind", "expected 'Dataset'")
            )
        if not IDENTIFIER.fullmatch(spec.name):
            violations.append(
                PolicyViolation("identifier", f"{path}.metadata.name", "invalid name")
            )
        if not owner_pattern.fullmatch(spec.owner):
            violations.append(
                PolicyViolation(
                    "ownership",
                    f"{path}.metadata.owner",
                    "owner must identify a team using the configured pattern",
                )
            )
        if not IDENTIFIER.fullmatch(spec.domain):
            violations.append(
                PolicyViolation("domain", f"{path}.metadata.domain", "invalid domain")
            )
        if len(spec.description.strip()) < 20:
            violations.append(
                PolicyViolation(
                    "description",
                    f"{path}.metadata.description",
                    "description must contain at least 20 characters",
                )
            )
        if not spec.synthetic or spec.production_deployment:
            violations.append(
                PolicyViolation(
                    "demo_provenance",
                    f"{path}.metadata",
                    "demo specs must be synthetic=true and production_deployment=false",
                )
            )
        if len(set(spec.tags)) != len(spec.tags):
            violations.append(
                PolicyViolation("duplicate_tags", f"{path}.metadata.tags", "tags must be unique")
            )

        if spec.source_type not in policy.allowed_source_types:
            violations.append(
                PolicyViolation(
                    "source_type",
                    f"{path}.source.type",
                    f"expected one of {sorted(policy.allowed_source_types)}",
                )
            )
        if spec.source_format not in policy.allowed_formats:
            violations.append(
                PolicyViolation(
                    "source_format",
                    f"{path}.source.format",
                    f"expected one of {sorted(policy.allowed_formats)}",
                )
            )
        if spec.source_type == "object_store" and not spec.source_uri.startswith(
            "synthetic://"
        ):
            violations.append(
                PolicyViolation(
                    "demo_source",
                    f"{path}.source.uri",
                    "object-store demo sources must use synthetic://",
                )
            )
        if spec.source_type == "dataset":
            expected_sources = {f"dataset://{dependency}" for dependency in spec.dependencies}
            if spec.source_uri not in expected_sources:
                violations.append(
                    PolicyViolation(
                        "source_dependency",
                        f"{path}.source.uri",
                        "dataset source must reference one declared dependency",
                    )
                )

        field_names = [field.name for field in spec.schema]
        if not field_names:
            violations.append(
                PolicyViolation("schema", f"{path}.schema", "at least one field is required")
            )
        if len(field_names) != len(set(field_names)):
            violations.append(
                PolicyViolation("duplicate_field", f"{path}.schema", "field names must be unique")
            )
        dataset_rank = policy.classification_rank.get(spec.classification)
        if dataset_rank is None:
            violations.append(
                PolicyViolation(
                    "classification",
                    f"{path}.classification.level",
                    f"expected one of {sorted(policy.classification_rank)}",
                )
            )
        for field in spec.schema:
            field_path = f"{path}.schema.{field.name}"
            if not IDENTIFIER.fullmatch(field.name):
                violations.append(
                    PolicyViolation("identifier", field_path, "invalid field name")
                )
            if field.data_type not in ALLOWED_FIELD_TYPES:
                violations.append(
                    PolicyViolation(
                        "field_type",
                        f"{field_path}.type",
                        f"expected one of {sorted(ALLOWED_FIELD_TYPES)}",
                    )
                )
            field_rank = policy.classification_rank.get(field.classification)
            if field_rank is None:
                violations.append(
                    PolicyViolation(
                        "classification",
                        f"{field_path}.classification",
                        f"expected one of {sorted(policy.classification_rank)}",
                    )
                )
            elif dataset_rank is not None and field_rank > dataset_rank:
                violations.append(
                    PolicyViolation(
                        "classification_rollup",
                        f"{field_path}.classification",
                        "field classification exceeds dataset classification",
                    )
                )

        if len(spec.pii_fields) != len(set(spec.pii_fields)):
            violations.append(
                PolicyViolation(
                    "duplicate_pii",
                    f"{path}.classification.pii_fields",
                    "PII fields must be unique",
                )
            )
        for pii_field in spec.pii_fields:
            if pii_field not in field_names:
                violations.append(
                    PolicyViolation(
                        "unknown_pii_field",
                        f"{path}.classification.pii_fields",
                        f"{pii_field!r} is not in the schema",
                    )
                )
            else:
                field = next(item for item in spec.schema if item.name == pii_field)
                field_rank = policy.classification_rank.get(field.classification, -1)
                confidential_rank = policy.classification_rank.get("confidential", 2)
                if field_rank < confidential_rank:
                    violations.append(
                        PolicyViolation(
                            "pii_classification",
                            f"{path}.classification.pii_fields",
                            f"{pii_field!r} must be confidential or restricted",
                        )
                    )
        if spec.pii_fields:
            confidential_rank = policy.classification_rank.get("confidential", 2)
            if dataset_rank is not None and dataset_rank < confidential_rank:
                violations.append(
                    PolicyViolation(
                        "pii_classification",
                        f"{path}.classification.level",
                        "a dataset with PII must be confidential or restricted",
                    )
                )

        retention_cap = policy.max_retention_days.get(spec.classification)
        if spec.retention_days <= 0:
            violations.append(
                PolicyViolation(
                    "retention",
                    f"{path}.retention.days",
                    "retention must be positive",
                )
            )
        elif retention_cap is not None and spec.retention_days > retention_cap:
            violations.append(
                PolicyViolation(
                    "retention",
                    f"{path}.retention.days",
                    f"exceeds {spec.classification} cap of {retention_cap} days",
                )
            )
        if len(spec.retention_reason.strip()) < 10:
            violations.append(
                PolicyViolation(
                    "retention_reason",
                    f"{path}.retention.reason",
                    "retention reason must be documented",
                )
            )

        if not 0 < spec.freshness_minutes <= policy.max_freshness_minutes:
            violations.append(
                PolicyViolation(
                    "freshness_slo",
                    f"{path}.slo.freshness_minutes",
                    f"must be in [1, {policy.max_freshness_minutes}]",
                )
            )
        if not (
            policy.minimum_availability_percentage
            <= spec.availability_percentage
            <= 100
        ):
            violations.append(
                PolicyViolation(
                    "availability_slo",
                    f"{path}.slo.availability_percentage",
                    (
                        f"must be in [{policy.minimum_availability_percentage}, 100]"
                    ),
                )
            )

        if len(set(spec.dependencies)) != len(spec.dependencies):
            violations.append(
                PolicyViolation(
                    "duplicate_dependency",
                    f"{path}.dependencies",
                    "dependencies must be unique",
                )
            )
        for dependency in spec.dependencies:
            if dependency == spec.name:
                violations.append(
                    PolicyViolation(
                        "self_dependency",
                        f"{path}.dependencies",
                        "a dataset cannot depend on itself",
                    )
                )
            elif dependency not in specs:
                violations.append(
                    PolicyViolation(
                        "unknown_dependency",
                        f"{path}.dependencies",
                        f"{dependency!r} is not defined",
                    )
                )

        if spec.layer not in ALLOWED_LAYERS:
            violations.append(
                PolicyViolation(
                    "layer",
                    f"{path}.delivery.layer",
                    f"expected one of {sorted(ALLOWED_LAYERS)}",
                )
            )
        for partition_field in spec.partition_by:
            if partition_field not in field_names:
                violations.append(
                    PolicyViolation(
                        "partition_field",
                        f"{path}.delivery.partition_by",
                        f"{partition_field!r} is not in the schema",
                    )
                )
        for index, rule in enumerate(spec.quality):
            rule_path = f"{path}.quality[{index}]"
            if rule.rule_type not in ALLOWED_QUALITY_RULES:
                violations.append(
                    PolicyViolation(
                        "quality_rule",
                        f"{rule_path}.type",
                        f"expected one of {sorted(ALLOWED_QUALITY_RULES)}",
                    )
                )
            if not rule.columns:
                violations.append(
                    PolicyViolation(
                        "quality_columns",
                        f"{rule_path}.columns",
                        "at least one column is required",
                    )
                )
            for column in rule.columns:
                if column not in field_names:
                    violations.append(
                        PolicyViolation(
                            "quality_column",
                            f"{rule_path}.columns",
                            f"{column!r} is not in the schema",
                        )
                    )

    try:
        DependencyGraph(specs).topological_order()
    except DependencyCycleError as error:
        violations.append(
            PolicyViolation(
                "dependency_cycle",
                "datasets",
                f"cycle includes {', '.join(error.nodes)}",
            )
        )
    return tuple(violations)


def require_policy_pass(specs: dict[str, DatasetSpec], policy: PolicyConfig) -> None:
    violations = validate_specs(specs, policy)
    if violations:
        raise PolicyGateError(violations)

