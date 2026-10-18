import pytest

from pyflow import Task, Workflow, WorkflowValidationError, execution_layers, topological_order


def task(name: str, *dependencies: str) -> Task:
    return Task(name, lambda inputs, params: None, frozenset(dependencies))


def test_empty_workflow() -> None:
    workflow = Workflow()
    workflow.validate()
    assert topological_order(workflow) == []
    assert execution_layers(workflow) == []


def test_single_task_and_chain() -> None:
    workflow = Workflow()
    workflow.add_task(task("source"))
    workflow.add_task(task("clean", "source"))
    workflow.add_task(task("report", "clean"))
    assert topological_order(workflow) == ["source", "clean", "report"]
    assert execution_layers(workflow) == [["source"], ["clean"], ["report"]]


def test_independent_tasks_are_sorted_deterministically() -> None:
    workflow = Workflow()
    for name in ("zeta", "alpha", "middle"):
        workflow.add_task(task(name))
    assert topological_order(workflow) == ["alpha", "middle", "zeta"]
    assert execution_layers(workflow) == [["alpha", "middle", "zeta"]]


def test_layers_group_ready_tasks_then_join() -> None:
    workflow = Workflow()
    workflow.add_task(task("report", "clean_b", "clean_a"))
    workflow.add_task(task("clean_b", "extract"))
    workflow.add_task(task("clean_a", "extract"))
    workflow.add_task(task("extract"))
    assert execution_layers(workflow) == [["extract"], ["clean_a", "clean_b"], ["report"]]


def test_validate_rejects_missing_dependency() -> None:
    workflow = Workflow()
    workflow.add_task(task("consumer", "missing"))
    with pytest.raises(WorkflowValidationError, match="consumer.*missing"):
        workflow.validate()


def test_validate_rejects_cycle() -> None:
    workflow = Workflow()
    workflow.add_task(task("first", "second"))
    workflow.add_task(task("second", "first"))
    with pytest.raises(WorkflowValidationError, match="cycle"):
        workflow.validate()
    with pytest.raises(WorkflowValidationError, match="cycle"):
        topological_order(workflow)
