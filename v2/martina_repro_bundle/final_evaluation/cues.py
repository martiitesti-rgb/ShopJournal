"""Frozen query-only detections and executable title/price compatibility."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re

from .lexical import (
    CUE_EXPRESSIONS, DIET_ALIASES, DIET_PROPERTIES, GIFT_SUPPORT, URGENCY_SUPPORT,
    LexicalText, folded_surface, occurrences, suppressed, tokenize,
    validate_query_contractions,
)


_AMOUNT = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]{1,2})?"
_MONEY = rf"\$\s*(?P<amount>{_AMOUNT})(?![\w']|[.,][0-9])"
_PREFIX_BOUND = re.compile(
    rf"(?<![\w'])(?P<operator>under|below|less\s+than|max|up\s+to)\s*{_MONEY}"
)
_SUFFIX_BOUND = re.compile(rf"(?<![\w'$.,]){_MONEY}\s+or\s+less(?![\w'])")
_PRICE = re.compile(rf"(?:\$\s*)?({_AMOUNT})")


@dataclass(frozen=True)
class BudgetBound:
    amount: Decimal
    strict: bool
    start: int
    end: int
    expression: str


@dataclass(frozen=True)
class BudgetParse:
    bounds: tuple[BudgetBound, ...]
    rejected: tuple[tuple[BudgetBound, str], ...]

    @property
    def tightest(self) -> BudgetBound | None:
        return min(self.bounds, key=lambda b: (b.amount, not b.strict, b.start), default=None)

    @property
    def lexical_spans(self) -> tuple[tuple[int, int], ...]:
        return tuple(sorted({(b.start, b.end) for b in self.bounds}
                            | {(b.start, b.end) for b, _ in self.rejected}))


def parse_price(value) -> Decimal | None:
    """A finite nonnegative USD price; strings allow $ and correctly grouped commas."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        match = _PRICE.fullmatch(value.strip())
        if not match:
            return None
        value = match[1].replace(",", "")
    elif not isinstance(value, (int, float, Decimal)):
        return None
    try:
        price = Decimal(str(value))
    except InvalidOperation:
        return None
    return price if price.is_finite() and price >= 0 else None


def explicit_usd_amounts(text: str) -> tuple[Decimal, ...]:
    """Literal amounts for independent first-version annotations, without cue feedback."""
    return tuple(Decimal(match["amount"].replace(",", ""))
                 for match in re.finditer(_MONEY, folded_surface(text)))


def _unsupported_budget_context(raw: str, doc: LexicalText, bounds: list[BudgetBound]) -> str | None:
    """Conservative lexical rejection of explicitly unsupported interpretations.

    No attempt is made to infer units, currency conversion, basket size, or intent.
    Rejection applies to the query's bounds together; callers retain the reason.
    """
    surface = folded_surface(raw)
    if re.search(r"\$\s*[-‐‑‒–—−]\s*[0-9]|[-‐‑‒–—−]\s*\$\s*[0-9]", surface):
        return "negative amount"
    if re.search(r"[€£¥₹₩₽]|\b(?:eur|euro|euros|gbp|cad|aud|nzd|jpy|cny|inr|pounds|yen)\b|(?:ca|a|nz|c)\$", surface):
        return "non-USD or mixed currencies"
    if re.search(r"\b(?:basket|cart)\s+(?:total|cost|price)\b|\b(?:total|combined)\s+(?:basket|cart|cost|price|spend)\b", doc.text):
        return "basket total"
    for bound in bounds:
        before, after = doc.text[:bound.start], doc.text[bound.end:]
        if (re.search(r"\b(?:total|combined|altogether)\s*[:,]?\s*$", before)
                or re.match(r"\s*[,;]?\s*(?:(?:(?:in\s+)?total|combined|altogether)\b|for\s+(?:(?:the|my|whole|entire)\s+)?(?:basket|cart|both|all|two|three|[0-9]+)\b)", after)):
            return "basket total"
        if (re.search(r"\b(?:per\s+[a-z]+|unit\s+price)\s*[:,]?\s*$", before)
                or re.match(r"\s*[,;]?\s*(?:/\s*[a-z0-9]|(?:per|(?:for\s+)?each|apiece)\b)", after)):
            return "unit-price interpretation"
        if re.match(r"\s+[0-9]", after):
            return "ambiguous spaced amount"
        if re.match(r"\s+(?:a|an)\s+(?:unit|item|pack|box|bag|bottle|serving|pound|ounce|gram|kilogram|litre|liter)\b", after):
            return "unit-price interpretation"
        if re.match(r"\s+or\s+(?:more|higher|above)\b", after):
            return "ambiguous bound"
        if (re.search(r"\b(?:about|around|approximately|roughly|maybe)\s*$", before)
                or re.match(r"\s+(?:approximately|roughly)\b", after)):
            return "ambiguous bound"
    if re.search(r"\bbetween\s+\$?\s*[0-9][0-9,.]*\s+and\s+\$?\s*[0-9]|\$\s*[0-9][0-9,.]*\s*(?:[-‐‑‒–—−]|\bto\b)\s*\$?\s*[0-9]", surface):
        return "range"
    ordered = sorted(bounds, key=lambda b: b.start)
    if any(re.search(r"\bor\b", doc.text[a.end:b.start]) for a, b in zip(ordered, ordered[1:])):
        return "alternative bounds"
    money = tuple(re.finditer(_MONEY, doc.text))
    for a, b in zip(money, money[1:]):
        gap = "".join(doc.text[i] if not any(bound.start <= i < bound.end for bound in bounds) else " "
                      for i in range(a.end(), b.start()))
        if re.search(r"\bor\b", gap):
            return "alternative amounts"
    return None


def parse_budget(text: str) -> BudgetParse:
    doc = tokenize(text)
    found = []
    for pattern in (_PREFIX_BOUND, _SUFFIX_BOUND):
        for match in pattern.finditer(doc.text):
            operator = " ".join(match.groupdict().get("operator", "or less").split())
            found.append(BudgetBound(
                Decimal(match["amount"].replace(",", "")),
                operator in {"under", "below", "less than"},
                match.start(), match.end(), match[0],
            ))
    found.sort(key=lambda b: (b.start, b.end))
    # e.g. 'under $10 or less' expresses two incompatible comparison operators.
    overlap = any(a.end > b.start for a, b in zip(found, found[1:]))
    context_reason = "overlapping/ambiguous operators" if overlap else _unsupported_budget_context(text, doc, found)
    accepted, rejected = [], []
    for bound in found:
        indices = [i for i, (start, end) in enumerate(doc.spans)
                   if start < bound.end and end > bound.start]
        is_negated = bool(indices) and suppressed(doc, indices[0], indices[-1] + 1)
        reason = "bounded negation" if is_negated else context_reason
        if reason:
            rejected.append((bound, reason))
        else:
            accepted.append(bound)
    return BudgetParse(tuple(accepted), tuple(rejected))


@dataclass(frozen=True)
class CueMatch:
    category: str
    expression: str
    start: int
    end: int
    suppressed: bool
    reason: str | None = None


@dataclass(frozen=True)
class CueExtraction:
    normalized_query: str
    detected: frozenset[str]
    executable: frozenset[str]
    diet_properties: tuple[str, ...]
    matches: tuple[CueMatch, ...]
    budget: BudgetParse


def _expression_matches(doc: LexicalText, expressions):
    for expression in expressions:
        exception = expression in DIET_ALIASES or expression == "not expensive"
        for start, end in occurrences(doc, tuple(expression.split())):
            yield expression, start, end, suppressed(doc, start, end, exception=exception)


def extract_cues(query: str) -> CueExtraction:
    validate_query_contractions(query)
    doc = tokenize(query)
    budget = parse_budget(query)
    detected, properties, matches = set(), set(), []
    for category, expressions in CUE_EXPRESSIONS.items():
        for expression, start, end, blocked in _expression_matches(doc, expressions):
            matches.append(CueMatch(category, expression, doc.spans[start][0], doc.spans[end - 1][1],
                                    blocked, "bounded negation" if blocked else None))
            if not blocked:
                detected.add(category)
                if category == "DIET":
                    prop = DIET_ALIASES.get(expression, expression)
                    if prop in DIET_PROPERTIES:
                        properties.add(prop)
    for bound in budget.bounds:
        matches.append(CueMatch("BUDGET", bound.expression, bound.start, bound.end, False))
        detected.add("BUDGET")
    for bound, reason in budget.rejected:
        matches.append(CueMatch("BUDGET", bound.expression, bound.start, bound.end, True, reason))
    executable = detected & {"GIFT", "URGENCY"}
    if properties:
        executable.add("DIET")
    if budget.bounds:
        executable.add("BUDGET")
    return CueExtraction(doc.text, frozenset(detected), frozenset(executable), tuple(sorted(properties)),
                         tuple(sorted(matches, key=lambda m: (m.start, m.end, m.category, m.expression))), budget)


def compatibility(cues: CueExtraction, title: str | None, price) -> tuple[tuple[str, int], ...]:
    """One binary value per executable category; missing evidence stays in the denominator."""
    doc = tokenize(title or "")
    support = set()
    for expression, _, _, blocked in _expression_matches(doc, DIET_PROPERTIES + tuple(DIET_ALIASES)):
        if not blocked:
            support.add(DIET_ALIASES.get(expression, expression))
    # Any recognized negation of a property's support defeats that property,
    # including contradictory titles containing both positive and negative mentions.
    for expression, _, _, blocked in _expression_matches(doc, DIET_PROPERTIES + tuple(DIET_ALIASES)):
        if blocked:
            support.discard(DIET_ALIASES.get(expression, expression))
    values = {}
    if "DIET" in cues.executable:
        values["DIET"] = int(set(cues.diet_properties) <= support)
    for category, expressions in (("GIFT", GIFT_SUPPORT), ("URGENCY", URGENCY_SUPPORT)):
        if category in cues.executable:
            values[category] = int(any(not blocked for _, _, _, blocked in _expression_matches(doc, expressions)))
    if "BUDGET" in cues.executable:
        amount = parse_price(price)
        values["BUDGET"] = int(amount is not None and all(
            amount < bound.amount if bound.strict else amount <= bound.amount
            for bound in cues.budget.bounds
        ))
    return tuple(sorted(values.items()))


def cue_score(cues: CueExtraction, title: str | None, price) -> float:
    values = compatibility(cues, title, price)
    return sum(value for _, value in values) / len(values) if values else 0.0
