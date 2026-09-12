# ShopJournal — Web App (Streamlit)

Scaffold multi-pagina per la demo di ShopJournal: query + note salvate →
Top-10 prodotti consigliati, con gestione utenti e confronto tra le 4
varianti di scoring (query_only, query_notes, query_notes_pop,
query_notes_pop_cue).

## Struttura

```
shopjournal_app/
├── app.py                     # Home — entry point, avvia con `streamlit run app.py`
├── pages/
│   ├── 1_Cerca.py             # query + nota -> Top-10 (una variante)
│   ├── 2_Confronto_Varianti.py# le 4 varianti affiancate
│   ├── 3_Le_mie_Note.py       # CRUD note salvate (richiede login)
│   └── 4_Profilo.py           # registrazione / login / logout
├── db/
│   ├── database.py            # connessione SQLite + schema (users, notes, search_history)
│   ├── models.py               # funzioni di accesso ai dati (register_user, save_note, ...)
│   └── shopjournal.db          # creato al primo avvio, non versionato
├── core/
│   ├── cue_extractor.py        # REALE — porting di extract_cues() (extracting_cues.ipynb)
│   ├── note_pipeline.py        # REALE — porting della pipeline Set A (v3r1_extraction_pipeline)
│   ├── scoring.py               # REALE — porting di functions.py (matchQuery, matchNotes, cueScore, popularityScore, score_query)
│   ├── catalog.py               # loader del catalogo prodotti — percorso da confermare, vedi sotto
│   └── recommender.py           # collega scoring.py + catalog.py, espone get_recommendations() e compute_all_variants()
├── data/
│   └── catalog.parquet         # <-- DA AGGIUNGERE: il catalogo prodotti (vedi sotto)
├── requirements.txt
└── .gitignore
```

## Stato dell'integrazione

- **Cue extractor**, **pipeline di generazione note (Set A)** e **scoring
  (`matchQuery`, `matchNotes`, `cueScore`, `popularityScore`, `score_query`)**
  sono collegati e testati end-to-end con un catalogo fittizio — la logica
  è verbatim dai tuoi file, nessun comportamento cambiato.
- **Manca solo il catalogo prodotti reale.** `core/catalog.py` si aspetta
  un file in `data/catalog.parquet` (o `.csv`) con colonne:
  `asin`, `title`, `price`, `average_rating`. Finché il file non c'è,
  le pagine Cerca e Confronto Varianti mostrano un avviso invece di
  risultati finti.

### Cosa mi serve da te per chiudere il cerchio

Il catalogo Amazon Reviews 2023 Grocery_and_Gourmet_Food ha ~603K prodotti:
troppi per essere ricaricati da Hugging Face a ogni avvio dell'app. Hai già
un export locale (parquet/csv/pickle) da `recommender_system.ipynb`, oppure
va generato apposta? Appena mi dici percorso e formato aggiorno
`CATALOG_PATH` in `core/catalog.py`.

## Adattamento per note libere (pagina Cerca)

`score_query()` si aspetta un dict `note` con `distinctive_terms` (lista di
termini) e `note_text`. Per lo storico d'acquisto (Set A) questi termini
arrivano da `note_pipeline.generate_note()`. Per una nota scritta a mano
nella pagina Cerca (stile Set B, senza storico) li ricavo tokenizzando il
testo della nota con la stessa stopword-list di `note_pipeline.py`
(`core/recommender.py::derive_note_terms`) — non è la stessa procedura
esatta del Set A (niente soglia freq>=2), è un adattamento per l'uso live.
Da menzionare se questa pagina finisce nella tesi.

## Avvio locale

```bash
cd shopjournal_app
pip install -r requirements.txt
streamlit run app.py
```

Il database SQLite (`db/shopjournal.db`) viene creato automaticamente al
primo avvio.
