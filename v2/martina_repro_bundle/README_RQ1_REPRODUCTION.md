# RQ1 reproduction package

This package reproduces the frozen RQ1 query-cue extraction result. It uses the
original first-authored query versions, not any RQ2 revision.

## Reproduction population

The input contains 40 original RQ1 queries. The frozen pre-extractor semantic
authoring review admitted 35 queries to the primary extractor metrics and marked
five as authoring failures. Those five rows are excluded from TP, FP, FN, exact-set,
micro, macro, and cue-free extractor-error counts; they are not counted as extractor
errors. Their decisions and plain-language reasons are in
`rq1_authoring_admission.csv`. No extractor outputs or matched spans are included in
that file.

The zero-denominator convention is `0.0` for precision, recall, and F1. The helper
computes exact-set accuracy, per-category TP/FP/FN/precision/recall/F1, micro
precision/recall/F1, macro precision/recall/F1, and cue-free false-positive rate.
Metric values are computed from the input and frozen extractor; they are not
hard-coded.

## Environment and command

The frozen run used Python 3.11.15 in your `YOUR_PY_ENV` Conda environment and had
no third-party Python dependencies. From this directory, run:

```powershell
conda run --no-capture-output -n YOUR_PY_ENV python -B reproduce_rq1.py --verify
```

The command prints the reproduced result JSON. With `--verify`, it exits with an
`implementation_config_blocker` unless that complete JSON object exactly equals
`rq1_result_v1.json`.

Frozen RQ1 execution commit: `06b0742790740f68c427a20d5409bebe0560c18b`

Current final-query freeze commit: `5c90bbe806f02db5895bdd12eda5eb67c3d909e9`

## Expected hashes

| File or canonical input | SHA-256 |
| --- | --- |
| `rq1_first_versions.csv` | `d9e36e3bfa9606e8dc0985a0928ce4e53d15c75b7812419384e9278636ecd34d` |
| `rq1_authoring_admission.csv` | `c1002d69e8d94e86d4f373249bb7407f9437785c98c862ef5fa3eb7bc57275d1` |
| `final_evaluation/__init__.py` | `6b6d98c78fe1648e24250e364da66818d855593060882bf9088cc2c21a59fa90` |
| `final_evaluation/lexical.py` | `8c8843747a436d897209e3e5dd3b1eca0a3f4cfd1c9b51c9d8fe4221ea1b711e` |
| `final_evaluation/cues.py` | `b3db6382d1ec232a99583fac821ba1d79384cb04107f13077490bf6ba81f9251` |
| `rq1_result_v1.json` | `3d6ea1652e9e9245778100409bd2e7667029bc7d51b419b41ad71751535816d0` |
| `rq1_run_v1.json` | `1b0991e44afea21fec37ec63609eb43024334626f1040c1578ee0edd3faacb85` |
| `reproduce_rq1.py` | `df13809b7a805548a89c730c3f660004b8436499c7cc7731f7cc60d389062f64` |
| `rq2_final_queries.csv` | `53f889326e5f315279342d751eed7cc0b1bb1b210866cfb2776e482778ef0ad5` |
| Canonical private final RQ2 set | `103772fdaded03c99a35d5227222aeb1d087eeb1ed46f978b939a71bd53b9986` |

`rq1_first_versions.csv`, the three files under `final_evaluation/`,
`rq1_result_v1.json`, and `rq1_run_v1.json` are byte-identical copies of their
frozen repository sources.

## RQ2 input provenance

`rq2_final_queries.csv` is a student-facing projection of the frozen final 40-query
RQ2 input. Its query text, opaque IDs, intended assignments, and numeric-budget
requirements were checked field-for-field against the canonical private set whose
SHA-256 is listed above. It contains 30 cue-bearing and 10 cue-free rows.

The `version_origin` values have these meanings:

- `ORIGINAL_SEALED`: unchanged sealed RQ2 query (23 rows).
- `MARTINA_REVISION`: accepted attempt-1 submission version (7 rows).
- `SUPERVISOR_SEMANTIC_PRESERVING_REVISION`: supervisor-controlled attempt-2
  semantic-preserving revision (7 rows).
- `RQ2_ONLY_PROSPECTIVE_AUGMENTATION`: supervisor-controlled, pre-ranking RQ2-only
  augmentation (3 rows).

For six budget-bearing `MARTINA_REVISION` rows, the only query-text change was the
previously recorded packet-generation normalization from suffix/spaced currency
notation to `$N`. That mechanical normalization was already present in the packet
returned by Martina and must not be interpreted as independent Martina authorship
of the currency syntax. The seventh accepted attempt-1 row also contains Martina's
semantic-preserving wording revision.

The three RQ2-only augmentations are explicitly identified in the `added_property`
column:

- `5d064537386df97f3f5488a4`: `organic`
- `1246fec471b0825b640c5d9e`: `gluten free`
- `ed3213072a3050bc8a08df7b`: `vegan`

These three additions were supervisor-controlled and prospectively selected before
any result-bearing RQ2 work. They were not authored by Martina and do not replace
the frozen RQ1 queries.

RQ2 has not yet been executed. The included RQ2 CSV is frozen query input only, not
a complete RQ2 reproduction package. This bundle contains no notes, histories,
product IDs or evidence, candidates, rankings, BM25 output, qrels, relevance labels,
scores, matched spans, row-level extractor outputs, RQ2 metrics, or outcomes.
