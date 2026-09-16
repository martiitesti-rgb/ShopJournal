# ShopJournal

Affect-Aware Text-Driven Shopping Recommender Prototype — bachelor's thesis project.

ShopJournal combines a user's current search query with a mechanically generated
note (derived from purchase history) plus intent cues (keyword-based detection of
diet, gift, urgency and budget signals) to produce a ranked Top-10 product list from
the Amazon Reviews 2023 Grocery & Gourmet Food catalog (~603K products).

> **Status note (September 2026):** the evaluation protocol described below under
> [Final evaluation protocol](#final-evaluation-protocol-locked-september-2026) is
> the current, locked methodology. Everything under
> [`evaluation_test/` — pilot evaluation](#evaluation_test--pilot-evaluation-phase-3)
> reflects an earlier iteration (4 scoring variants, 15 queries) and is now kept as a
> **pilot / development set**, not the final evaluation.

## Repository content

- **`shopjournal_app`**: Streamlit web app demo of ShopJournal
- **`Diary_ShopJournal.ipynb`**: log of the project's evolution throughout development
- **`Articles_notes.ipynb`**: notes on relevant topics found in the research literature
- **`RetrievingReviews.ipynb`**: code to retrieve and inspect the McAuley-Lab
  Amazon-Reviews-2023 dataset
- **`extracting_cues.ipynb`**: prototype of `extract_cues(query, notes)` — returns the
  VADER compound score, sentiment label, per-category intent flags, and the list of
  matched keywords

## Research questions

The research questions were redefined in September 2026 in agreement with the
thesis advisor; this framing supersedes an earlier one (notes-vs-query-only,
cues-add-value-beyond-notes).

- **RQ1** — In che misura un estrattore lessicale semplice identifica correttamente,
  nelle query di acquisto, le cue semantiche predefinite (DIET, GIFT, URGENCY,
  BUDGET)?
- **RQ2** — Quando tali cue sono riconosciute e utilizzabili dal sistema, l'aggiunta
  di un punteggio di compatibilità basato sulle cue (`cueScore`) migliora la qualità
  del ranking rispetto allo stesso sistema di base senza cue?

## V1 CONTENT
## `evaluation_test/` — pilot evaluation (Phase 3)

Earlier iteration of the evaluation, now a pilot/development set (superseded by the
protocol above, not the final evaluation).

- `ggf_notes_student_v0.1.jsonl` — pool of 200 synthetic user notes (Grocery and
  Gourmet Food) from which the 15 pilot evaluation notes are sampled

#### `fase3.1/`

- **`Evaluation_TestSet.ipynb`** — builds the pilot evaluation test set: loads 15
  selected user notes and the Amazon Reviews 2023 Grocery and Gourmet Food catalog,
  defines 15 query–note pairs, and builds a keyword-matched candidate pool per pair
  (~30 products each). Exports `pool_candidates.jsonl` and `labelling.csv`.
- **`pool_candidates.jsonl`** — candidate pool: one line per query (15 queries),
  each with `query_id`, `query`, `note_id`, `note_text`, and a `candidates` list
  (title, asin, price)
- **`labelling.csv`** — labelling file: `query_id`, `query`, `note_text`, `asin`,
  `title`, `price`, `label` (0/1/2 relevance), `incerto`, `note_labelling`
- **`labelling_log.md`** — log of queries that were hard to label and why

#### `fase3.2/`

- `functions.py` — pilot scoring functions: `matchQuery()`, `matchNotes()`,
  `cueScore()`, `popularityScore()`, `extract_cues()`, and `score_query()`,
  combining them into 4 scoring variants: `query_only`, `query_notes`,
  `query_notes_pop`, `query_notes_pop_cue`
- `recommender_system.ipynb` — runs the pilot system: for each of the 15 queries,
  computes the Top-10 ranking under all 4 variants, exported to
  `system_candidates.csv`
- `system_candidates.csv` — 600 rows (15 queries × 4 variants × 10 results), with
  `source`, `rank`, `score`
- `qrels_v1.csv` — the `labelling.csv` from phase 3.1
- `prepare_phase3_second_round_pool.py` — validation/pooling script comparing
  `system_candidates.csv` against `qrels_v1.csv` to find unjudged candidates the
  real system surfaced (112 new query–asin pairs), prepared for a second blind
  labelling round
- `labelling_log.md` — notes from building the pilot scoring system
- `second_round_output/`:
  - `second_round_labelling_blind.csv` — the 112 new candidate pairs to label
  - `second_round_source_map_private.csv`
  - `second_round_pool_report.md` — report of the pooling run

## Tools

Python, Jupyter / Google Colab, pandas, VADER (vaderSentiment). CSV delimiter is
`;` throughout the project. Planned demo: Streamlit (Python-only, local).
