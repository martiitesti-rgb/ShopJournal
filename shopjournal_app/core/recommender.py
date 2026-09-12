
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from core.catalog import load_catalog_raw
from core.note_pipeline import tokenize, ALL_STOP
from core.scoring import score_query

VARIANTS = ["query_only", "query_notes", "query_notes_pop", "query_notes_pop_cue"]

EMPTY_NOTE = {"note_text": "", "distinctive_terms": []}


@dataclass
class Product:
    name: str
    price: float | None
    score: float
    id: str
    category: str


@st.cache_data(show_spinner="Carico il catalogo prodotti...")
def _load_catalog_cached() -> pd.DataFrame:
    return load_catalog_raw()


def derive_note_terms(note_text: str) -> list[str]:
   
    if not note_text or not note_text.strip():
        return []
    tokens = tokenize(note_text)
    seen = []
    for t in tokens:
        if t not in ALL_STOP and t not in seen:
            seen.append(t)
    return seen


def _run_scoring(query: str, note: dict, flags: list[str]) -> dict[str, list[Product]]:
    df = _load_catalog_cached()
    raw_results = score_query("live", query, note, df, flags)
    return {
        flag: [
            Product(name=r["title"], price=r["price"], score=r["score"], id=r["asin"], category=r["category"])
            for r in raw_results[flag]
        ]
        for flag in flags
    }

def compute_all_variants(query: str, note: dict = EMPTY_NOTE) -> dict[str, list[Product]]:
    return _run_scoring(query, note, VARIANTS)


def get_recommendations(query: str, note: dict = EMPTY_NOTE,
                         variant: str = "query_notes_pop_cue",
                         top_k: int = 10) -> list[Product]:
    if variant not in VARIANTS:
        raise ValueError(f"Variante sconosciuta: {variant}. Attese: {VARIANTS}")
    return _run_scoring(query, note, [variant])[variant][:top_k]


