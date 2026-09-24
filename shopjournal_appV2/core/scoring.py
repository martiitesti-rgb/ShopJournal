"""Adattatore tra l'app e la logica di scoring finale in core/final_evaluation.

La firma e il formato di ritorno di score_query() sono IDENTICI alla versione
precedente, cosi' recommender.py, Home.py e il resto dell'app non cambiano.
Tutto il calcolo (candidati, matchQuery, matchNotes, ratingPrior, cueScore,
ordinamento) viene da core/final_evaluation/, usato senza modifiche.
"""
import pandas as pd

from core.final_evaluation.cues import parse_price
from core.final_evaluation.scoring import CatalogItem, prepare_catalog, rank_pair


_PREPARED = {}  # cache: impronta del catalogo -> (RetrievalCatalog, metadati per asin)


def _prepare(df):
    """Converte il DataFrame nel RetrievalCatalog richiesto da rank_pair (una volta sola)."""
    key = (len(df), int(pd.util.hash_pandas_object(
        df[["asin", "title", "price", "average_rating"]], index=False).sum()))
    if key not in _PREPARED:
        items = [
            CatalogItem(
                parent_asin=row.asin,
                title=row.title if isinstance(row.title, str) else None,
                price=row.price,
                mean_rating=row.average_rating,
            )
            for row in df.itertuples(index=False)
        ]
        catalog = prepare_catalog(
            items,
            [item.parent_asin for item in items],
            membership_identity="data/catalog.parquet (tutti gli item)",
            catalog_identity="data/catalog.parquet",
        )
        meta = {
            str(row.asin).strip(): (row.title, row.price, row.category)
            for row in df.itertuples(index=False)
        }
        _PREPARED.clear()
        _PREPARED[key] = (catalog, meta)
    return _PREPARED[key]


def _variant_score(scored, flag):
    """Le quattro varianti dell'app come somme dei segnali del nuovo scorer."""
    if flag == "query_only":
        return scored.match_query
    elif flag == "query_notes":
        return scored.match_query + scored.match_notes
    elif flag == "query_notes_pop":
        return scored.base    # matchQuery + matchNotes + ratingPrior
    elif flag == "query_notes_pop_cue":
        return scored.full    # base + cueScore
    else:
        raise ValueError(f"Flag not found: {flag}")


def score_query(query_id, query_text, note, df, flags):
    catalog, meta = _prepare(df)
    pair = rank_pair(catalog, query_text, note["distinctive_terms"])

    results = {flag: [] for flag in flags}
    for scored in pair.full:
        title, raw_price, category = meta[scored.parent_asin]
        price = parse_price(raw_price)
        for flag in flags:
            results[flag].append({
                "asin": scored.parent_asin,
                "title": title,
                "price": float(price) if price is not None else None,
                "score": _variant_score(scored, flag),
                "category": category,
            })

    for flag in flags:
        # stesso ordinamento del nuovo scorer: punteggio decrescente, parent_asin crescente
        results[flag] = sorted(results[flag], key=lambda x: (-x["score"], x["asin"]))[:10]

    return results
