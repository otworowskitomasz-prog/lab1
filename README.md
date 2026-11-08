# PyFlow

PyFlow to niewielka biblioteka dla Pythona 3.11+, kt�ra pozwala definiowa� workflowy danych, sprawdza� ich zale�no�ci i wykonywa� zadania synchronicznie.

## Instalacja

Utw�rz i aktywuj �rodowisko wirtualne, a nast�pnie zainstaluj pakiet wraz z zale�no�ciami deweloperskimi:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Uruchomienie workflowu

Funkcja zadania ma posta� `function(inputs, params)`. `inputs` zawiera wyniki wy��cznie bezpo�rednich zale�no�ci, pod kluczami b�d�cymi ich nazwami. `params` zawiera konfiguracj� zadania.

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

Silnik najpierw waliduje workflow, a nast�pnie korzysta z planera topologicznego z Laboratorium 1. Pusty workflow zwraca poprawny wynik z pustymi mapami.

## Wynik i statusy

`RunResult` udost�pnia:

- `outputs` - mapowanie nazw zada� na ich wyniki;
- `task_states` - mapowanie nazw zada� na `TaskState` z polem `status`, czasem startu i ko�ca, `duration_seconds`, wynikiem oraz ewentualnym b��dem;
- `duration_seconds` - czas ca�ego przebiegu;
- `succeeded` - informacj�, czy wszystkie zadania zako�czy�y si� powodzeniem.

Statusy zadania to `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED` i `SKIPPED`. Czasy s� mierzone monotonicznym zegarem `time.perf_counter`.

## Polityka b��d�w

Po b��dzie zadania silnik oznacza je jako `FAILED`, pomija jego zadania zale�ne, a niezale�ne zadania wykonuje dalej. Po przej�ciu planu zg�asza `TaskExecutionError` dla pierwszej awarii; oryginalny wyj�tek jest dost�pny jako `__cause__`, a kompletny raport przebiegu jako `error.result`.

```python
from pyflow import TaskExecutionError, run

try:
    result = run(workflow)
except TaskExecutionError as error:
    print(error.task_name)
    print(error.result.task_states)
    print(error.__cause__)
```

## Przyk�ad CSV -> JSON

Przyk�adowy workflow odczytuje `examples/data/sales.csv`, odrzuca niepoprawne rekordy, agreguje kwoty wed�ug kategorii i zapisuje `examples/output/report.json`. Dane s� lokalne, a przyk�ad nie korzysta z sieci.

```bash
python examples/end_to_end.py
```

Skrypt wypisuje �cie�k� raportu oraz czas wykonania ka�dego zadania i ca�ego workflowu.

## Testy

```bash
python -m pytest
```

Testy obejmuj� przep�yw wynik�w i parametr�w, kolejno�� wykonania, pusty workflow, obs�ug� awarii i pomijanie zale�nych zada�, wykonanie niezale�nych zada� oraz przyk�ad CSV -> JSON.

## Algorytm planowania

Planowanie wykorzystuje algorytm sortowania topologicznego Kahna. Kopiec minimalny wybiera gotowe zadania w kolejno�ci alfabetycznej, dzi�ki czemu wynik jest deterministyczny. Warstwy wykonania grupuj� zadania gotowe na tym samym poziomie. Z�o�ono�� czasowa wynosi `O((V + E) log V)`, a pami�ciowa `O(V + E)`, gdzie `V` oznacza liczb� zada�, a `E` liczb� zale�no�ci. Brakuj�ce zale�no�ci i cykle powoduj� wyj�tek `WorkflowValidationError` z komunikatem diagnostycznym.
