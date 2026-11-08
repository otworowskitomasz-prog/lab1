"""Synchronous execution engine for validated workflows."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any
import time

from .graph import Workflow, topological_order


class TaskStatus(str, Enum):
    """Lifecycle status of one task in a workflow run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class TaskState:
    """Status, timing, output, and optional error for one task."""

    status: TaskStatus = TaskStatus.PENDING
    started_at: float | None = None
    finished_at: float | None = None
    duration_seconds: float = 0.0
    output: Any = None
    error: Exception | None = None


@dataclass(frozen=True, slots=True)
class RunResult:
    """Machine-readable summary of a workflow execution."""

    outputs: Mapping[str, Any] = field(default_factory=dict)
    task_states: Mapping[str, TaskState] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))
        object.__setattr__(self, "task_states", MappingProxyType(dict(self.task_states)))

    @property
    def succeeded(self) -> bool:
        """Whether every task completed successfully (true for an empty workflow)."""
        return all(state.status is TaskStatus.SUCCEEDED for state in self.task_states.values())


class TaskExecutionError(RuntimeError):
    """Raised after a failed run, with its task name and complete run report."""

    def __init__(self, task_name: str, result: RunResult) -> None:
        self.task_name = task_name
        self.result = result
        failed_state = result.task_states[task_name]
        self.original_error = failed_state.error
        super().__init__(f"Task {task_name!r} failed: {failed_state.error}")


def run(workflow: Workflow) -> RunResult:
    """Execute tasks in topological order and return their outputs and states.

    When a task fails, its descendants are skipped while independent tasks keep
    running. After the plan has been processed, the first failure is raised as
    ``TaskExecutionError``; its ``result`` attribute contains the full report.
    """
    workflow.validate()
    order = topological_order(workflow)
    tasks = workflow.tasks
    run_started = time.perf_counter()
    states = {name: TaskState() for name in order}
    outputs: dict[str, Any] = {}
    first_failure: tuple[str, Exception] | None = None

    for name in order:
        task = tasks[name]
        if any(states[dependency].status is not TaskStatus.SUCCEEDED for dependency in task.dependencies):
            states[name] = TaskState(
                status=TaskStatus.SKIPPED,
                finished_at=time.perf_counter(),
            )
            continue

        started = time.perf_counter()
        states[name] = TaskState(status=TaskStatus.RUNNING, started_at=started)
        inputs = {dependency: outputs[dependency] for dependency in sorted(task.dependencies)}
        try:
            output = task.function(inputs, task.params)
        except Exception as exc:
            finished = time.perf_counter()
            states[name] = TaskState(
                status=TaskStatus.FAILED,
                started_at=started,
                finished_at=finished,
                duration_seconds=finished - started,
                error=exc,
            )
            if first_failure is None:
                first_failure = (name, exc)
        else:
            finished = time.perf_counter()
            outputs[name] = output
            states[name] = TaskState(
                status=TaskStatus.SUCCEEDED,
                started_at=started,
                finished_at=finished,
                duration_seconds=finished - started,
                output=output,
            )

    result = RunResult(
        outputs=outputs,
        task_states=states,
        duration_seconds=time.perf_counter() - run_started,
    )
    if first_failure is not None:
        failed_name, original_error = first_failure
        raise TaskExecutionError(failed_name, result) from original_error
    return result
