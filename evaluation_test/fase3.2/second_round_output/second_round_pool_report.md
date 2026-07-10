# Phase 3 second-round pool report

This report describes a mechanical pool-preparation step only.

- qrels_v1 path: `qrels_v1.csv`
- candidate input path: `system_candidates.csv`
- output directory: `second_round_output`
- qrels row count: **450**
- candidate row count: **600**
- already-labelled candidate count: **0**
- new unjudged candidate count: **271**

## Per-query new candidate counts

- `q01`: 16
- `q02`: 12
- `q03`: 17
- `q04`: 17
- `q05`: 25
- `q06`: 18
- `q07`: 15
- `q08`: 19
- `q09`: 17
- `q10`: 28
- `q11`: 20
- `q12`: 16
- `q13`: 20
- `q14`: 17
- `q15`: 14

## Method boundary

- No metric computation was performed by this script.
- Recall@10 and NDCG@10 were not computed.
- `qrels_v1.csv` was not modified.
- `second_round_labelling_blind.csv` hides source, rank, score, and retrieval_version.
- `second_round_source_map_private.csv` is private provenance and must not be used during labelling.
- This script does not run retrieval or make a system-performance claim.
