import json
from pathlib import Path
from typing import Any

import pytest

from examples.end_to_end import build_workflow
from pyflow import RunResult, Task, TaskExecutionError, TaskStatus, Workflow, run


def test_run_passes_direct_dependency_results_and_params_in_order() -> None:
    workflow = Workflow()
    seen: list[str] = []
    join_inputs: dict[str, Any] = {}
    workflow.add_task(Task("source", lambda inputs, params: seen.append("source") or 4))
    workflow.add_task(Task("left", lambda inputs, params: seen.append("left") or inputs["source"] + params["offset"], {"source"}, {"offset": 2}))
    workflow.add_task(Task("right", lambda inputs, params: seen.append("right") or inputs["source"] * 3, {"source"}))

    def join(inputs: dict[str, Any], params: dict[str, Any]) -> int:
        join_inputs.update(inputs)
        seen.append("join")
        return sum(inputs.values())

    workflow.add_task(Task("join", join, {"left", "right"}))

    result = run(workflow)

    assert seen == ["source", "left", "right", "join"]
    assert join_inputs == {"left": 6, "right": 12}
    assert result.outputs == {"source": 4, "left": 6, "right": 12, "join": 18}
    assert result.task_states["join"].status is TaskStatus.SUCCEEDED
    assert result.task_states["join"].started_at is not None
    assert result.task_states["join"].finished_at is not None
    assert result.task_states["join"].duration_seconds >= 0
    assert result.duration_seconds >= 0
    assert result.succeeded


def test_run_of_empty_workflow_succeeds() -> None:
    result = run(Workflow())

    assert isinstance(result, RunResult)
    assert result.succeeded
    assert result.outputs == {}
    assert result.task_states == {}


def test_failure_skips_dependents_but_continues_independent_tasks() -> None:
    workflow = Workflow()
    independent_ran: list[bool] = []

    def fail(inputs: dict[str, Any], params: dict[str, Any]) -> None:
        raise ValueError("bad input")

    workflow.add_task(Task("broken", fail))
    workflow.add_task(Task("dependent", lambda inputs, params: "should not run", {"broken"}))
    workflow.add_task(Task("downstream", lambda inputs, params: "should not run", {"dependent"}))
    workflow.add_task(Task("independent", lambda inputs, params: independent_ran.append(True) or 9))

    with pytest.raises(TaskExecutionError, match="broken") as raised:
        run(workflow)

    error = raised.value
    assert isinstance(error.__cause__, ValueError)
    assert str(error.__cause__) == "bad input"
    assert error.task_name == "broken"
    assert error.original_error is error.__cause__
    assert isinstance(error.result, RunResult)
    assert not error.result.succeeded
    assert error.result.task_states["broken"].status is TaskStatus.FAILED
    assert error.result.task_states["dependent"].status is TaskStatus.SKIPPED
    assert error.result.task_states["downstream"].status is TaskStatus.SKIPPED
    assert error.result.task_states["independent"].status is TaskStatus.SUCCEEDED
    assert error.result.outputs == {"independent": 9}
    assert independent_ran == [True]


def test_csv_to_json_example_runs_end_to_end(tmp_path: Path) -> None:
    csv_path = tmp_path / "sales.csv"
    json_path = tmp_path / "output" / "report.json"
    csv_path.write_text(
        "name,category,amount\nA,books,12.5\nB,books,7.5\nC,games,20\nD,games,-3\nE,,5\n",
        encoding="utf-8",
    )

    result = run(build_workflow(csv_path, json_path))

    assert json.loads(json_path.read_text(encoding="utf-8")) == {
        "record_count": 3,
        "totals_by_category": {"books": 20.0, "games": 20.0},
    }
    assert result.succeeded
    assert list(result.task_states) == ["read_csv", "clean_records", "aggregate", "write_json"]
    assert result.outputs["write_json"] == str(json_path)
