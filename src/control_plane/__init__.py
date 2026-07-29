"""Synthetic declarative data-platform control-plane reference."""

from .compiler import ManifestCompiler
from .graph import DependencyCycleError, DependencyGraph
from .models import DatasetSpec, PolicyConfig, load_specs
from .policy import PolicyViolation, validate_specs

__all__ = [
    "DatasetSpec",
    "DependencyCycleError",
    "DependencyGraph",
    "ManifestCompiler",
    "PolicyConfig",
    "PolicyViolation",
    "load_specs",
    "validate_specs",
]

__version__ = "0.1.0"

