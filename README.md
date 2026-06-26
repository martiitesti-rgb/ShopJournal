## Repository content
- **Diary_ShopJournal.ipynb**: it contains the project's throughout evolution
- **Articles_notes.ipynb**: here there are some useful topics found in the research papers

codes
- **RetrievingReviews.ipynb**: code to retrieve the first lines of the McAuley-Lab Amazon-Reviews-2023 dataset
  
- **extracting_cues.ipynb**: code to retrieve given in input a query and a note the compound score, the sentiment label and the intent flags, as well as a list of the keywords used.

- **Evaluation_TestSet.ipynb: builds the evaluation test set for Phase 3. It loads the 15 selected user notes from `ggf_notes_student_v0_1.jsonl`, loads the Amazon Reviews 2023 Grocery and Gourmet Food product catalog, and defines 15 query–note pairs. For each pair it constructs a candidate pool by retrieving catalog items whose titles match keywords from the query and the note's distinctive terms. The notebook exports the pools to `pool_candidates.jsonl` and a labelling sheet to `labelling.csv`.

- **pool_candidates.jsonl**: candidate pool for the offline evaluation. One line per query (15 queries, all within the Grocery and Gourmet Food section), each with `query_id`, `query`, `note_id`, `note_text`, and a `candidates` list (~30 products per query: title, asin, price).

- **labelling.csv**: labelling file for the offline evaluation . It contains the query–candidate pairs drawn from the candidate pool, one row per candidate product. The columns are: `query_id`, `query`, `note_text`, `asin`, `title`, `price`, `label`, `incerto`, `note_labelling`. The `label` column is filled in manually with a relevance judgment on a 0–1–2 scale (0 = not relevant, 1 = partially relevant, 2 = clearly relevant); `incerto` flags uncertain cases; `note_labelling` records a short reason for pairs that were hard to judge. 
