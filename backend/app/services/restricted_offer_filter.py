from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class RestrictedOfferMatch:
    category: str
    term: str

    @property
    def reason(self) -> str:
        return f"restricted_{self.category}:{self.term}"


# Product-level safety filter. It should block actual pork/ham products and
# alcoholic drinks, but it must not block a whole department store or unrelated
# products such as "wine red" clothing, "champagne" color dresses, ham-radio
# equipment, alcohol-free perfume, wine cabinets, or bottle openers.

_STRONG_PORK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (term, re.compile(pattern, re.IGNORECASE))
    for term, pattern in (
        ("jamon", r"\bjam[oó]n(?:es)?\b"),
        ("chorizo", r"\bchorizo(?:s)?\b"),
        ("salchichon", r"\bsalchich[oó]n(?:es)?\b"),
        ("lomo embuchado", r"\blomo\s+embuchado\b"),
        ("paleta iberica", r"\bpaleta\s+ib[eé]rica\b"),
        ("prosciutto", r"\bprosciutto\b"),
        ("panceta", r"\bpanceta\b"),
        ("sobrasada", r"\bsobrasada\b"),
        ("fuet", r"\bfuet\b"),
        ("charcuteria", r"\bcharcuter[ií]a\b"),
        ("embutido", r"\bembutido(?:s)?\b"),
    )
)

_CONTEXTUAL_PORK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (term, re.compile(pattern, re.IGNORECASE))
    for term, pattern in (
        ("ham", r"\bham\b"),
        ("pork", r"\bpork\b"),
        ("bacon", r"\bbacon\b"),
        ("gammon", r"\bgammon\b"),
        ("iberico", r"\bib[eé]rico(?:s|a|as)?\b"),
    )
)

_MEAT_CONTEXT_RE = re.compile(
    r"\b("
    r"meat|deli|gourmet|food|foods|sausage|sausages|cured|smoked|sliced|slice|strips|"
    r"bellota|serrano|iberian|iberico|iberica|raza|fisan|jamon|paleta|lomo|embutido|charcuteria|"
    r"carne|cerdo|curado|ahumado|loncha|lonchas"
    r")\b",
    re.IGNORECASE,
)

_HAM_RADIO_CONTEXT_RE = re.compile(
    r"\b(ham\s+radio|radio|antenna|balun|coaxial|coax|uhf|vhf|hf|ssb|sma|cb\s+radio|xiegu|qrp|lmr\d*)\b",
    re.IGNORECASE,
)

_NON_MEAT_PRODUCT_CONTEXT_RE = re.compile(
    r"\b(stove|weight|handle|tool|utensil|grill|press|accessor(?:y|ies)|equipment|cable|kit|bracket|holder)\b",
    re.IGNORECASE,
)

_ALCOHOL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (term, re.compile(pattern, re.IGNORECASE))
    for term, pattern in (
        ("wine", r"\bwine(?:s)?\b"),
        ("vino", r"\bvino(?:s)?\b"),
        ("beer", r"\bbeer(?:s)?\b"),
        ("cerveza", r"\bcerveza(?:s)?\b"),
        ("whisky", r"\bwhisk(?:y|ey)(?:s)?\b"),
        ("vodka", r"\bvodka(?:s)?\b"),
        ("rum", r"\brum\b"),
        ("gin", r"\bgin\b"),
        ("tequila", r"\btequila(?:s)?\b"),
        ("champagne", r"\bchampagne(?:s)?\b"),
        ("cava", r"\bcava(?:s)?\b"),
        ("liquor", r"\bliquor(?:s)?\b"),
        ("liqueur", r"\bliqueur(?:s)?\b"),
        ("alcohol", r"\balcohol(?:ic)?\b"),
        ("spirits", r"\bspirits\b"),
        ("brandy", r"\bbrandy\b"),
        ("cognac", r"\bcognac\b"),
        ("bourbon", r"\bbourbon\b"),
        ("vermouth", r"\bvermouth\b"),
        ("bebidas alcoholicas", r"\bbebidas?\s+alcoh[oó]licas?\b"),
        ("bebida alcoholica", r"\bbebida\s+alcoh[oó]lica\b"),
    )
)

_ACTUAL_ALCOHOL_CONTEXT_RE = re.compile(
    r"\b("
    r"rioja|merlot|chardonnay|cabernet|sauvignon|pinot|malbec|shiraz|tempranillo|prosecco|"
    r"drink|drinks|beverage|beverages|alcoholic\s+drink|alcoholic\s+beverage|"
    r"licor|liquor|liqueur|spirit|spirits|distilled|destilado|destilada|"
    r"red\s+wine|white\s+wine|rose\s+wine|sparkling\s+wine|vino\s+tinto|vino\s+blanco|vino\s+rosado|"
    r"bottle\s+of|case\s+of|pack\s+of|six\s+pack|"
    r"\d+(?:[\.,]\d+)?\s*(?:ml|cl|l|lt|litre|liter|litro|litros|oz)"
    r")\b",
    re.IGNORECASE,
)

_NON_DRINK_ALCOHOL_CONTEXT_RE = re.compile(
    r"\b("
    r"wine\s+red|champagne\s+(?:pink|yellow|gold|lace|satin|color|colour)|"
    r"dress|shirt|t\s*shirt|gown|nightgown|fabric|corduroy|outfit|clothing|apparel|"
    r"cabinet|rack|display\s+case|curio|shelf|shelves|furniture|bar\s+cabinet|home\s+bar|"
    r"glass|glasses|marker|markers|opener|tap\s+handle|faucet|mold|mould|ice\s+cube|"
    r"perfume|cologne|fragrance|parfum|scent|mist|"
    r"alcohol\s*free|free\s+of\s+alcohol|swab|swabs|disinfection|cleaning|cleaner|dispenser|pump|refillable|empty\s+bottle|"
    r"spirit\s+animal|print|pattern|statue|decor|decorative|accessor(?:y|ies)|holder|storage"
    r")\b",
    re.IGNORECASE,
)

# Terms that may be useful for DB pre-filtering. The final Python filter above is
# intentionally context-aware; do not delete rows by SQL LIKE alone.
ALL_RESTRICTED_TERMS: tuple[str, ...] = tuple(
    term for term, _pattern in (_STRONG_PORK_PATTERNS + _CONTEXTUAL_PORK_PATTERNS + _ALCOHOL_PATTERNS)
)


def normalize_offer_text(value: object | None) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = text.replace("/", " ").replace("_", " ").replace("-", " ")
    text = unicodedata.normalize("NFKC", text)
    # Also keep an ASCII copy so jamón / ibérico / alcohólicas are caught even
    # when a feed URL or category strips accents inconsistently.
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    combined = f"{text} {ascii_text}".lower()
    combined = re.sub(r"\s+", " ", combined)
    return combined.strip()


def _has_meat_context(text: str) -> bool:
    return _MEAT_CONTEXT_RE.search(text) is not None


def _is_non_meat_context(text: str, term: str) -> bool:
    if term == "ham" and _HAM_RADIO_CONTEXT_RE.search(text):
        return True
    if _NON_MEAT_PRODUCT_CONTEXT_RE.search(text) and not _has_meat_context(text):
        return True
    return False


def _has_actual_alcohol_context(text: str, term: str) -> bool:
    # Explicit drink/category/volume context is required to avoid blocking colors,
    # furniture, empty bottles, perfume, swabs, and accessories.
    if re.search(r"\bbebidas?\s+alcoh[oó]licas?\b", text, re.IGNORECASE):
        return True
    if _ACTUAL_ALCOHOL_CONTEXT_RE.search(text):
        return True
    if term in {"vodka", "tequila", "rum", "gin", "brandy", "cognac", "bourbon", "vermouth"}:
        # Distilled drink names are strong, but still require bottle/volume/drink context.
        return re.search(r"\b(bottle|drink|beverage|\d+(?:[\.,]\d+)?\s*(?:ml|cl|l|lt|litre|liter|litro|litros|oz))\b", text, re.IGNORECASE) is not None
    return False


def _is_non_drink_context(text: str) -> bool:
    return _NON_DRINK_ALCOHOL_CONTEXT_RE.search(text) is not None


def restricted_offer_match(values: Iterable[object | None]) -> RestrictedOfferMatch | None:
    text = normalize_offer_text(" ".join(str(value or "") for value in values))
    if not text:
        return None

    for term, pattern in _STRONG_PORK_PATTERNS:
        if pattern.search(text):
            return RestrictedOfferMatch(category="pork_or_ham", term=term)

    for term, pattern in _CONTEXTUAL_PORK_PATTERNS:
        if not pattern.search(text):
            continue
        if _is_non_meat_context(text, term):
            continue
        if term == "iberico" and not _has_meat_context(text):
            continue
        if term in {"ham", "pork", "bacon", "gammon"} and not _has_meat_context(text):
            continue
        return RestrictedOfferMatch(category="pork_or_ham", term=term)

    for term, pattern in _ALCOHOL_PATTERNS:
        if not pattern.search(text):
            continue
        if _is_non_drink_context(text):
            continue
        if not _has_actual_alcohol_context(text, term):
            continue
        return RestrictedOfferMatch(category="alcohol", term=term)

    return None


def is_restricted_offer(values: Iterable[object | None]) -> bool:
    return restricted_offer_match(values) is not None


def restricted_offer_match_for_mapping(
    item: Mapping[str, Any],
    *,
    keys: Iterable[str],
) -> RestrictedOfferMatch | None:
    return restricted_offer_match(item.get(key) for key in keys)
