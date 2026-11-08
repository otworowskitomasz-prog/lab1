# PyFlow

PyFlow to niewielka biblioteka dla Pythona 3.11+, która pozwala definiować workflowy danych, sprawdzać ich zależności i wykonywać zadania synchronicznie.

## Instalacja

Utwórz i aktywuj środowisko wirtualne, a następnie zainstaluj pakiet wraz z zależnościami deweloperskimi:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Uruchomienie workflowu

Funkcja zadania ma postać `function(inputs, params)`. `inputs` zawiera wyniki wyłącznie bezpośrednich zależności, pod kluczami będącymi ich nazwami. `params` zawiera konfigurację zadania.

```python
from pyflow import Task, Workflow, run

workflow = Workflow()
workflow.add_task(Task("liczby", lambda inputs, params: [2, 3, 5]))
workflow.add_task(Task(
    "suma",
    lambda inputs, params: sum(inputs["liczby"]) + params["offset"],
    dependencies=frozenset({"liczby"}),
    params={"offset": 1},
))

result = run(workflow)
print(result.outputs["suma"])  # 11
print(result.succeeded)        # True
```

Silnik najpierw waliduje workflow, a następnie korzysta z planera topologicznego z Laboratorium 1. Pusty workflow zwraca poprawny wynik z pustymi mapami.

## Wynik i statusy

`RunResult` udostępnia:

- `outputs` - mapowanie nazw zadań na ich wyniki;
- `task_states` - mapowanie nazw zadań na `TaskState` z polem `status`, czasem startu i końca, `duration_seconds`, wynikiem oraz ewentualnym błędem;
- `duration_seconds` - czas całego przebiegu;
- `succeeded` - informację, czy wszystkie zadania zakończyły się powodzeniem.

Statusy zadania to `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED` i `SKIPPED`. Czasy są mierzone monotonicznym zegarem `time.perf_counter`.

## Polityka błędów

Po błędzie zadania silnik oznacza je jako `FAILED`, pomija jego zadania zależne, a niezależne zadania wykonuje dalej. Po przejściu planu zgłasza `TaskExecutionError` dla pierwszej awarii; oryginalny wyjątek jest dostępny jako `__cause__`, a kompletny raport przebiegu jako `error.result`.

```python
from pyflow import TaskExecutionError, run

try:
    result = run(workflow)
except TaskExecutionError as error:
    print(error.task_name)
    print(error.result.task_states)
    print(error.__cause__)
```

## Przykład CSV -> JSON

Przykładowy workflow odczytuje `examples/data/sales.csv`, odrzuca niepoprawne rekordy, agreguje kwoty według kategorii i zapisuje `examples/output/report.json`. Dane są lokalne, a przykład nie korzysta z sieci.

```bash
python examples/end_to_end.py
```

Skrypt wypisuje ścieżkę raportu oraz czas wykonania każdego zadania i całego workflowu.

## Testy

```bash
python -m pytest
```

Testy obejmują przepływ wyników i parametrów, kolejność wykonania, pusty workflow, obsługę awarii i pomijanie zależnych zadań, wykonanie niezależnych zadań oraz przykład CSV -> JSON.

## Algorytm planowania

Planowanie wykorzystuje algorytm sortowania topologicznego Kahna. Kopiec minimalny wybiera gotowe zadania w kolejności alfabetycznej, dzięki czemu wynik jest deterministyczny. Warstwy wykonania grupują zadania gotowe na tym samym poziomie. Złożoność czasowa wynosi `O((V + E) log V)`, a pamięciowa `O(V + E)`, gdzie `V` oznacza liczbę zadań, a `E` liczbę zależności. Brakujące zależności i cykle powodują wyjątek `WorkflowValidationError` z komunikatem diagnostycznym.

