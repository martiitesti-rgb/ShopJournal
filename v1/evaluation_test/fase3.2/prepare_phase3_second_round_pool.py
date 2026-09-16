#!/usr/bin/env python
"""Prepare a blind Phase 3 second-round labelling pool.

This helper compares frozen qrels v1 labels against externally supplied
system-candidate rows. It does not run retrieval and does not compute metrics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


BLIND_COLUMNS = [
    "query_id",
    "note_id",
    "query",
    "note_text",
    "asin",
    "title",
    "price",
    "label",
    "uncertain",
    "note_labelling",
]
PRIVATE_COLUMNS = ["query_id", "asin", "source", "rank", "score", "retrieval_version"]
CANDIDATE_REQUIRED_COLUMNS = ["query_id", "asin", "title"]
RECOVERABLE_CONTEXT_COLUMNS = ["query", "note_id", "note_text"]
FORBIDDEN_BLIND_COLUMNS = {"source", "rank", "score", "retrieval_version"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a blind second-round labelling file for system candidates "
            "that are absent from qrels_v1.csv."
        )
    )
    parser.add_argument("--qrels", required=True, type=Path, help="Path to qrels_v1.csv")
    parser.add_argument(
        "--candidates",
        required=True,
        type=Path,
        help="Path to candidate CSV or JSONL produced outside this script",
    )
    parser.add_argument("--out-dir", required=True, type=Path, help="Output directory")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def load_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        rows: list[dict[str, str]] = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"{path} row {row_number} has extra unnamed columns")
            rows.append({key: normalize_value(value) for key, value in row.items()})
    return rows, list(reader.fieldnames)


def load_jsonl_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    fieldnames: list[str] = []
    seen_fields: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path} line {line_number} is not valid JSON: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError(f"{path} line {line_number} is not a JSON object")
            row = {str(key): normalize_value(value) for key, value in parsed.items()}
            for key in row:
                if key not in seen_fields:
                    seen_fields.add(key)
                    fieldnames.append(key)
            rows.append(row)
    return rows, fieldnames


def load_candidates(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        rows, fieldnames = load_csv_rows(path)
    elif suffix in {".jsonl", ".ndjson"}:
        rows, fieldnames = load_jsonl_rows(path)
    else:
        raise ValueError("Candidate input must be a .csv or .jsonl file")

    missing = [col for col in CANDIDATE_REQUIRED_COLUMNS if col not in fieldnames]
    if missing:
        raise ValueError(f"Candidate input is missing required fields: {', '.join(missing)}")

    for row_number, row in enumerate(rows, start=1):
        blanks = [col for col in CANDIDATE_REQUIRED_COLUMNS if not row.get(col, "").strip()]
        if blanks:
            raise ValueError(
                f"Candidate row {row_number} has blank required fields: {', '.join(blanks)}"
            )
    return rows, fieldnames


def load_qrels(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    rows, fieldnames = load_csv_rows(path)
    missing = [col for col in BLIND_COLUMNS if col not in fieldnames]
    if missing:
        raise ValueError(f"qrels file is missing required fields: {', '.join(missing)}")
    for row_number, row in enumerate(rows, start=1):
        if not row.get("query_id", "").strip() or not row.get("asin", "").strip():
            raise ValueError(f"qrels row {row_number} has blank query_id or asin")
    return rows, fieldnames


def qrels_pair(row: dict[str, str]) -> tuple[str, str]:
    return row["query_id"].strip(), row["asin"].strip()


def build_qrels_context(
    qrels_rows: Iterable[dict[str, str]],
) -> dict[str, dict[str, set[str]]]:
    context: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {field: set() for field in RECOVERABLE_CONTEXT_COLUMNS}
    )
    for row in qrels_rows:
        query_id = row["query_id"].strip()
        for field in RECOVERABLE_CONTEXT_COLUMNS:
            value = row.get(field, "")
            if value:
                context[query_id][field].add(value)
    return dict(context)


def candidate_pair(row: dict[str, str]) -> tuple[str, str]:
    return row["query_id"].strip(), row["asin"].strip()


def recover_context_value(
    row: dict[str, str],
    field: str,
    query_id: str,
    qrels_context: dict[str, dict[str, set[str]]],
) -> str:
    candidate_value = row.get(field, "")
    if candidate_value.strip():
        return candidate_value

    values = qrels_context.get(query_id, {}).get(field, set())
    if len(values) == 1:
        return next(iter(values))
    if not values:
        raise ValueError(
            f"Cannot recover {field!r} for query_id {query_id!r}; no qrels_v1 value found"
        )
    raise ValueError(
        f"Cannot recover {field!r} for query_id {query_id!r}; qrels_v1 values are ambiguous"
    )


def build_outputs(
    qrels_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    qrels_pairs = {qrels_pair(row) for row in qrels_rows}
    qrels_context = build_qrels_context(qrels_rows)

    blind_rows: list[dict[str, str]] = []
    source_map_rows: list[dict[str, str]] = []
    seen_blind_pairs: set[tuple[str, str]] = set()
    new_source_row_counts: Counter[tuple[str, str]] = Counter()
    already_labelled_count = 0

    for row in candidate_rows:
        pair = candidate_pair(row)
        if pair in qrels_pairs:
            already_labelled_count += 1
            continue

        new_source_row_counts[pair] += 1
        source_map_rows.append({column: row.get(column, "") for column in PRIVATE_COLUMNS})

        if pair in seen_blind_pairs:
            continue

        query_id, asin = pair
        blind_rows.append(
            {
                "query_id": query_id,
                "note_id": recover_context_value(row, "note_id", query_id, qrels_context),
                "query": recover_context_value(row, "query", query_id, qrels_context),
                "note_text": recover_context_value(row, "note_text", query_id, qrels_context),
                "asin": asin,
                "title": row.get("title", ""),
                "price": row.get("price", ""),
                "label": "",
                "uncertain": "",
                "note_labelling": "",
            }
        )
        seen_blind_pairs.add(pair)

    stats: dict[str, object] = {
        "qrels_row_count": len(qrels_rows),
        "candidate_row_count": len(candidate_rows),
        "already_labelled_candidate_count": already_labelled_count,
        "new_unjudged_candidate_count": len(blind_rows),
        "per_query_new_counts": Counter(row["query_id"] for row in blind_rows),
        "new_source_row_counts": new_source_row_counts,
    }
    return blind_rows, source_map_rows, stats


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    qrels_path: Path,
    candidates_path: Path,
    out_dir: Path,
    stats: dict[str, object],
) -> None:
    per_query = stats["per_query_new_counts"]
    if not isinstance(per_query, Counter):
        raise TypeError("per_query_new_counts must be a Counter")

    lines = [
        "# Phase 3 second-round pool report",
        "",
        "This report describes a mechanical pool-preparation step only.",
        "",
        f"- qrels_v1 path: `{qrels_path}`",
        f"- candidate input path: `{candidates_path}`",
        f"- output directory: `{out_dir}`",
        f"- qrels row count: **{stats['qrels_row_count']}**",
        f"- candidate row count: **{stats['candidate_row_count']}**",
        (
            "- already-labelled candidate count: "
            f"**{stats['already_labelled_candidate_count']}**"
        ),
        f"- new unjudged candidate count: **{stats['new_unjudged_candidate_count']}**",
        "",
        "## Per-query new candidate counts",
        "",
    ]
    if per_query:
        for query_id in sorted(per_query):
            lines.append(f"- `{query_id}`: {per_query[query_id]}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Method boundary",
            "",
            "- No metric computation was performed by this script.",
            "- Recall@10 and NDCG@10 were not computed.",
            "- `qrels_v1.csv` was not modified.",
            (
                "- `second_round_labelling_blind.csv` hides source, rank, score, "
                "and retrieval_version."
            ),
            (
                "- `second_round_source_map_private.csv` is private provenance and "
                "must not be used during labelling."
            ),
            "- This script does not run retrieval or make a system-performance claim.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def verify_outputs(
    qrels_path: Path,
    original_qrels_hash: str,
    qrels_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    blind_rows: list[dict[str, str]],
    source_map_rows: list[dict[str, str]],
    stats: dict[str, object],
) -> None:
    if file_sha256(qrels_path) != original_qrels_hash:
        raise ValueError("qrels_v1.csv was modified during processing")

    blind_column_set = set(BLIND_COLUMNS)
    leaked_columns = blind_column_set & FORBIDDEN_BLIND_COLUMNS
    if leaked_columns:
        raise ValueError(f"Blind output contains forbidden columns: {', '.join(leaked_columns)}")

    qrels_pairs = {qrels_pair(row) for row in qrels_rows}
    blind_pairs = [candidate_pair(row) for row in blind_rows]
    overlapping = [pair for pair in blind_pairs if pair in qrels_pairs]
    if overlapping:
        raise ValueError(f"Blind output contains already-labelled pairs: {overlapping[:5]}")

    duplicate_blind_pairs = [pair for pair, count in Counter(blind_pairs).items() if count > 1]
    if duplicate_blind_pairs:
        raise ValueError(f"Blind output contains duplicate pairs: {duplicate_blind_pairs[:5]}")

    if len(blind_rows) != stats["new_unjudged_candidate_count"]:
        raise ValueError("New unjudged candidate count does not match blind output rows")

    new_source_row_counts = stats["new_source_row_counts"]
    if not isinstance(new_source_row_counts, Counter):
        raise TypeError("new_source_row_counts must be a Counter")
    source_map_counts = Counter(candidate_pair(row) for row in source_map_rows)
    if source_map_counts != new_source_row_counts:
        raise ValueError("Private source map does not preserve all new candidate source rows")

    candidate_new_source_rows = sum(
        1 for row in candidate_rows if candidate_pair(row) not in qrels_pairs
    )
    if len(source_map_rows) != candidate_new_source_rows:
        raise ValueError("Private source map row count does not match new candidate source rows")


def run() -> int:
    args = parse_args()
    qrels_path = args.qrels
    candidates_path = args.candidates
    out_dir = args.out_dir

    original_qrels_hash = file_sha256(qrels_path)
    qrels_rows, _qrels_fields = load_qrels(qrels_path)
    candidate_rows, _candidate_fields = load_candidates(candidates_path)
    blind_rows, source_map_rows, stats = build_outputs(qrels_rows, candidate_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    blind_path = out_dir / "second_round_labelling_blind.csv"
    source_map_path = out_dir / "second_round_source_map_private.csv"
    report_path = out_dir / "second_round_pool_report.md"

    verify_outputs(
        qrels_path,
        original_qrels_hash,
        qrels_rows,
        candidate_rows,
        blind_rows,
        source_map_rows,
        stats,
    )

    write_csv(blind_path, BLIND_COLUMNS, blind_rows)
    write_csv(source_map_path, PRIVATE_COLUMNS, source_map_rows)
    write_report(report_path, qrels_path, candidates_path, out_dir, stats)

    verify_outputs(
        qrels_path,
        original_qrels_hash,
        qrels_rows,
        candidate_rows,
        blind_rows,
        source_map_rows,
        stats,
    )

    print(f"Wrote {blind_path}")
    print(f"Wrote {source_map_path}")
    print(f"Wrote {report_path}")
    print("No metric computation was performed.")
    print("qrels_v1.csv was not modified.")
    return 0


def main() -> int:
    try:
        return run()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
