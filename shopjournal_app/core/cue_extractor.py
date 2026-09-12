
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

nltk.download("vader_lexicon", quiet=True)
_analyzer = SentimentIntensityAnalyzer()

INTENT_KEYWORDS = {
    "urgency": ["urgent", "fast", "quick", "now", "today", "tomorrow",
                "last minute", "emergency"],
    "budget": ["cheap", "budget", "not expensive", "affordable", "discount",
               "under", "max", "sale", "price"],
    "diet": ["vegetarian", "vegan", "gluten-free", "allergy", "healthy", "diet"],
    "gift": ["gift", "present", "birthday", "for my", "anniversary",
             "mom", "dad", "friend"],
}


def extract_cues(query: str, notes: str):
    
    combined_text = f"{query} {notes}".strip().lower()
    if not combined_text:
        return 0.0, "neutral", {k: False for k in INTENT_KEYWORDS}, []

    scores = _analyzer.polarity_scores(combined_text)
    compound_score = scores["compound"]

    if compound_score >= 0.05:
        sentiment_label = "positive"
    elif compound_score <= -0.05:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"

    keywords_found = []
    intent_flags = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        trovato = False
        for keyword in keywords:
            if keyword in combined_text:
                keywords_found.append(keyword)
                trovato = True
                break
        intent_flags[intent] = trovato

    return compound_score, sentiment_label, intent_flags, keywords_found
