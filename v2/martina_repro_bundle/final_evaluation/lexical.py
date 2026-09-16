"""Frozen shared lexical resources. Spans index the normalized text, not raw text."""

from dataclasses import dataclass
import re
from types import MappingProxyType
import unicodedata


STOPWORDS = frozenset("""
a am an and are be buy can could do does for from get good have i in is it
looking me my need of on or please some something that the this to want with would
""".split())

# This table is source-controlled, never learned or supplied by a caller.
CONTRACTIONS = MappingProxyType({
    "i'm": "i am", "you're": "you are", "we're": "we are", "they're": "they are",
    "he's": "he is", "she's": "she is", "it's": "it is", "that's": "that is",
    "there's": "there is", "here's": "here is", "what's": "what is",
    "who's": "who is", "where's": "where is", "when's": "when is",
    "why's": "why is", "how's": "how is",
    "i've": "i have", "you've": "you have", "we've": "we have",
    "they've": "they have", "could've": "could have", "should've": "should have",
    "would've": "would have", "might've": "might have", "must've": "must have",
    "i'll": "i will", "you'll": "you will", "he'll": "he will",
    "she'll": "she will", "it'll": "it will", "we'll": "we will",
    "they'll": "they will", "that'll": "that will", "there'll": "there will",
    "who'll": "who will", "what'll": "what will",
    "i'd": "i would", "you'd": "you would", "he'd": "he would",
    "she'd": "she would", "it'd": "it would", "we'd": "we would",
    "they'd": "they would", "that'd": "that would", "there'd": "there would",
    "who'd": "who would", "what'd": "what would",
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "can't": "can not", "cannot": "can not", "couldn't": "could not",
    "won't": "will not", "wouldn't": "would not", "shouldn't": "should not",
    "isn't": "is not", "aren't": "are not", "wasn't": "was not",
    "weren't": "were not", "haven't": "have not", "hasn't": "has not",
    "hadn't": "had not", "mustn't": "must not", "needn't": "need not",
    "mightn't": "might not", "shan't": "shall not",
    "let's": "let us", "y'all": "you all",
    "i'd've": "i would have", "you'd've": "you would have",
    "he'd've": "he would have", "she'd've": "she would have",
    "we'd've": "we would have", "they'd've": "they would have",
    "couldn't've": "could not have", "shouldn't've": "should not have",
    "wouldn't've": "would not have", "mustn't've": "must not have",
})

NEGATORS = frozenset({"no", "not", "never", "without", "avoid"})
ARTICLES = frozenset({"a", "an", "the"})
DIET_PROPERTIES = (
    "vegan", "vegetarian", "gluten free", "dairy free", "nut free",
    "peanut free", "sugar free", "organic", "healthy",
)
DIET_ALIASES = MappingProxyType({
    f"{negator} {target}": prop
    for negator in ("no", "without")
    for target, prop in (
        ("gluten", "gluten free"), ("dairy", "dairy free"),
        ("nuts", "nut free"), ("peanuts", "peanut free"), ("sugar", "sugar free"),
    )
})
CUE_EXPRESSIONS = MappingProxyType({
    "DIET": DIET_PROPERTIES + ("diet", "allergy") + tuple(DIET_ALIASES),
    "GIFT": ("gift", "present", "birthday", "anniversary"),
    "URGENCY": ("urgent", "fast", "quick", "now", "today", "tomorrow",
                "last minute", "emergency"),
    "BUDGET": ("cheap", "affordable", "budget", "not expensive", "discount", "sale"),
})
GIFT_SUPPORT = ("gift", "gift set", "gift box")
URGENCY_SUPPORT = ("instant", "ready to eat", "quick", "microwave")
PHRASES = tuple(sorted({
    tuple(expression.split())
    for expressions in (*CUE_EXPRESSIONS.values(), GIFT_SUPPORT, URGENCY_SUPPORT)
    for expression in expressions if " " in expression
}, key=lambda unit: (-len(unit), unit)))

_APOSTROPHES = str.maketrans({c: "'" for c in "\u2018\u2019\u201b\u02bc\uff07"})
_QUOTES = str.maketrans({c: '"' for c in "\u201c\u201d\u201e\u201f"})
_WORDS = re.compile(r"[^\W_]+(?:'[^\W_]+)*", re.UNICODE)
_QUOTED = re.compile(r"(?<!\w)([\"'])(.+?)\1(?!\w)")


def folded_surface(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("Lexical input must be text.")
    return unicodedata.normalize("NFKC", text).casefold().translate(_APOSTROPHES).translate(_QUOTES)


def normalize(text: str) -> str:
    surface = folded_surface(text)
    surface = "".join(
        " " if unicodedata.category(c) == "Pd" or c in "\u2212\u00ad" else c
        for c in surface
    )
    return _WORDS.sub(lambda match: CONTRACTIONS.get(match[0], match[0]), surface)


def validate_query_contractions(text: str) -> None:
    """Reject unknown auxiliary/negative contractions before admitting a query.

    Possessives stay whole (e.g. mom's), so they never create an 's' fragment.
    Ambiguous 's and 'd entries above have frozen is/would expansions.
    """
    for word in _WORDS.findall(folded_surface(text)):
        if ("'" in word and word not in CONTRACTIONS
                and (word.endswith(("'m", "'re", "'ve", "'ll", "'d", "n't"))
                     or word.count("'") > 1)):
            raise ValueError(f"Contraction absent from frozen resource: {word}")


@dataclass(frozen=True)
class LexicalText:
    text: str
    tokens: tuple[str, ...]
    spans: tuple[tuple[int, int], ...]


def tokenize(text: str) -> LexicalText:
    text = normalize(text)
    matches = tuple(_WORDS.finditer(text))
    return LexicalText(text, tuple(m[0] for m in matches), tuple(m.span() for m in matches))


def occurrences(doc: LexicalText, unit: tuple[str, ...]) -> tuple[tuple[int, int], ...]:
    """Return complete-token matches as half-open token-index spans."""
    if not unit:
        return ()
    return tuple((i, i + len(unit)) for i in range(len(doc.tokens) - len(unit) + 1)
                 if doc.tokens[i:i + len(unit)] == unit)


def _atoms(doc: LexicalText) -> dict[int, int]:
    quoted = {}
    for match in _QUOTED.finditer(doc.text):
        inside = [i for i, (start, end) in enumerate(doc.spans)
                  if start >= match.start(2) and end <= match.end(2)]
        if inside:
            quoted[inside[0]] = inside[-1] + 1
    atoms = {}
    i = 0
    while i < len(doc.tokens):
        ends = [i + 1, quoted.get(i, i + 1)]
        ends.extend(i + len(p) for p in PHRASES if doc.tokens[i:i + len(p)] == p)
        atoms[i] = max(ends)
        i = atoms[i]
    return atoms


def negation_spans(doc: LexicalText) -> tuple[tuple[int, int], ...]:
    atoms = _atoms(doc)
    spans = []
    for i, token in enumerate(doc.tokens):
        if token not in NEGATORS:
            continue
        j = i + 1
        if j < len(doc.tokens) and doc.tokens[j] in ARTICLES:
            j += 1
        while j < len(doc.tokens) and doc.tokens[j] in STOPWORDS and j not in atoms:
            j += 1
        # Skip standalone stopwords, but preserve a phrase beginning with one.
        while (j < len(doc.tokens) and doc.tokens[j] in STOPWORDS
               and atoms.get(j, j + 1) == j + 1):
            j += 1
        if j < len(doc.tokens):
            spans.append((i, atoms.get(j, j + 1)))
    return tuple(spans)


def suppressed(doc: LexicalText, start: int, end: int, *, exception: bool = False) -> bool:
    return any(left <= start < right and not (exception and left == start and right == end)
               for left, right in negation_spans(doc))


def query_units(doc: LexicalText, excluded_spans: tuple[tuple[int, int], ...] = ()) -> tuple[tuple[str, ...], ...]:
    """Longest-leftmost phrases, bounded negation, then unique informative units."""
    excluded = {i for i, (a, b) in enumerate(doc.spans)
                if any(a < end and b > start for start, end in excluded_spans)}
    atoms = _atoms(doc)
    negatives = dict(negation_spans(doc))
    units = set()
    i = 0
    while i < len(doc.tokens):
        if i in excluded:
            i += 1
            continue
        end = max(atoms.get(i, i + 1), negatives.get(i, i + 1))
        if any(j in excluded for j in range(i, end)):
            i = end
            continue
        unit = doc.tokens[i:end]
        if len(unit) > 1 or unit[0] not in STOPWORDS:
            units.add(unit)
        i = end
    return tuple(sorted(units))


def note_only_tokens(distinctive_terms, query: LexicalText) -> tuple[str, ...]:
    """Project frozen term/count pairs or term strings; counts never weight coverage."""
    if isinstance(distinctive_terms, str):
        raise TypeError("distinctive_terms must be a sequence or term/count mapping.")
    terms = distinctive_terms.keys() if hasattr(distinctive_terms, "keys") else distinctive_terms
    tokens = set()
    for entry in terms:
        if isinstance(entry, str):
            term = entry
        elif isinstance(entry, (tuple, list)) and len(entry) == 2 and isinstance(entry[0], str):
            term = entry[0]
        elif isinstance(entry, dict) and set(entry) == {"term", "count"} and isinstance(entry["term"], str):
            term = entry["term"]
        else:
            raise TypeError("Expected term text or a (term, count) entry.")
        tokens.update(tokenize(term).tokens)
    return tuple(sorted(tokens - STOPWORDS - set(query.tokens)))
