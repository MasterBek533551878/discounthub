from __future__ import annotations

import re
import urllib.parse
from collections.abc import Iterable
from typing import Any


COUNTRY_NAMES: dict[str, str] = {
    "AD": "Andorra",
    "AE": "United Arab Emirates",
    "AL": "Albania",
    "AM": "Armenia",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "AZ": "Azerbaijan",
    "BA": "Bosnia and Herzegovina",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BO": "Bolivia",
    "BR": "Brazil",
    "BY": "Belarus",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "CR": "Costa Rica",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DK": "Denmark",
    "DO": "Dominican Republic",
    "EC": "Ecuador",
    "EE": "Estonia",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GB": "United Kingdom",
    "GE": "Georgia",
    "GR": "Greece",
    "GT": "Guatemala",
    "HN": "Honduras",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IN": "India",
    "IS": "Iceland",
    "IT": "Italy",
    "JP": "Japan",
    "KG": "Kyrgyzstan",
    "KZ": "Kazakhstan",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MC": "Monaco",
    "MD": "Moldova",
    "ME": "Montenegro",
    "MK": "North Macedonia",
    "MT": "Malta",
    "MX": "Mexico",
    "NI": "Nicaragua",
    "NL": "Netherlands",
    "NO": "Norway",
    "NZ": "New Zealand",
    "PA": "Panama",
    "PE": "Peru",
    "PL": "Poland",
    "PT": "Portugal",
    "PY": "Paraguay",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "SE": "Sweden",
    "SG": "Singapore",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "SV": "El Salvador",
    "TJ": "Tajikistan",
    "TM": "Turkmenistan",
    "TR": "Turkey",
    "UA": "Ukraine",
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VE": "Venezuela",
    "XK": "Kosovo",
    "ZA": "South Africa",
}

EUROPE_COUNTRIES: tuple[str, ...] = (
    "AL", "AD", "AM", "AT", "AZ", "BY", "BE", "BA", "BG", "HR", "CY",
    "CZ", "DK", "EE", "FI", "FR", "GE", "DE", "GR", "HU", "IS", "IE",
    "IT", "XK", "LV", "LI", "LT", "LU", "MT", "MD", "MC", "ME", "NL",
    "MK", "NO", "PL", "PT", "RO", "RS", "SK", "SI", "ES", "SE", "CH",
    "TR", "UA", "GB",
)

LATAM_COUNTRIES: tuple[str, ...] = (
    "AR", "BO", "BR", "CL", "CO", "CR", "DO", "EC", "SV", "GT", "HN",
    "MX", "NI", "PA", "PY", "PE", "UY", "VE",
)

CIS_COUNTRIES: tuple[str, ...] = (
    "AM", "AZ", "BY", "GE", "KZ", "KG", "MD", "RU", "TJ", "TM", "UA", "UZ",
)

SUPPORTED_FILTER_COUNTRIES: tuple[str, ...] = (
    "US", "GB", "DE", "FR", "ES", "IT", "PL", "NL", "BE", "AT", "IE",
    "PT", "CZ", "RO", "SE", "DK", "FI", "NO", "CH", "AU", "CA", "NZ",
    "BR", "MX", "AR", "CL", "CO", "PE", "IN", "JP", "SG", "AE", "TR",
    "UA", "KZ", "UZ",
)

REGION_ALIASES: dict[str, tuple[str, ...] | None] = {
    "global": None,
    "worldwide": None,
    "world wide": None,
    "international": None,
    "all countries": None,
    "all regions": None,
    "europe": EUROPE_COUNTRIES,
    "european union": EUROPE_COUNTRIES,
    "eu": EUROPE_COUNTRIES,
    "eea": EUROPE_COUNTRIES,
    "latam": LATAM_COUNTRIES,
    "latin america": LATAM_COUNTRIES,
    "south america": LATAM_COUNTRIES,
    "cis": CIS_COUNTRIES,
    "sng": CIS_COUNTRIES,
    "снг": CIS_COUNTRIES,
    "usa": ("US",),
    "united states": ("US",),
    "united states of america": ("US",),
    "america": ("US",),
    "uk": ("GB",),
    "great britain": ("GB",),
    "united kingdom": ("GB",),
}

COUNTRY_ALIASES: dict[str, str] = {
    **{name.lower(): code for code, name in COUNTRY_NAMES.items()},
    "u.s.": "US",
    "u.s.a.": "US",
    "us": "US",
    "usa": "US",
    "united states of america": "US",
    "uk": "GB",
    "u.k.": "GB",
    "great britain": "GB",
    "england": "GB",
    "uae": "AE",
    "czechia": "CZ",
    "republic of ireland": "IE",
    "south korea": "KR",
    "korea": "KR",
    "turkiye": "TR",
    "moldova, republic of": "MD",
    "russian federation": "RU",
}

TLD_TO_COUNTRY: dict[str, str] = {
    "co.uk": "GB",
    "uk": "GB",
    "us": "US",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "it": "IT",
    "pl": "PL",
    "nl": "NL",
    "be": "BE",
    "at": "AT",
    "ie": "IE",
    "pt": "PT",
    "cz": "CZ",
    "sk": "SK",
    "hu": "HU",
    "ro": "RO",
    "bg": "BG",
    "gr": "GR",
    "se": "SE",
    "dk": "DK",
    "fi": "FI",
    "no": "NO",
    "ch": "CH",
    "com.au": "AU",
    "au": "AU",
    "ca": "CA",
    "co.nz": "NZ",
    "nz": "NZ",
    "com.br": "BR",
    "br": "BR",
    "com.mx": "MX",
    "mx": "MX",
    "com.ar": "AR",
    "cl": "CL",
    "com.co": "CO",
    "co": "CO",
    "com.pe": "PE",
    "pe": "PE",
    "co.in": "IN",
    "in": "IN",
    "co.jp": "JP",
    "jp": "JP",
    "com.sg": "SG",
    "sg": "SG",
    "ae": "AE",
    "com.tr": "TR",
    "tr": "TR",
    "ua": "UA",
    "kz": "KZ",
    "uz": "UZ",
}


def country_name(code: str) -> str:
    normalized = str(code or "").strip().upper()
    return COUNTRY_NAMES.get(normalized, normalized)


def normalize_country_code(value: object) -> str | None:
    token = _clean_token(value)
    if not token:
        return None

    if token.upper() in COUNTRY_NAMES:
        return token.upper()

    mapped = COUNTRY_ALIASES.get(token)
    if mapped:
        return mapped

    # Awin sometimes appends a settlement currency, e.g. "Brazil USD" or
    # "Mexico pesos". Prefer a leading country name when present.
    for alias, code in sorted(COUNTRY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if token.startswith(alias + " ") or token.endswith(" " + alias):
            return code

    return None


def normalize_availability(values: Any) -> tuple[list[str], bool]:
    countries: list[str] = []
    is_global = False

    for raw_value in _flatten_values(values):
        for token in _split_tokens(raw_value):
            cleaned = _clean_token(token)
            if not cleaned:
                continue

            if cleaned in REGION_ALIASES:
                region_countries = REGION_ALIASES[cleaned]
                if region_countries is None:
                    is_global = True
                else:
                    for code in region_countries:
                        if code not in countries:
                            countries.append(code)
                continue

            code = normalize_country_code(cleaned)
            if code and code not in countries:
                countries.append(code)

    return sorted(countries), is_global


def infer_availability(*values: Any) -> tuple[list[str], bool]:
    countries, is_global = normalize_availability(values)
    if countries or is_global:
        return countries, is_global

    joined = " ".join(str(value or "") for value in values).strip()
    if not joined:
        return [], False

    lowered = _clean_token(joined)
    if re.search(r"\b(global|worldwide|international)\b", lowered):
        return [], True
    if "aliexpress" in lowered:
        return [], True
    if "mercado libre" in lowered or "mercadolibre" in lowered:
        return list(LATAM_COUNTRIES), False

    inferred: list[str] = []
    token_patterns = {
        "US": r"(?:^|[^a-z0-9])(us|usa|united states)(?:$|[^a-z0-9])",
        "GB": r"(?:^|[^a-z0-9])(uk|gb|united kingdom|great britain)(?:$|[^a-z0-9])",
        "AU": r"(?:^|[^a-z0-9])(au|australia)(?:$|[^a-z0-9])",
        "CA": r"(?:^|[^a-z0-9])(ca|canada)(?:$|[^a-z0-9])",
        "FR": r"(?:^|[^a-z0-9])(fr|france)(?:$|[^a-z0-9])",
        "DE": r"(?:^|[^a-z0-9])(de|germany)(?:$|[^a-z0-9])",
        "PL": r"(?:^|[^a-z0-9])(pl|poland)(?:$|[^a-z0-9])",
    }
    for code, pattern in token_patterns.items():
        if re.search(pattern, lowered):
            inferred.append(code)

    if re.search(r"(?:^|[^a-z0-9])(eu|europe)(?:$|[^a-z0-9])", lowered):
        inferred.extend(EUROPE_COUNTRIES)

    for value in values:
        text = str(value or "").strip()
        if not text.startswith(("http://", "https://")):
            continue
        host = urllib.parse.urlparse(text).netloc.lower().split(":", 1)[0]
        host = host.removeprefix("www.")
        for suffix, code in sorted(TLD_TO_COUNTRY.items(), key=lambda item: len(item[0]), reverse=True):
            if host == suffix or host.endswith("." + suffix):
                inferred.append(code)
                break

    return sorted(set(inferred)), False


def _flatten_values(value: Any) -> Iterable[Any]:
    if value is None:
        return []
    if isinstance(value, dict):
        flattened: list[Any] = []
        preferred_keys = (
            "code", "id", "name", "country", "countryCode", "country_code",
            "region", "regionCode", "region_code", "countries", "countryCodes",
            "country_codes", "regions", "regionCodes", "region_codes",
        )
        for key in preferred_keys:
            if key in value:
                flattened.extend(_flatten_values(value[key]))
        if flattened:
            return flattened
        for nested in value.values():
            flattened.extend(_flatten_values(nested))
        return flattened
    if isinstance(value, (list, tuple, set, frozenset)):
        flattened = []
        for nested in value:
            flattened.extend(_flatten_values(nested))
        return flattened
    return [value]


def _split_tokens(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part for part in re.split(r"[,;|/\n]+", text) if part.strip()]


def _clean_token(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\U0001F1E6-\U0001F1FF]", "", text)
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-zа-яё0-9. ]+", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()
