
import re
import math
from collections import Counter

SKLEARN_STOP = set("""
a about above after again against all am an and any are aren't as at be
because been before being below between both but by can can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for
from further get got had hadn't has hasn't have haven't having he he'd
he'll he's her here here's hers herself him himself his how how's i i'd
i'll i'm i've if in into is isn't it it's its itself let's me more most
mustn't my myself no nor not of off on once only or other ought our ours
ourselves out over own same shan't she she'd she'll she's should shouldn't
so some such than that that's the their theirs them themselves then there
there's these they they'd they'll they're they've this those through to
too under until up very was wasn't we we'd we'll we're we've were weren't
what what's when when's where where's which while who who's whom why why's
with won't would wouldn't you you'd you'll you're you've your yours
yourself yourselves will
""".split())

GROCERY_FILLERS = {
    "food", "snack", "item", "product", "pack", "box", "bag", "jar", "set",
    "selection", "assorted", "mix", "flavor", "original", "classic", "new",
    "premium", "gourmet", "gift", "hamper", "basket", "collection",
    "assortment", "large", "small", "mini", "pack-of", "count",
}
GENERIC_ADJ = {"good", "best", "top", "fresh", "real", "natural"}
ALL_STOP = SKLEARN_STOP | GROCERY_FILLERS | GENERIC_ADJ


def tokenize(text: str) -> list[str]:
    tokens = re.split(r"[\s\-\/\'\"\,\.\;\:\!\?\(\)\&\#]+", text.lower())
    return [t for t in tokens if len(t) >= 3]


def is_meas(t: str) -> bool:
    return bool(re.match(r"^\d+[\.\d]*(oz|ct|lb|lbs|ml|g|kg|pct|srv|fl)$", t))


def is_num(t: str) -> bool:
    return bool(re.match(r"^\d+[\.\d]*$", t))


def extract_terms(titles: list[str]):
   
    all_tokens = []
    for title in titles:
        toks = tokenize(title)
        toks = [t for t in toks if t not in ALL_STOP and not is_meas(t) and not is_num(t)]
        all_tokens.extend(toks)

    freq = Counter(all_tokens)
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))

    freq2 = [(t, c) for t, c in ranked if c >= 2]
    freq1 = [(t, c) for t, c in ranked if c == 1]

    if len(freq2) >= 5:
        terms = freq2[:8]
    else:
        needed = 5 - len(freq2)
        terms = freq2 + freq1[:needed]

    return terms, freq


def price_stats(prices: list[float]):
    s = sorted(prices)
    n = len(s)
    median = s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2
    mx = max(s)
    mean = sum(s) / n
    var = sum((x - mean) ** 2 for x in s) / n
    return s, round(median, 2), round(mx, 2), round(mean, 2), round(math.sqrt(var), 2)


def subcat_top3(subcats: list[str]):
    freq = Counter(subcats)
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return ranked[:3]


def price_tier(median: float) -> str:
    if median < 10:
        return "low-price"
    if median <= 25:
        return "mid-price"
    return "premium"


def generate_note(purchase_history: list[tuple[str, str, float, int]]) -> dict:
    
    subcats = [item[0] for item in purchase_history]
    titles = [item[1] for item in purchase_history]
    prices = [item[2] for item in purchase_history]

    top3 = subcat_top3(subcats)
    terms, _freq = extract_terms(titles)
    _sorted_p, median, mx, mean, std = price_stats(prices)
    tier = price_tier(median)

    sc_list = [sc.lower() for sc, _ in top3]
    sc_str = ", ".join(sc_list[:-1]) + f", and {sc_list[-1]}" if len(sc_list) > 1 else sc_list[0]
    t_str = ", ".join(t for t, _ in terms)

    note_text = f"I usually buy {sc_str}. I prefer {t_str}."

    return {
        "note_text": note_text,
        "price_profile": {"median": median, "max": mx, "mean": mean, "std": std},
        "price_tier": tier,
        "top_subcategories": top3,
        "distinctive_terms": terms,
    }
