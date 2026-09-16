import re
import pandas as pd

from core.cue_extractor import extract_cues

QUERY_STOP = {
    "i", "im", "i'm", "a", "an", "the", "for", "to", "of", "and", "or",
    "need", "want", "looking", "some", "something", "good", "my", "me",
    "with", "is", "are", "it", "this", "that", "buy", "get",
}


def get_query_words(query_text):
    raw_words = re.split(r"[^a-z]+", query_text.lower())
    return [w for w in raw_words if w and w not in QUERY_STOP]


def matchQuery(query_words, title):
    title_lower = title.lower()
    if not query_words:
        return 0.0
    matches = sum(1 for w in query_words if w in title_lower)
    return matches / len(query_words)


def matchNotes(note_terms, title):
    title_lower = title.lower()
    if not note_terms:
        return 0.0
    matches = sum(1 for term in note_terms if term.lower() in title_lower)
    return matches / len(note_terms)


CUE_PRODUCT_TERMS = {
    "diet": ["organic", "vegan", "gluten-free", "gluten free", "healthy"],
    "urgency": ["instant", "ready to eat", "ready-to-eat", "quick", "microwave"],
    "gift": ["gift", "gift set", "gift box"],
}


def cueScore(cue_flags, product_title, product_price, compound=0.0, budget_threshold=10.0):
    title_lower = product_title.lower()
    active_cues = []
    for c, active in cue_flags.items():
        if active:
            active_cues.append(c)

    if not active_cues:
        return 0.0

    points = 0
    for cue in active_cues:
        if cue == "budget":
            if product_price is not None and product_price <= budget_threshold:
                points += 1
        elif cue in CUE_PRODUCT_TERMS:
            if any(term in title_lower for term in CUE_PRODUCT_TERMS[cue]):
                points += 1

    base_score = points / len(active_cues)
    # l'intensita' affettiva (positiva o negativa) rafforza il peso del segnale cue,
    # cosi' il compound score di VADER non viene piu' calcolato e scartato
    affect_weight = 1 + abs(compound)
    return base_score * affect_weight


def popularityScore(avg_rating):
    if avg_rating is None:
        return 0.0
    return avg_rating / 5.0


def sum_scores(scores, flag):
    if flag == "query_only":
        return scores["query"]
    elif flag == "query_notes":
        return scores["query"] + scores["notes"]
    elif flag == "query_notes_pop":
        return scores["query"] + scores["notes"] + scores["popularity"]
    elif flag == "query_notes_pop_cue":
        return scores["query"] + scores["notes"] + scores["popularity"] + scores["cue"]
    else:
        raise ValueError(f"Flag not found: {flag}")


def prefilter_candidates(query_words, note_terms, df, max_candidates=200):
    all_keywords = list(set(query_words + note_terms))
    if not all_keywords:
        return df.iloc[0:0]

    mask = df["title"].str.lower().str.contains(
        "|".join(map(re.escape, all_keywords)), na=False
    )
    matches = df[mask].copy()

    def count_matches(title):
        t = title.lower()
        return sum(1 for kw in all_keywords if kw in t)

    matches["match_count"] = matches["title"].apply(count_matches)
    matches = matches.sort_values("match_count", ascending=False).head(max_candidates)
    return matches.drop(columns=["match_count"])


def formatta_prezzo(value):
    if value is None or value == "None" or pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def score_query(query_id, query_text, note, df, flags):
    query_words = get_query_words(query_text)
    note_terms = note["distinctive_terms"]
    # sentiment e' scartato di proposito: e' compound_score discretizzato in 3 bucket,
    # quindi ridondante ora che compound entra direttamente in cueScore().
    # keywords resta non utilizzato: potenziale estensione futura per un matching
    # cue-prodotto piu' granulare (keyword specifica invece del solo flag di categoria).
    compound, sentiment, cue_flags, keywords = extract_cues(query_text, note["note_text"])

    candidates = prefilter_candidates(query_words, note_terms, df)
    candidates["price"] = candidates["price"].apply(formatta_prezzo)
    candidates = candidates[candidates["price"].notna()]

    results = {flag: [] for flag in flags}

    for _, row in candidates.iterrows():
    
        title = row["title"]
        price = formatta_prezzo(row["price"])
        avg_rating = row["average_rating"] if pd.notna(row.get("average_rating")) else None
        category= row["category"]
        scores = {
            "query": matchQuery(query_words, title),
            "notes": matchNotes(note_terms, title),
            "cue": cueScore(cue_flags, title, price, compound=compound),
            "popularity": popularityScore(avg_rating),
        }

        for flag in flags:
            total = sum_scores(scores, flag)
            results[flag].append({
                "asin": row["asin"],
                "title": title,
                "price": price,
                "score": total,
                "category": category
            })

    for flag in flags:
        results[flag] = sorted(results[flag], key=lambda x: x["score"], reverse=True)[:10]

    return results