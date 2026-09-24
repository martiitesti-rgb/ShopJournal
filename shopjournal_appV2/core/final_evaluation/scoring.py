"""One canonical Base/Full scorer. No caller-supplied coefficients or candidate cap."""

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import platform

from . import __version__
from .cues import CueExtraction, cue_score, extract_cues
from .lexical import LexicalText, note_only_tokens, occurrences, query_units, tokenize


CANDIDATE_CAP = 200


def canonical_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A nonempty canonical parent_asin is required; asin is not an alias.")
    return value.strip()


def valid_rating(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        rating = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return rating if math.isfinite(rating) and 1 <= rating <= 5 else None


@dataclass(frozen=True)
class CatalogItem:
    parent_asin: str
    title: str | None = None
    price: object = None
    mean_rating: object = None

    def __post_init__(self):
        object.__setattr__(self, "parent_asin", canonical_id(self.parent_asin))
        if self.title is not None and not isinstance(self.title, str):
            raise TypeError("title must be text or None.")
        for value in (self.price, self.mean_rating):
            if isinstance(value, (dict, list, set)):
                raise TypeError("Catalog prices and mean ratings must be scalar values.")


@dataclass(frozen=True)
class RetrievalCatalog:
    items: tuple[CatalogItem, ...]
    rating_mean: float
    membership_identity: str
    catalog_identity: str
    catalog_sha256: str | None


def prepare_catalog(items, retrieval_parent_asins, *, membership_identity: str,
                    catalog_identity: str, catalog_sha256: str | None = None) -> RetrievalCatalog:
    """Bind a complete, already restricted catalog to the supplied frozen membership.

    The caller authenticates the committed membership list and metadata source.
    This function never loads a full catalog, partitions data, or silently filters it.
    """
    if not isinstance(membership_identity, str) or not membership_identity.strip():
        raise ValueError("Record the retrieval membership identity separately.")
    if not isinstance(catalog_identity, str) or not catalog_identity.strip():
        raise ValueError("Record the catalog source/version identity separately.")
    if catalog_sha256 is not None and (len(catalog_sha256) != 64
                                       or any(c not in "0123456789abcdefABCDEF" for c in catalog_sha256)):
        raise ValueError("catalog_sha256 must be a SHA-256 hexadecimal digest.")
    members = {canonical_id(value) for value in retrieval_parent_asins}
    unique = {}
    for item in items:
        if not isinstance(item, CatalogItem):
            raise TypeError("Use CatalogItem with explicit parent_asin, title, price, mean_rating fields.")
        if item.parent_asin not in members:
            raise ValueError("Catalog contains an item outside the bound retrieval membership.")
        if item.parent_asin in unique and unique[item.parent_asin] != item:
            raise ValueError(f"Conflicting records for canonical ID {item.parent_asin}.")
        unique[item.parent_asin] = item
    if set(unique) != members:
        raise ValueError("Full retrieval membership is required to freeze the catalog-level mean.")
    ordered = tuple(unique[key] for key in sorted(unique))
    ratings = [r for item in ordered if (r := valid_rating(item.mean_rating)) is not None]
    if not ratings:
        raise ValueError("No valid retrieval-catalog mean rating; execution cannot proceed.")
    return RetrievalCatalog(ordered, math.fsum(ratings) / len(ratings), membership_identity,
                            catalog_identity, catalog_sha256)


@dataclass(frozen=True)
class QueryRepresentation:
    query: LexicalText
    query_units: tuple[tuple[str, ...], ...]
    note_only: tuple[str, ...]
    cues: CueExtraction


def represent_query(query_text: str, distinctive_terms) -> QueryRepresentation:
    cues = extract_cues(query_text)
    query = tokenize(query_text)
    return QueryRepresentation(query, query_units(query, cues.budget.lexical_spans),
                               note_only_tokens(distinctive_terms, query), cues)


def candidates(catalog: RetrievalCatalog, query: QueryRepresentation) -> tuple[CatalogItem, ...]:
    if not isinstance(catalog, RetrievalCatalog):
        raise TypeError("Prepare and bind the retrieval catalog before candidate generation.")
    union = tuple(sorted(set(query.query_units) | {(token,) for token in query.note_only}))
    if not union:
        return ()
    matches = []
    for item in catalog.items:
        title = tokenize(item.title or "")
        count = sum(bool(occurrences(title, unit)) for unit in union)
        if count:
            matches.append((count, item))
    matches.sort(key=lambda match: (-match[0], match[1].parent_asin))
    return tuple(item for _, item in matches[:CANDIDATE_CAP])


def _coverage(title: LexicalText, units: tuple[tuple[str, ...], ...]) -> float:
    return sum(bool(occurrences(title, unit)) for unit in units) / len(units) if units else 0.0


@dataclass(frozen=True)
class ScoredItem:
    parent_asin: str
    match_query: float
    match_notes: float
    rating_prior: float
    cue_score: float
    base: float
    full: float


@dataclass(frozen=True)
class RankingPair:
    candidate_ids: tuple[str, ...]
    base: tuple[ScoredItem, ...]
    full: tuple[ScoredItem, ...]


def rank_pair(catalog: RetrievalCatalog, query_text: str, distinctive_terms) -> RankingPair:
    """Synthetic-testable primitive; real execution also requires sealed inputs/record."""
    query = represent_query(query_text, distinctive_terms)
    shared = candidates(catalog, query)
    scored = []
    for item in shared:
        title = tokenize(item.title or "")
        match_query = _coverage(title, query.query_units)
        match_notes = _coverage(title, tuple((token,) for token in query.note_only))
        rating = valid_rating(item.mean_rating)
        rating_prior = (catalog.rating_mean if rating is None else rating) / 5.0
        cue = cue_score(query.cues, item.title, item.price)
        base = (match_query + match_notes) + rating_prior
        full = base + cue
        scored.append(ScoredItem(item.parent_asin, match_query, match_notes, rating_prior, cue, base, full))
    return RankingPair(tuple(item.parent_asin for item in shared),
                       tuple(sorted(scored, key=lambda row: (-row.base, row.parent_asin))),
                       tuple(sorted(scored, key=lambda row: (-row.full, row.parent_asin))))


def implementation_identity() -> dict:
    """Code/resource hashes and runtime facts for a later frozen execution record."""
    root = Path(__file__).parent
    names = ("__init__.py", "__main__.py", "lexical.py", "cues.py", "scoring.py",
             "metrics.py", "prepare_final_queries.py")
    return {
        "package": __version__, "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "dependencies": "Python standard library only",
        "source_sha256": {f"final_evaluation/{name}": hashlib.sha256((root / name).read_bytes()).hexdigest()
                          for name in names},
        "coefficients": {"matchQuery": 1, "matchNotes": 1, "ratingPrior": 1, "cueScore": 1},
        "candidate_cap": CANDIDATE_CAP,
        "candidate_order": "distinct union match count descending, parent_asin ascending",
        "ranking_order": "unrounded total descending, parent_asin ascending",
    }
