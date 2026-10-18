"""Workflow storage, validation and deterministic DAG planning."""

from collections import defaultdict
from collections.abc import Iterable
import heapq

from .models import Task


class WorkflowValidationError(ValueError):
    """Raised when a workflow contains missing dependencies or a cycle."""


class Workflow:
    """A registry of uniquely named tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    @property
    def tasks(self) -> dict[str, Task]:
        """Return a shallow copy of the task registry."""
        return self._tasks.copy()

    def add_task(self, task: Task) -> None:
        """Register a task, rejecting duplicate names."""
        if not isinstance(task, Task):
            raise TypeError("task must be a Task instance.")
        if task.name in self._tasks:
            raise ValueError(f"A task named {task.name!r} is already registered.")
        self._tasks[task.name] = task

    def validate(self) -> None:
        """Check that all dependencies exist and that the graph is acyclic."""
        missing = sorted(
            (task.name, dependency)
            for task in self._tasks.values()
            for dependency in task.dependencies
            if dependency not in self._tasks
        )
        if missing:
            details = ", ".join(f"{task!r} depends on missing task {dep!r}" for task, dep in missing)
            raise WorkflowValidationError(f"Unregistered dependencies: {details}.")
        topological_order(self)


def _plan(workflow: Workflow) -> tuple[list[str], list[list[str]]]:
    if not isinstance(workflow, Workflow):
        raise TypeError("workflow must be a Workflow instance.")
    tasks = workflow.tasks
    missing = sorted(
        (task.name, dependency)
        for task in tasks.values()
        for dependency in task.dependencies
        if dependency not in tasks
    )
    if missing:
        details = ", ".join(f"{task!r} depends on missing task {dep!r}" for task, dep in missing)
        raise WorkflowValidationError(f"Unregistered dependencies: {details}.")

    indegree = {name: len(task.dependencies) for name, task in tasks.items()}
    dependents: dict[str, list[str]] = defaultdict(list)
    for name, task in tasks.items():
        for dependency in task.dependencies:
            dependents[dependency].append(name)
    for names in dependents.values():
        names.sort()

    ready = [name for name, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    order: list[str] = []
    layers: list[list[str]] = []
    while ready:
        current = [heapq.heappop(ready) for _ in range(len(ready))]
        layers.append(current)
        order.extend(current)
        next_ready: list[str] = []
        for name in current:
            for dependent in dependents[name]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    next_ready.append(dependent)
        ready = next_ready
        heapq.heapify(ready)

    if len(order) != len(tasks):
        cyclic = sorted(name for name, degree in indegree.items() if degree > 0)
        raise WorkflowValidationError(f"Workflow contains a cycle involving: {', '.join(cyclic)}.")
    return order, layers


def topological_order(workflow: Workflow) -> list[str]:
    """Return a deterministic topological order of task names."""
    return _plan(workflow)[0]


def execution_layers(workflow: Workflow) -> list[list[str]]:
    """Group task names into deterministic levels with satisfied dependencies."""
    return _plan(workflow)[1]
