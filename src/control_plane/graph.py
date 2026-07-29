"""Dependency DAG validation, ordering, and rendering."""

from __future__ import annotations

import re
from collections import defaultdict

from .models import DatasetSpec


class DependencyCycleError(ValueError):
    def __init__(self, nodes: tuple[str, ...]) -> None:
        self.nodes = nodes
        super().__init__(f"dependency cycle detected among: {', '.join(nodes)}")


class DependencyGraph:
    def __init__(self, specs: dict[str, DatasetSpec]) -> None:
        self.specs = specs

    def topological_order(self) -> tuple[str, ...]:
        indegree = {name: 0 for name in self.specs}
        dependents: dict[str, list[str]] = defaultdict(list)
        for name, spec in self.specs.items():
            for dependency in spec.dependencies:
                if dependency in self.specs:
                    indegree[name] += 1
                    dependents[dependency].append(name)

        ready = sorted(name for name, degree in indegree.items() if degree == 0)
        order: list[str] = []
        while ready:
            current = ready.pop(0)
            order.append(current)
            for dependent in sorted(dependents[current]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()
        if len(order) != len(self.specs):
            cyclic = tuple(sorted(name for name, degree in indegree.items() if degree > 0))
            raise DependencyCycleError(cyclic)
        return tuple(order)

    def to_dict(self) -> dict[str, object]:
        edges = sorted(
            (dependency, name)
            for name, spec in self.specs.items()
            for dependency in spec.dependencies
        )
        return {
            "nodes": sorted(self.specs),
            "edges": [
                {"upstream": upstream, "downstream": downstream}
                for upstream, downstream in edges
            ],
            "deployment_order": list(self.topological_order()),
        }

    def to_mermaid(self) -> str:
        def node_id(value: str) -> str:
            return re.sub(r"[^A-Za-z0-9_]", "_", value)

        lines = ["flowchart LR"]
        for name in sorted(self.specs):
            spec = self.specs[name]
            lines.append(
                f'    {node_id(name)}["{name}<br/>{spec.layer} · {spec.classification}"]'
            )
        for name, spec in sorted(self.specs.items()):
            for dependency in sorted(spec.dependencies):
                lines.append(f"    {node_id(dependency)} --> {node_id(name)}")
        return "\n".join(lines)

