"""Local CSV-to-JSON example for the synchronous PyFlow engine."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyflow import Task, Workflow, run


def _read_csv(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> list[dict[str, str]]:
    with Path(params["csv_path"]).open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def _clean_records(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for row in inputs["read_csv"]:
        name = row["name"].strip()
        category = row["category"].strip()
        try:
            amount = float(row["amount"])
        except (TypeError, ValueError):
            continue
        if name and category and amount >= 0:
            cleaned.append({"name": name, "category": category, "amount": amount})
    return cleaned


def _aggregate(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> dict[str, Any]:
    totals: dict[str, float] = defaultdict(float)
    records = inputs["clean_records"]
    for record in records:
        totals[record["category"]] += record["amount"]
    return {
        "record_count": len(records),
        "totals_by_category": {category: totals[category] for category in sorted(totals)},
    }


def _write_json(inputs: Mapping[str, Any], params: Mapping[str, Any]) -> str:
    report = json.dumps(inputs["aggregate"], ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_path = Path(params["json_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return str(output_path)


def build_workflow(csv_path: Path, json_path: Path) -> Workflow:
    """Build the four-step local data workflow."""
    workflow = Workflow()
    workflow.add_task(Task("read_csv", _read_csv, params={"csv_path": str(csv_path)}))
    workflow.add_task(Task("clean_records", _clean_records, frozenset({"read_csv"})))
    workflow.add_task(Task("aggregate", _aggregate, frozenset({"clean_records"})))
    workflow.add_task(Task("write_json", _write_json, frozenset({"aggregate"}), {"json_path": str(json_path)}))
    return workflow


def main() -> None:
    example_dir = Path(__file__).resolve().parent
    output_path = example_dir / "output" / "report.json"
    result = run(build_workflow(example_dir / "data" / "sales.csv", output_path))
    print(f"Raport zapisano w: {result.outputs['write_json']}")
    print(f"Czas przebiegu: {result.duration_seconds:.6f} s")
    for name, state in result.task_states.items():
        print(f"{name}: {state.status.value} ({state.duration_seconds:.6f} s)")


if __name__ == "__main__":
    main()
