"""Workflow task models."""

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeAlias

TaskFunction: TypeAlias = Callable[[Mapping[str, Any], Mapping[str, Any]], Any]


@dataclass(frozen=True, slots=True)
class Task:
    """A named computation and the tasks whose results it consumes."""

    name: str
    function: TaskFunction
    dependencies: frozenset[str] = field(default_factory=frozenset)
    params: Mapping[str, Any] = field(default_factory=dict)
    description: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Task name must be a non-empty string.")
        if not callable(self.function):
            raise TypeError("Task function must be callable.")
        dependencies = frozenset(self.dependencies)
        if any(not isinstance(name, str) or not name.strip() for name in dependencies):
            raise ValueError("Dependency names must be non-empty strings.")
        if self.name in dependencies:
            raise ValueError(f"Task {self.name!r} cannot depend on itself.")
        if not isinstance(self.params, Mapping):
            raise TypeError("Task params must be a mapping.")
        object.__setattr__(self, "dependencies", dependencies)
        # Snapshot the caller's mapping so later mutations cannot alter task configuration.
        object.__setattr__(self, "params", MappingProxyType(deepcopy(dict(self.params))))
