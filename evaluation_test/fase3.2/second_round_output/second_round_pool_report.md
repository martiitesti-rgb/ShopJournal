# Phase 3 second-round pool report

This report describes a mechanical pool-preparation step only.

- qrels_v1 path: `qrels_v1.csv`
- candidate input path: `system_candidates.csv`
- output directory: `second_round_output`
- qrels row count: **450**
- candidate row count: **600**
- already-labelled candidate count: **409**
- new unjudged candidate count: **112**

## Per-query new candidate counts

- `q01`: 6
- `q02`: 6
- `q03`: 12
- `q04`: 5
- `q05`: 14
- `q06`: 2
- `q07`: 2
- `q08`: 9
- `q09`: 12
- `q10`: 9
- `q11`: 8
- `q12`: 9
- `q13`: 13
- `q14`: 2
- `q15`: 3

## Method boundary

- No metric computation was performed by this script.
- Recall@10 and NDCG@10 were not computed.
- `qrels_v1.csv` was not modified.
- `second_round_labelling_blind.csv` hides source, rank, score, and retrieval_version.
- `second_round_source_map_private.csv` is private provenance and must not be used during labelling.
- This script does not run retrieval or make a system-performance claim.
