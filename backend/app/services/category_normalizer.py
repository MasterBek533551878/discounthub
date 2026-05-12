from __future__ import annotations


CATEGORY_ELECTRONICS = "Electronics"
CATEGORY_COMPUTERS = "Computers"
CATEGORY_FASHION = "Fashion"
CATEGORY_GAMING = "Gaming"
CATEGORY_HOME = "Home"
CATEGORY_AUTO = "Auto"
CATEGORY_BEAUTY = "Beauty"
CATEGORY_TOYS = "Toys"
CATEGORY_SPORTS = "Sports"
CATEGORY_OTHER = "Other"


_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        CATEGORY_COMPUTERS,
        (
            "laptop",
            "notebook",
            "netbook",
            "portatili",
            "pc ",
            "macbook",
            "computadora",
            "computador",
            "portatil",
            "portátil",
            "monitor",
            "monitors",
            "display",
            "graphics card",
            "gpu",
            "motherboard",
            "processor",
            "cpu",
            "ssd",
            "hard drive",
            "pc component",
            "computer component",
            "componentes",
            "ordinateur",
            "computer",
        ),
    ),
    (
        CATEGORY_GAMING,
        (
            "gaming",
            "video game",
            "controller",
            "keyboard & mouse",
            "keyboards & keypads",
            "gamepad",
            "gamer",
            "juego",
            "controle",
            "teclado",
            "playstation",
            "xbox",
            "nintendo",
            "console",
            "consoles",
        ),
    ),
    (
        CATEGORY_ELECTRONICS,
        (
            "headphone",
            "headphones",
            "headset",
            "earbud",
            "earbuds",
            "écouteurs",
            "ecouteurs",
            "kopfhörer",
            "smart watch",
            "smartwatch",
            "smartwatches",
            "montres connectées",
            "relojes inteligentes",
            "gps, montres running",
            "audifono",
            "audífono",
            "auricular",
            "auriculares",
            "fone",
            "fones",
            "reloj inteligente",
            "cell phone",
            "cell phones",
            "smartphone",
            "smartphones",
            "mobile phone",
            "iphone",
            "android phone",
            "tablet",
            "tablets",
            "ipad",
            "e-reader",
            "camera",
            "cameras",
            "digital camera",
            "mirrorless",
            "dslr",
            "lens",
            "lenses",
            "smart speakers",
            "home speakers",
            "cables & adapters",
        ),
    ),
    (
        CATEGORY_FASHION,
        (
            "sneaker",
            "sneakers",
            "athletic shoes",
            "trainers",
            "baskets",
            "scarpe",
            "schuhe",
            "sandalen",
            "casual shoes",
            "socken",
            "shoes",
            "tenis",
            "tênis",
            "zapatilla",
            "zapatillas",
            "calzado",
            "sapato",
            "handbag",
            "handbags",
            "bag",
            "bags",
            "backpack",
            "wallet",
            "purse",
            "watch",
            "watches",
            "wristwatches",
            "clothing",
            "apparel",
            "fashion",
        ),
    ),
    (
        CATEGORY_HOME,
        (
            "smart home",
            "door locks",
            "air fresheners",
            "home gadgets",
            "home electronics",
            "home appliance",
            "home appliances",
            "appliance",
            "appliances",
            "vacuum",
            "cleaner",
            "kitchen",
            "casa",
            "hogar",
            "cocina",
        ),
    ),
    (
        CATEGORY_BEAUTY,
        (
            "beauty",
            "health & beauty",
            "skincare",
            "skin care",
            "makeup",
            "cosmetic",
            "cosmetics",
            "perfume",
            "fragrance",
            "hair care",
            "personal care",
        ),
    ),
    (
        CATEGORY_TOYS,
        (
            "toy",
            "toys",
            "lego",
            "action figure",
            "doll",
            "board game",
            "puzzle",
            "collectible",
        ),
    ),
    (
        CATEGORY_AUTO,
        (
            "auto",
            "automotive",
            "car ",
            "cars",
            "vehicle",
            "motor",
            "car accessory",
            "car accessories",
            "auto part",
            "auto parts",
            "vehicle parts",
        ),
    ),
    (
        CATEGORY_SPORTS,
        (
            "sport",
            "sports",
            "fitness",
            "gym",
            "exercise",
            "yoga",
            "running",
            "outdoor",
            "cycling",
            "workout",
        ),
    ),
)


_CANONICAL_CATEGORIES = {
    CATEGORY_ELECTRONICS.lower(): CATEGORY_ELECTRONICS,
    CATEGORY_COMPUTERS.lower(): CATEGORY_COMPUTERS,
    CATEGORY_FASHION.lower(): CATEGORY_FASHION,
    CATEGORY_GAMING.lower(): CATEGORY_GAMING,
    CATEGORY_HOME.lower(): CATEGORY_HOME,
    CATEGORY_AUTO.lower(): CATEGORY_AUTO,
    CATEGORY_BEAUTY.lower(): CATEGORY_BEAUTY,
    CATEGORY_TOYS.lower(): CATEGORY_TOYS,
    CATEGORY_SPORTS.lower(): CATEGORY_SPORTS,
    CATEGORY_OTHER.lower(): CATEGORY_OTHER,
}


def normalize_category(category: str | None) -> str:
    """Map marketplace-specific category names into stable app categories."""
    raw = (category or "").strip()
    if not raw:
        return CATEGORY_OTHER

    canonical = _CANONICAL_CATEGORIES.get(raw.lower())
    if canonical:
        return canonical

    haystack = f" {raw.lower()} "
    for normalized, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return normalized

    return CATEGORY_OTHER
