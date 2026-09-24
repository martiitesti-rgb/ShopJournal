# ShopJournal — Streamlit app

Demo prototype for the bachelor's thesis *ShopJournal: Affect-Aware Text-Driven Shopping Recommender*.
The user types a natural-language query. The system combines it with the note generated from the user's purchase history and returns a top-10 of Grocery & Gourmet Food products (Amazon Reviews 2023).

## Running the app

Requires Python 3.10 or later. From the `shopjournal_app` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run Home.py
```

The app opens at `http://localhost:8501`.

On later runs:

```bash
source .venv/bin/activate
python3 -m streamlit run Home.py
```

Always launch it from inside `shopjournal_app`, otherwise the `core.` and `db.` imports will not resolve.

## Pages

| Page | Purpose |
|---|---|
| `Home.py` | Search: query → top-10 (variant `query_notes_pop_cue`), *Buy* button |
| `pages/Profile.py` | Sign up, log in, log out |
| `pages/Purchased.py` | The user's purchase history, with deletion |

## Structure

```
shopjournal_app/
├── Home.py
├── pages/
│   ├── Profile.py
│   └── Purchased.py
├── core/
│   ├── catalog.py            # loads data/catalog.parquet
│   ├── recommender.py        # interface used by the pages (VARIANTS, get_recommendations)
│   ├── scoring.py            # adapter: app DataFrame → final scoring logic
│   ├── note_pipeline.py      # note generation from purchase history (v3r1 logic, Set A)
│   ├── cue_extractor.py      # previous version (keywords + VADER), no longer used
│   └── final_evaluation/     # final scoring logic, copied unchanged
│       ├── lexical.py        # normalization, tokenization, contractions, negation
│       ├── cues.py           # query cues, budget parser, cueScore
│       └── scoring.py        # candidates, matchQuery, matchNotes, ratingPrior, ranking
├── db/
│   ├── database.py           # SQLite connection and schema
│   ├── models.py             # users, purchases, notes, search history
│   └── shopjournal.db
└── data/
    └── catalog.parquet       # 40,000 products
```

## Catalog

`data/catalog.parquet` must contain at least the columns `asin`, `title`, `price` and `average_rating`. The search page also uses `category`.
The `asin` column is passed to the scorer as `parent_asin`, the canonical identifier required by `final_evaluation`. Prices are stored as strings; `"None"` marks a missing price.

## How ranking works

`core/scoring.py` is only an adapter. It keeps the `score_query()` signature used by `recommender.py` and delegates all computation to `core/final_evaluation/`.

**Candidates.** The system takes the union of two sets: the informative units of the query, and the note's distinctive terms that do not already appear in the query. A product is a candidate if its title contains at least one of these units. Candidates are ordered by number of matched units (descending), then by `parent_asin`. At most 200 are kept.

**Score.** For each candidate:

```
matchQuery  = share of query units found in the title
matchNotes  = share of note terms found in the title
ratingPrior = average_rating / 5   (catalog mean if missing)
cueScore    = mean of the 0/1 compatibility values over executable cues

Base = matchQuery + matchNotes + ratingPrior
Full = Base + cueScore
```

All coefficients are 1. Ties are broken by the smaller `parent_asin`.

**Variants** (`core/recommender.py → VARIANTS`):

| Variant | Score |
|---|---|
| `query_only` | matchQuery |
| `query_notes` | matchQuery + matchNotes |
| `query_notes_pop` | Base |
| `query_notes_pop_cue` | Full (used in Home) |

## Cues

Cues are extracted **from the query only**: the note does not contribute cues, and VADER is not used. A cue can be *detected* without being *executable*. Only executable cues enter `cueScore`.

| Cue | Executable when | Compatible if |
|---|---|---|
| DIET | the query names a property: vegan, vegetarian, gluten free, dairy free, nut free, peanut free, sugar free, organic, healthy (aliases such as "no gluten" and "without sugar" also count) | the title contains every requested property, not negated |
| GIFT | gift, present, birthday, anniversary | the title contains gift, gift set or gift box |
| URGENCY | urgent, fast, quick, now, today, tomorrow, last minute, emergency | the title contains instant, ready to eat, quick or microwave |
| BUDGET | there is an explicit dollar bound: `under $10`, `below $10`, `less than $10`, `max $10`, `up to $10`, `$10 or less` | the price satisfies the bound (a missing price counts as 0) |

Some practical consequences:

- "cheap", "affordable" and "sale" detect BUDGET but do not make it executable.
- Euros, ranges ("between $5 and $10"), unit prices ("each"), alternative bounds ("or") and approximate bounds ("about") are ignored or rejected.
- Negation ("not vegan", "not cheap") suppresses the cue. "not expensive" is instead a budget expression in its own right.
- Budget is a score bonus, **not a filter**: over-budget products can still appear in the top-10.

## Database

SQLite, in a single file: `db/shopjournal.db`. Tables are created at startup by `init_db()`.

| Table | Contents |
|---|---|
| `users` | username, PBKDF2-SHA256 password hash, salt |
| `purchase_history` | purchases per user (sub-category, title, price, rating) |
| `generated_notes` | one note per user: text, distinctive terms, price profile |
| `search_history` | executed queries, variant used, whether a note was present |

To inspect it: `sqlite3 db/shopjournal.db`, then `.tables`.

## Known limitations

- **The note is never updated.** `regenerate_note()` exists in `db/models.py` but no page calls it. After a purchase or a deletion, the stored note stays the old one.
- **Products without a price.** About 56% of the catalog has no price. These products are shown as "prezzo non disponibile". If bought, they are saved with price 0 (the `price` column is `NOT NULL`), which lowers the median of the note's price profile.
- **Unknown contractions.** A query containing a contraction missing from the table in `lexical.py` (e.g. "gimme'd") raises `ValueError`. Home catches it, but shows the misleading message "Problema con i dati del catalogo."
- **Response time.** Each search takes about 1.5–2 seconds, because all 40,000 titles are tokenized on every query.
- **English only.** Italian queries ("caffè") trigger no cues and match few titles.
- Streamlit's "Running…" indicator is hidden via CSS on every page.
