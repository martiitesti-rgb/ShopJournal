"""Reproduce the frozen RQ1 aggregate from original queries and admission decisions."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


BUNDLE = Path(__file__).resolve().parent
sys.path.insert(0, str(BUNDLE))

from final_evaluation.cues import extract_cues


CATEGORIES = ("DIET", "GIFT", "URGENCY", "BUDGET")
QUERY_FIELDS = (
    "opaque_slot_id",
    "Query",
    "top_subcategories",
    "intended_semantic_cue_assignment",
    "explicit_numeric_budget_required",
)
ADMISSION_FIELDS = ("opaque_slot_id", "authoring_admission", "reason")


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path, delimiter=","):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=delimiter)
        rows = list(reader)
    return tuple(reader.fieldnames or ()), rows


def cue_set(value):
    if value == "CUE_FREE":
        return set()
    parts = value.split("+")
    if len(parts) != len(set(parts)) or not set(parts) <= set(CATEGORIES):
        raise ValueError("Invalid intended cue assignment")
    return set(parts)


def metric_row(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "support": tp + fn,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
    }


def compute_rq1(rows):
    admitted = [row for row in rows if row["authoring_admission"] == "passed"]
    if not admitted:
        raise ValueError("No semantically admitted RQ1 rows")
    per_category = {}
    for category in CATEGORIES:
        tp = sum(category in row["intended"] and category in row["detected"] for row in admitted)
        fp = sum(category not in row["intended"] and category in row["detected"] for row in admitted)
        fn = sum(category in row["intended"] and category not in row["detected"] for row in admitted)
        per_category[category] = metric_row(tp, fp, fn)
    exact = sum(row["intended"] == row["detected"] for row in admitted)
    cue_free = [row for row in admitted if not row["intended"]]
    cue_free_fp = sum(bool(row["detected"]) for row in cue_free)
    failures = len(rows) - len(admitted)
    return {
        "counts": {
            "total": len(rows),
            "authoring_admission_passed": len(admitted),
            "authoring_admission_failed": failures,
            "authoring_failure_proportion": failures / len(rows),
        },
        "exact_set": {
            "matches": exact,
            "support": len(admitted),
            "accuracy": exact / len(admitted),
        },
        "per_category": per_category,
        "micro": metric_row(*(sum(row[key] for row in per_category.values()) for key in ("tp", "fp", "fn"))),
        "macro": {
            key: sum(row[key] for row in per_category.values()) / len(CATEGORIES)
            for key in ("precision", "recall", "f1")
        },
        "cue_free": {
            "support": len(cue_free),
            "false_positive_queries": cue_free_fp,
            "false_positive_rate": cue_free_fp / len(cue_free) if cue_free else 0.0,
        },
        "zero_denominator_precision_recall": 0,
        "macro_category_count": len(CATEGORIES),
        "primary_population": "semantically admitted original first versions only",
        "failed_authoring_rows_counted_as_extractor_errors": False,
    }


def reproduce():
    query_path = BUNDLE / "rq1_first_versions.csv"
    admission_path = BUNDLE / "rq1_authoring_admission.csv"
    run_path = BUNDLE / "rq1_run_v1.json"
    frozen_result_path = BUNDLE / "rq1_result_v1.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))

    if file_sha256(query_path) != run["input_sha256"]["rq1_first_versions.csv"]:
        raise ValueError("RQ1 input hash differs from the frozen run record")
    for name in ("__init__.py", "lexical.py", "cues.py"):
        if file_sha256(BUNDLE / "final_evaluation" / name) != run["source_sha256"][name]:
            raise ValueError(f"Frozen source hash mismatch: {name}")

    query_fields, queries = read_csv(query_path, ";")
    admission_fields, admissions = read_csv(admission_path)
    if query_fields != QUERY_FIELDS or admission_fields != ADMISSION_FIELDS:
        raise ValueError("Unexpected reproduction input schema")
    if len(queries) != 40 or len(admissions) != 40:
        raise ValueError("Expected exactly 40 RQ1 rows")
    if [row["opaque_slot_id"] for row in queries] != [row["opaque_slot_id"] for row in admissions]:
        raise ValueError("RQ1 query/admission ID binding mismatch")
    if len({row["opaque_slot_id"] for row in queries}) != 40:
        raise ValueError("RQ1 opaque IDs are not unique")

    rows = []
    for query, admission in zip(queries, admissions):
        status = admission["authoring_admission"]
        if status not in {"passed", "failed"}:
            raise ValueError("Invalid authoring-admission status")
        if (status == "failed") != bool(admission["reason"]):
            raise ValueError("Only failed authoring rows may carry a reason")
        extracted = extract_cues(query["Query"])
        rows.append({
            "intended": cue_set(query["intended_semantic_cue_assignment"]),
            "detected": set(extracted.detected),
            "authoring_admission": status,
        })

    rq1 = compute_rq1(rows)
    if rq1["counts"] != run["counts"]:
        raise ValueError("Authoring-admission counts differ from the frozen run record")
    reproduced = {
        "input_sha256": dict(run["input_sha256"]),
        "repository_sha": run["repository_sha"],
        "rq1": rq1,
        "schema_version": run["schema_version"],
    }
    return reproduced, json.loads(frozen_result_path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Fail unless the reproduced result equals rq1_result_v1.json.")
    args = parser.parse_args()
    try:
        reproduced, frozen = reproduce()
        if args.verify and reproduced != frozen:
            raise ValueError("Reproduced aggregate does not equal the frozen RQ1 result")
    except Exception as exc:
        raise SystemExit(f"implementation_config_blocker: {exc}") from exc
    print(json.dumps(reproduced, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    if args.verify:
        print("VERIFIED: reproduced aggregate exactly equals rq1_result_v1.json", file=sys.stderr)


if __name__ == "__main__":
    main()
