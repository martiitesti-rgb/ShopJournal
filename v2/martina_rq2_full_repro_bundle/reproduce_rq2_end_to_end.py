#!/usr/bin/env python3
"""Reproduce FINAL RQ2-v2 locally, using authenticated external metadata/labels.

No network, project imports, cached rankings, output files, or official run entry
points. Product IDs and scores are used in memory only and never printed.
"""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time

sys.dont_write_bytecode = True
BUNDLE = Path(__file__).resolve().parent
MANIFEST_SHA256 = "8a76f6062774923bcc1bc7df8044c08db9c34ba86148e42d2c7eaf11c2c92bc4"
METADATA_SHA256 = "ed9b24ea707f7010b5cb321462a8e896ad1fcd59620fbc55f05084c3da59842e"
METADATA_SIZE = 1382105675
LABEL_SHA256 = "3e2240796c793917cbc1e87fd268da174a8d9864f966d5f20a86dc23f12c3b57"
RETRIEVAL_SHA256 = "da7cfa28541f6f646095c94b2e8f85828fbcb33f0694f8ea30cc7efbc91fbe26"
QUERY_SOURCE_SHA256 = "103772fdaded03c99a35d5227222aeb1d087eeb1ed46f978b939a71bd53b9986"
RETRIEVAL_COUNT = 301889
RATING_MEAN = 4.172684993490985
STRATA = ("DIET", "GIFT", "URGENCY", "BUDGET", "dual")
SELECTION_PREFIX = "20260915\nrq2-v2-primary-subsample\n"
QUERY_FIELDS = ("opaque_slot_id", "Query", "intended_semantic_cue_assignment",
                "explicit_numeric_budget_required")
LABEL_FIELDS = ("judgment_id", "grade", "uncertain", "reason")


class VerificationError(Exception):
    """An input or reproduced result does not meet the frozen contract."""


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def hash_stream(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def hash_file(path):
    with path.open("rb") as stream:
        return hash_stream(stream)


def sequence_signature(ids):
    """UTF-8, IDs in given order, one LF after EVERY ID, including the last."""
    require(all(isinstance(item, str) and item and "\n" not in item and "\r" not in item
                for item in ids), "Invalid ID sequence")
    return sha256(("\n".join(ids) + "\n").encode("utf-8"))


def read_csv(raw, fields, context):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    require(tuple(reader.fieldnames or ()) == fields, context + ": exact schema required")
    rows = list(reader)
    require(all(set(row) == set(fields) and all(row[f] is not None for f in fields)
                for row in rows), context + ": malformed row")
    return rows


def load_inputs(labels_path):
    raw = (BUNDLE / "bundle_manifest.json").read_bytes()
    require(sha256(raw) == MANIFEST_SHA256, "Bundle manifest SHA-256 mismatch")
    manifest = json.loads(raw)
    for name, expected in manifest["file_sha256"].items():
        path = (BUNDLE / name).resolve()
        require(path.is_relative_to(BUNDLE), "Invalid bundle asset path")
        require(hash_file(path) == expected, "Bundle asset SHA-256 mismatch: " + name)
    require(manifest["sources"]["query_set"]["sha256"] == QUERY_SOURCE_SHA256,
            "Canonical query source identity mismatch")
    raw_labels = labels_path.read_bytes()
    require(sha256(raw_labels) == LABEL_SHA256, "Returned-label CSV SHA-256 mismatch")
    rows = read_csv(raw_labels, LABEL_FIELDS, "Labels")
    require(len(rows) == 313 and len({r["judgment_id"] for r in rows}) == 313,
            "Labels must contain exactly 313 rows and 313 unique judgment IDs")
    for row in rows:
        require(len(row["judgment_id"]) == 64 and
                all(c in "0123456789abcdef" for c in row["judgment_id"]), "Invalid judgment ID")
        require(row["grade"] in ("0", "1", "2"), "Invalid grade")
        require(row["uncertain"] in ("true", "false"), "Invalid uncertainty flag")
        require(bool(row["reason"].strip()), "Empty judgment reason")
    labels = {r["judgment_id"]: int(r["grade"]) for r in rows}
    members_raw = (BUNDLE / "retrieval_parent_asins.txt").read_bytes()
    require(sha256(members_raw) == RETRIEVAL_SHA256, "Canonical retrieval identity mismatch")
    members = members_raw.decode("utf-8").splitlines()
    require(len(members) == RETRIEVAL_COUNT and members == sorted(set(members)),
            "Retrieval membership count, uniqueness, or order mismatch")
    queries = read_csv((BUNDLE / "rq2_final_queries.csv").read_bytes(), QUERY_FIELDS, "Queries")
    notes = json.loads((BUNDLE / "rq2_note_inputs.json").read_bytes())
    require(len(queries) == len({r["opaque_slot_id"] for r in queries}) == 40,
            "Expected 40 unique query IDs")
    require(len(notes) == len({n["opaque_slot_id"] for n in notes}) == 40,
            "Expected 40 unique note pairings")
    require(all(set(n) == {"opaque_slot_id", "canonical_note_id", "distinctive_terms"}
                for n in notes), "Note projection schema mismatch")
    require(len({n["canonical_note_id"] for n in notes}) == 40, "Notes must be unique")
    require([r["opaque_slot_id"] for r in queries] == [n["opaque_slot_id"] for n in notes],
            "Query-note pairing order mismatch")
    return manifest, members, queries, notes, labels


def load_catalog(stream, members, scoring):
    """Stream metadata; retain only parent ID, title, price and average_rating.

    The frozen data has zero duplicates. Reject ANY duplicate retrieval ID,
    including identical duplicates, instead of silently accepting altered data.
    Missing/invalid ratings use scoring.valid_rating and prepare_catalog exactly.
    """
    membership = set(members)
    items = {}
    digest = hashlib.sha256()
    for raw in stream:
        digest.update(raw)
        row = json.loads(raw)
        item_id = scoring.canonical_id(row.get("parent_asin"))
        if item_id not in membership:
            continue
        require(item_id not in items, "Duplicate or conflicting canonical retrieval ID")
        items[item_id] = scoring.CatalogItem(
            item_id, row.get("title"), row.get("price"), row.get("average_rating"))
    require(digest.hexdigest() == METADATA_SHA256, "Metadata changed during catalog read")
    require(set(items) == membership and len(items) == RETRIEVAL_COUNT,
            "Retrieval catalog coverage/count mismatch")
    valid_count = sum(scoring.valid_rating(item.mean_rating) is not None for item in items.values())
    require(valid_count == RETRIEVAL_COUNT, "Valid rating count mismatch")
    catalog = scoring.prepare_catalog(
        items.values(), members, membership_identity=RETRIEVAL_SHA256,
        catalog_identity="2b6d039ed471f2ba5fd2acb718bf33b0a7e5598e",
        catalog_sha256=METADATA_SHA256)
    require(catalog.rating_mean.hex() == RATING_MEAN.hex(), "Frozen arithmetic rating mean mismatch")
    return catalog, valid_count


def select_queries(queries):
    groups = {stratum: [] for stratum in (*STRATA, "cue_free")}
    for query in queries:
        assignment = query["intended_semantic_cue_assignment"]
        cues = [] if assignment == "CUE_FREE" else assignment.split("+")
        require(len(cues) <= 2 and len(set(cues)) == len(cues) and set(cues) <= set(STRATA[:-1]),
                "Invalid intended cue assignment")
        stratum = "dual" if len(cues) == 2 else cues[0] if cues else "cue_free"
        qid = query["opaque_slot_id"]
        groups[stratum].append({"opaque_slot_id": qid, "stratum": stratum,
                               "selection_sha256": sha256((SELECTION_PREFIX + qid).encode("utf-8"))})
    require(all(len(groups[s]) == 6 for s in STRATA) and len(groups["cue_free"]) == 10,
            "Frozen 40-query stratum counts mismatch")
    selected = []
    for stratum in STRATA:
        selected.extend(sorted(groups[stratum], key=lambda x: (x["selection_sha256"], x["opaque_slot_id"]))[:4])
    expected = json.loads((BUNDLE / "expected_v2_selection.json").read_bytes())
    require(selected == expected["selected"], "Frozen selected-20 sequence mismatch")
    return selected


def reconstruct_rankings(catalog, queries, notes, scoring, verify):
    expected = json.loads((BUNDLE / "expected_ranking_signatures.json").read_bytes())["queries"]
    require(set(expected) == {q["opaque_slot_id"] for q in queries}, "Signature query set mismatch")
    pairs = {}
    controls = 0
    budget_count = 0
    matched = 0
    for index, (query, note) in enumerate(zip(queries, notes), 1):
        qid = query["opaque_slot_id"]
        intended = set() if query["intended_semantic_cue_assignment"] == "CUE_FREE" else set(
            query["intended_semantic_cue_assignment"].split("+"))
        rep = scoring.represent_query(query["Query"], note["distinctive_terms"])
        require(rep.cues.detected == intended and rep.cues.executable == intended,
                "Frozen query cue admission mismatch")
        require(query["explicit_numeric_budget_required"] in ("true", "false"), "Invalid budget flag")
        require((query["explicit_numeric_budget_required"] == "true") == ("BUDGET" in intended),
                "Budget requirement mismatch")
        if "BUDGET" in intended:
            require(bool(rep.cues.budget.bounds), "Numeric budget is not executable")
            budget_count += 1
        # Unmodified frozen scorer: no accelerated replacement or monkey patch.
        pair = scoring.rank_pair(catalog, query["Query"], note["distinctive_terms"])
        require(len(pair.candidate_ids) == len(set(pair.candidate_ids)) == 200,
                "Expected exactly 200 unique shared candidates")
        require(len(pair.base) == len(pair.full) == 200, "Ranking count mismatch")
        if not intended:
            require(pair.base == pair.full, "Cue-free Base=Full control failed")
            controls += 1
        signatures = {
            "candidate_ids_sha256": sequence_signature(pair.candidate_ids),
            "base_top10_ids_sha256": sequence_signature([r.parent_asin for r in pair.base[:10]]),
            "full_top10_ids_sha256": sequence_signature([r.parent_asin for r in pair.full[:10]]),
        }
        match = signatures == expected[qid]
        matched += match
        if verify:
            require(match, "Candidate/ranking signature mismatch at query number " + str(index))
        pairs[qid] = pair
        print(f"Ranked query {index}/40; signature {'PASS' if match else 'FAIL'}", file=sys.stderr, flush=True)
    require(controls == 10 and budget_count == 9, "Control/budget query counts mismatch")
    return pairs, matched, controls


def judgment_id(query_id, parent_asin):
    return sha256(f"20260914\njudgment-id/{query_id}\n{parent_asin}".encode("utf-8"))


def build_analysis_records(selected, pairs, labels):
    records = []
    seen = set()
    for query in selected:
        qid = query["opaque_slot_id"]
        pair = pairs[qid]
        base = [judgment_id(qid, r.parent_asin) for r in pair.base[:10]]
        full = [judgment_id(qid, r.parent_asin) for r in pair.full[:10]]
        union = set(base) | set(full)
        require(len(set(base)) == len(set(full)) == 10, "Duplicate top-10 judgment ID")
        require(not seen & union, "Cross-query judgment-ID collision")
        require(union <= labels.keys(), "Missing labels for reconstructed judgment universe")
        seen.update(union)
        records.append({"stratum": query["stratum"], "base": base, "full": full,
                        "grades": {jid: labels[jid] for jid in union}})
    require(len(seen) == 313 and seen == labels.keys(), "313-label coverage mismatch: missing or extra labels")
    return records


def dcg(grades):
    # Exact math.fsum/discount arithmetic from frozen run_rq2_v2._dcg.
    return math.fsum((2**grade - 1) / math.log2(rank + 1)
                     for rank, grade in enumerate(grades, start=1))


def paired_summary(values):
    require(len(values) == 20, "Paired summary requires 20 queries")
    return {"full_minus_base_mean": math.fsum(values) / len(values),
            "full_minus_base_median": statistics.median(values),
            "negative_count": sum(value < 0.0 for value in values),
            "positive_count": sum(value > 0.0 for value in values),
            "zero_count": sum(value == 0.0 for value in values)}


def calculate(records, np):
    ndcg_by_stratum = {s: [] for s in STRATA}
    precision_differences = []
    zero_idcg = 0
    for record in records:
        grades = record["grades"]
        ideal = dcg(sorted(grades.values(), reverse=True)[:10])
        zero_idcg += ideal == 0.0
        ndcg, precision = [], []
        for condition in ("base", "full"):
            ranking = record[condition]
            ndcg.append(dcg(grades[jid] for jid in ranking) / ideal if ideal else 0.0)
            precision.append(sum(grades[jid] in (1, 2) for jid in ranking) / 10.0)
        ndcg_by_stratum[record["stratum"]].append(ndcg[1] - ndcg[0])
        precision_differences.append(precision[1] - precision[0])
    arrays = [np.asarray(ndcg_by_stratum[s], dtype=float) for s in STRATA]
    require(all(array.size == 4 for array in arrays), "Bootstrap requires four queries per stratum")
    # Keep the exact controller's RNG call order and NumPy mean operation.
    rng = np.random.Generator(np.random.PCG64(20260915))
    replicates = np.empty(10000, dtype=float)
    for index in range(10000):
        draws = [rng.choice(array, size=4, replace=True) for array in arrays]
        replicates[index] = float(np.concatenate(draws).mean())
    interval = np.percentile(replicates, [2.5, 97.5], method="linear")
    return {
        "bootstrap": {"draws_per_stratum": 4, "numpy_version": np.__version__,
                      "percentile_method": "linear", "replicates": 10000,
                      "rng": "PCG64", "seed": 20260915, "stratum_order": list(STRATA)},
        "metrics": {
            "ndcg_at_10": {
                "paired_full_minus_base": paired_summary([v for s in STRATA for v in ndcg_by_stratum[s]]),
                "percentile_interval_2_5_97_5": [float(x) for x in interval],
                "zero_idcg_query_count": zero_idcg},
            "precision_at_10": {"paired_full_minus_base": paired_summary(precision_differences)}},
        "population": {"query_count": 20, "stratum_counts": {s: 4 for s in STRATA}}}


def compare_exact(actual, expected):
    require(type(actual) is type(expected), "Aggregate value type mismatch")
    if isinstance(expected, dict):
        require(actual.keys() == expected.keys(), "Aggregate field set mismatch")
        for key in expected:
            compare_exact(actual[key], expected[key])
    elif isinstance(expected, list):
        require(len(actual) == len(expected), "Aggregate array length mismatch")
        for left, right in zip(actual, expected):
            compare_exact(left, right)
    else:
        require(actual == expected, "Exact aggregate value mismatch")


def verify_aggregate(result):
    frozen = json.loads((BUNDLE / "rq2_v2_result_v1.json").read_bytes())
    compare_exact(result, {key: frozen[key] for key in ("bootstrap", "metrics", "population")})
    ndcg = result["metrics"]["ndcg_at_10"]
    precision = result["metrics"]["precision_at_10"]["paired_full_minus_base"]
    compare_exact(ndcg, {
        "paired_full_minus_base": {"full_minus_base_mean": 0.30081140426797137,
            "full_minus_base_median": 0.05525379734128455, "positive_count": 11,
            "zero_count": 7, "negative_count": 2},
        "percentile_interval_2_5_97_5": [0.14704192509677733, 0.4590615897564671],
        "zero_idcg_query_count": 2})
    compare_exact(precision, {"full_minus_base_mean": 0.22000000000000003,
        "full_minus_base_median": 0.15, "positive_count": 12, "zero_count": 8, "negative_count": 0})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True, help="Exact frozen Amazon metadata JSONL")
    parser.add_argument("--labels", type=Path, required=True, help="Exact returned primary judgment CSV")
    parser.add_argument("--verify", action="store_true", help="Require all ranking and aggregate matches")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    # Authenticate ALL inputs before scientific computation; keep the metadata
    # handle open and rehash the streaming pass to detect mid-run replacement.
    with args.metadata.open("rb") as stream:
        require(stream.seek(0, 2) == METADATA_SIZE, "Metadata byte size mismatch")
        stream.seek(0)
        require(hash_stream(stream) == METADATA_SHA256, "Metadata SHA-256 mismatch")
        stream.seek(0)
        manifest, members, queries, notes, labels = load_inputs(args.labels)
        import numpy as np
        if args.verify:
            require(np.__version__ == "1.26.4", "Exact verification requires NumPy 1.26.4")
        # The four package files were authenticated before this import.
        sys.path.insert(0, str(BUNDLE))
        from final_evaluation import scoring
        require(Path(scoring.__file__).resolve() == BUNDLE / "final_evaluation/scoring.py",
                "Scorer import is not bundle-local")
        require(scoring.CANDIDATE_CAP == 200, "Frozen candidate cap mismatch")
        print("Input authentication PASS; streaming retrieval catalog", file=sys.stderr, flush=True)
        catalog, valid_count = load_catalog(stream, members, scoring)
    selected = select_queries(queries)
    pairs, matched, controls = reconstruct_rankings(catalog, queries, notes, scoring, args.verify)
    records = build_analysis_records(selected, pairs, labels)
    result = calculate(records, np)
    if args.verify:
        verify_aggregate(result)
    report = {
        "verification": "PASS" if args.verify else "NOT_REQUESTED",
        "checks": {"metadata_authentication": "PASS", "bundle_input_authentication": "PASS",
                   "retrieval_catalog_count": len(catalog.items), "valid_rating_count": valid_count,
                   "rating_mean": catalog.rating_mean, "rating_mean_float_hex": catalog.rating_mean.hex(),
                   "duplicate_retrieval_ids": 0, "query_count": len(pairs), "candidates_per_query": 200,
                   "candidate_ranking_signatures": "PASS" if matched == 40 else "FAIL",
                   "matched_query_signatures": matched, "cue_free_equal_controls": controls,
                   "selected_20": "PASS", "label_coverage_313": "PASS",
                   "aggregate": "PASS" if args.verify else "NOT_REQUESTED"},
        "result": result,
        "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                    "elapsed_seconds": time.perf_counter() - started}}
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Frozen library exceptions can contain raw product IDs. Never echo them.
        message = str(exc) if isinstance(exc, VerificationError) else type(exc).__name__
        print(json.dumps({"verification": "FAIL", "blocker": message}), file=sys.stderr)
        raise SystemExit(1)
