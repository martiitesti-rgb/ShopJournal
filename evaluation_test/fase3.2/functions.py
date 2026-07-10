import re
import pandas as pd

QUERY_STOP = {
    "i", "im", "i'm", "a", "an", "the", "for", "to", "of", "and", "or",
    "need", "want", "looking", "some", "something", "good", "my", "me",
    "with", "is", "are", "it", "this", "that", "buy", "get"
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

def cueScore(cue_flags, product_title, product_price, budget_threshold=10.0):
    title_lower = product_title.lower()
    # creo una lista di cue attivi
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

    return points / len(active_cues)  

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
        return df.iloc[0:0]  # nessuna parola chiave, nessun candidato
    
    mask = df["title"].str.lower().str.contains(
        "|".join(map(re.escape, all_keywords)), na=False
    )
    return df[mask].head(max_candidates).copy()

from nltk.sentiment.vader import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

#copia esatta di quella presente nel file extracting_cues.ipynb
def extract_cues(query, notes):
    combined_text = f"{query} {notes}".strip().lower()
    if not combined_text:
        return 0.0, "neutral", {"urgency": False, "budget": False, "diet": False, "gift": False}, []

    scores = analyzer.polarity_scores(combined_text)
    compound_score = scores['compound']

    if compound_score >= 0.05:
        sentiment_label = "positive"
    elif compound_score <= -0.05:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"

    intent_keywords = {
        "urgency": ["urgent", "fast", "quick", "now", "today", "tomorrow", "last minute", "emergency"],
        "budget": ["cheap", "budget", "not expensive", "affordable", "discount", "under", "max", "sale", "price"],
        "diet": ["vegetarian", "vegan", "gluten-free", "allergy", "healthy", "diet"],
        "gift": ["gift", "present", "birthday", "for my", "anniversary", "mom", "dad", "friend"]
    }

    keywords_found = []
    intent_flags = {}
    for intent, keywords in intent_keywords.items():
        trovato = False
        for keyword in keywords:
            if keyword in combined_text:
                keywords_found.append(keyword)
                trovato = True
                break
        intent_flags[intent] = trovato
    return compound_score, sentiment_label, intent_flags, keywords_found

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
    compound, sentiment, cue_flags, keywords = extract_cues(query_text, note["note_text"])
    
    candidates = prefilter_candidates(query_words, note_terms, df)
    
    results = {flag: [] for flag in flags}
    
    for _, row in candidates.iterrows():
        title = row["title"]
        price = formatta_prezzo(row["price"])
        avg_rating = row["average_rating"] if pd.notna(row.get("average_rating")) else None
        
        scores = {
            "query": matchQuery(query_words, title),
            "notes": matchNotes(note_terms, title),
            "cue": cueScore(cue_flags, title, price),
            "popularity": popularityScore(avg_rating),
        }
        
        for flag in flags:
            total = sum_scores(scores, flag)
            results[flag].append({
                "asin": row["asin"],
                "title": title,
                "price": price,
                "score": total,
            })
    
    for flag in flags:
        results[flag] = sorted(results[flag], key=lambda x: x["score"], reverse=True)[:10]
    
    return results   