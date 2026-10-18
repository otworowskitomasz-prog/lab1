from pyflow import Task, Workflow


def make_task(name: str, dependencies: set[str] | frozenset[str] = frozenset()) -> Task:
    return Task(name, lambda inputs, params: None, frozenset(dependencies))


def test_task_snapshots_params_and_dependencies() -> None:
    params = {"threshold": 3}
    dependencies = {"source"}
    task = Task("clean", lambda inputs, params: None, dependencies, params)
    params["threshold"] = 9
    dependencies.add("later")
    assert task.params["threshold"] == 3
    assert task.dependencies == frozenset({"source"})


def test_task_rejects_empty_name_and_self_dependency() -> None:
    import pytest
    with pytest.raises(ValueError, match="non-empty"):
        make_task(" ")
    with pytest.raises(ValueError, match="depend on itself"):
        make_task("same", {"same"})


def test_add_task_rejects_duplicates_and_registry_is_copied() -> None:
    import pytest
    workflow = Workflow()
    workflow.add_task(make_task("one"))
    with pytest.raises(ValueError, match="already registered"):
        workflow.add_task(make_task("one"))
    copied = workflow.tasks
    copied.clear()
    assert "one" in workflow.tasks
