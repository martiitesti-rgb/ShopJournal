## `Repository content`
- **`Diary_ShopJournal.ipynb`**: it contains the project's throughout evolution
- **`Articles_notes.ipynb`**: here there are some useful topics found in the research papers

- **`RetrievingReviews.ipynb`**: code to retrieve the first lines of the McAuley-Lab Amazon-Reviews-2023 dataset
  
- **`extracting_cues.ipynb`**: code to retrieve given in input a query and a note the compound score, the sentiment label and the intent flags, as well as a list of the keywords used.

### `evaluation_test/` — offline evaluation (Phase 3)

- `ggf_notes_student_v0.1.jsonl` — the full pool of 200 synthetic user notes (Grocery and Gourmet Food) from which the 15 evaluation notes are sampled.

#### `fase3.1/`
- **`Evaluation_TestSet.ipynb`**: builds the evaluation test set for Phase 3. It loads the 15 selected user notes from `ggf_notes_student_v0_1.jsonl`, loads the Amazon Reviews 2023 Grocery and Gourmet Food product catalog, and defines 15 query–note pairs. For each pair it constructs a candidate pool by retrieving catalog items whose titles match keywords from the query and the note's distinctive terms. The notebook exports the pools to `pool_candidates.jsonl` and a labelling sheet to `labelling.csv`.

- **`pool_candidates.jsonl`**: candidate pool for the offline evaluation. One line per query (15 queries, all within the Grocery and Gourmet Food section), each with `query_id`, `query`, `note_id`, `note_text`, and a `candidates` list (~30 products per query: title, asin, price).

- **`labelling.cs`v**: labelling file for the offline evaluation . It contains the query–candidate pairs drawn from the candidate pool, one row per candidate product. The columns are: `query_id`, `query`, `note_text`, `asin`, `title`, `price`, `label`, `incerto`, `note_labelling`. The `label` column is filled in manually with a relevance judgment on a 0–1–2 scale (0 = not relevant, 1 = partially relevant, 2 = clearly relevant); `incerto` flags uncertain cases; `note_labelling` records a short reason for pairs that were hard to judge. 

- **`labelling_log.md`**: log that documents the queries that were hard to label and a short reason why

#### `fase3.2/`
- `functions.py` — the actual scoring functions of the recommender: `matchQuery()`, `matchNotes()`, `cueScore()` (checks budget/diet/urgency/gift cues against product title and price), `popularityScore()` (based on average rating), plus `extract_cues()` (same VADER + keyword logic as `extracting_cues.ipynb`) and `score_query()`, which combines everything into 4 scoring variants: `query_only`, `query_notes`, `query_notes_pop`, `query_notes_pop_cue`.
- `recommender_system.ipynb` — runs the actual system: for each of the 15 queries, computes the top-10 ranking under all 4 scoring variants and exports every ranked result to `system_candidates.csv`.
- `system_candidates.csv` — 600 rows (15 queries × 4 variants × 10 ranked results), with `source` (which variant), `rank`, and `score` for each candidate.
- `qrels_v1.csv` — the labelling.csv obtained in phase 3.1
- `prepare_phase3_second_round_pool.py` — a validation/pooling script that compares `system_candidates.csv` against `qrels_v1.csv` to find candidates the real system surfaced that were **not** in the original judged pool (112 new query–asin pairs), and prepares them for a second, blind labelling round. 
- `labelling_log.md` — notes from building the real scoring system.
- `second_round_output/` — outputs of `prepare_phase3_second_round_pool.py`:
  - `second_round_labelling_blind.csv` — the 112 new candidate pairs to label, with scoring.
  - `second_round_source_map_private.csv`
  - `second_round_pool_report.md` — a report of the pooling run 
