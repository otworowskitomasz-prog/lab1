# PyFlow

PyFlow to niewielka biblioteka dla Pythona 3.11+, która pozwala definiować zadania przetwarzania danych, sprawdzać ich zależności i wyznaczać deterministyczny plan wykonania.

## Instalacja

Utwórz i aktywuj środowisko wirtualne, a następnie zainstaluj pakiet wraz z zależnościami deweloperskimi:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Przykład

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

Funkcja zadania przyjmuje dwa mapowania: wyniki bezpośrednich zależności (`inputs`) oraz skonfigurowane parametry (`params`). Parametry i zależności są kopiowane przy tworzeniu zadania, więc późniejsze zmiany w danych źródłowych nie zmieniają jego konfiguracji.

## Testy

```bash
python -m pytest
```

## Algorytm planowania

Planowanie wykorzystuje algorytm sortowania topologicznego Kahna. Kopiec minimalny wybiera gotowe zadania w kolejności alfabetycznej, dzięki czemu wynik jest deterministyczny. Warstwy wykonania grupują zadania gotowe na tym samym poziomie. Złożoność czasowa wynosi `O((V + E) log V)`, a pamięciowa `O(V + E)`, gdzie `V` oznacza liczbę zadań, a `E` liczbę zależności. Brakujące zależności i cykle powodują wyjątek `WorkflowValidationError` z komunikatem diagnostycznym.

