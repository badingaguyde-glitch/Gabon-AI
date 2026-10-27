"""Scientific data normalizer for units, taxonomy, Gabon localities, and multilingual concepts."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple, Union

GABON_PARKS = {
    "lopé": "Lopé National Park",
    "lope": "Lopé National Park",
    "ivindo": "Ivindo National Park",
    "loango": "Loango National Park",
    "minkébé": "Minkébé National Park",
    "minkebe": "Minkébé National Park",
    "pongara": "Pongara National Park",
    "moukalaba": "Moukalaba-Doudou National Park",
    "moukalaba-doudou": "Moukalaba-Doudou National Park",
    "plateaux batéké": "Plateaux Batéké National Park",
    "plateaux bateke": "Plateaux Batéké National Park",
    "bateke": "Plateaux Batéké National Park",
    "mayumba": "Mayumba National Park",
    "monts de cristal": "Monts de Cristal National Park",
    "cristal mountains": "Monts de Cristal National Park",
    "waka": "Waka National Park",
    "birougou": "Birougou National Park",
    "mwagna": "Mwagna National Park",
}

GABON_PROVINCES = [
    "Estuaire", "Haut-Ogooué", "Moyen-Ogooué", "Ngounié",
    "Nyanga", "Ogooué-Ivindo", "Ogooué-Lolo", "Ogooué-Maritime", "Woleu-Ntem"
]

IUCN_STATUS_MAP = {
    "critically endangered": "CR",
    "en danger critique": "CR",
    "cr": "CR",
    "endangered": "EN",
    "en danger": "EN",
    "en": "EN",
    "vulnerable": "VU",
    "vulnérable": "VU",
    "vu": "VU",
    "near threatened": "NT",
    "quasi menacé": "NT",
    "nt": "NT",
    "least concern": "LC",
    "préoccupation mineure": "LC",
    "lc": "LC",
    "data deficient": "DD",
    "données insuffisantes": "DD",
    "dd": "DD",
}

DIET_TYPES_MAP = {
    "herbivore": "herbivore",
    "herbivorous": "herbivore",
    "frugivore": "frugivore",
    "frugivorous": "frugivore",
    "folivore": "folivore",
    "folivorous": "folivore",
    "carnivore": "carnivore",
    "carnivorous": "carnivore",
    "insectivore": "insectivore",
    "insectivorous": "insectivore",
    "omnivore": "omnivore",
    "omnivorous": "omnivore",
    "piscivore": "piscivore",
    "piscivorous": "piscivore",
    "granivore": "granivore",
    "granivorous": "granivore",
}


def normalize_park_name(raw_name: str) -> Optional[str]:
    """Matches a mention to one of Gabon's 13 National Parks."""
    if not raw_name:
        return None
    raw_lower = raw_name.lower().strip()
    for key, canonical in GABON_PARKS.items():
        if key in raw_lower:
            return canonical
    return raw_name.title()


def normalize_iucn_status(raw_status: str) -> Optional[str]:
    if not raw_status:
        return None
    cleaned = raw_status.strip().lower()
    return IUCN_STATUS_MAP.get(cleaned, raw_status.upper() if len(raw_status) <= 2 else None)


def normalize_diet_type(raw_type: str) -> str:
    cleaned = raw_type.strip().lower()
    return DIET_TYPES_MAP.get(cleaned, cleaned)


def normalize_measurement_unit(value_str: str) -> Dict[str, Any]:
    """Parses measurements like '120 kg', '45 - 60 cm', '2.5 m' into normalized numeric structures."""
    val_clean = value_str.strip().lower()

    # Match range or single number + unit
    m = re.search(r"(\d+(?:[.,]\d+)?)(?:\s*(?:-|to|à)\s*(\d+(?:[.,]\d+)?))?\s*([a-zA-Z%²³]+)?", val_clean)
    if not m:
        return {"raw": value_str}

    min_v = float(m.group(1).replace(",", "."))
    max_v = float(m.group(2).replace(",", ".")) if m.group(2) else min_v
    unit = m.group(3) or ""

    # Normalize weights to kg
    if unit in ("g", "grams", "grammes"):
        return {"min": min_v / 1000.0, "max": max_v / 1000.0, "unit": "kg", "original": value_str}
    if unit in ("kg", "kgs", "kilograms", "kilogrammes"):
        return {"min": min_v, "max": max_v, "unit": "kg", "original": value_str}
    if unit in ("lbs", "lb", "pounds"):
        return {"min": round(min_v * 0.453592, 2), "max": round(max_v * 0.453592, 2), "unit": "kg", "original": value_str}

    # Normalize lengths to cm / m
    if unit in ("mm", "millimeters", "millimètres"):
        return {"min": min_v / 10.0, "max": max_v / 10.0, "unit": "cm", "original": value_str}
    if unit in ("cm", "cms", "centimeters", "centimètres"):
        return {"min": min_v, "max": max_v, "unit": "cm", "original": value_str}
    if unit in ("m", "meters", "mètres"):
        return {"min": min_v, "max": max_v, "unit": "m", "original": value_str}

    return {"min": min_v, "max": max_v, "unit": unit, "original": value_str}
