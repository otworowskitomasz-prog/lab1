# PyFlow

PyFlow is a small Python 3.11+ library for describing data tasks, validating their dependency graph, and building deterministic execution plans.

## Install

Create and activate a virtual environment, then install the package with its development dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Example

```python
from pyflow import Task, Workflow, execution_layers, topological_order

workflow = Workflow()
workflow.add_task(Task("extract", lambda inputs, params: [1, 2, 3]))
workflow.add_task(Task(
    "total",
    lambda inputs, params: sum(inputs["extract"]),
    dependencies=frozenset({"extract"}),
))

workflow.validate()
print(topological_order(workflow))  # ['extract', 'total']
print(execution_layers(workflow))   # [['extract'], ['total']]
```

A task function accepts two mappings: results from its direct dependencies (`inputs`) and its configured `params`. Task parameters and dependencies are snapshotted when the task is created.

## Tests

```bash
python -m pytest
```

## Planning algorithm

Planning uses Kahn's topological-sort algorithm. A min-heap selects ready tasks alphabetically, making the result stable. Execution layers contain all tasks ready at the same depth. The running time is `O((V + E) log V)` with heap ordering, and memory use is `O(V + E)`, where `V` is the number of tasks and `E` is the number of dependencies. Missing dependencies and cycles raise `WorkflowValidationError` with a diagnostic message.

