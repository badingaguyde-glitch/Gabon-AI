"""Document domain classifier: detects COUNTRY (primary axis) and CATEGORY / SUBCATEGORY."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unicodedata
from typing import Dict, List, Optional

from src.models import InternalDocument
from src.general_knowledge.taxonomy import CATEGORIES, PATH_HINTS, LEGAL_SUBCATEGORY_HINTS

# Countries that may appear in the corpus. Extend freely: the system is country-agnostic.
COUNTRY_ALIASES: Dict[str, List[str]] = {
    "Gabon": ["gabon", "gabonaise", "gabonais", "république gabonaise", "republique gabonaise", "gab"],
    "Cameroun": ["cameroun", "cameroon", "camerounaise"],
    "Congo": ["république du congo", "congo-brazzaville", "republic of congo"],
    "Guinée équatoriale": ["guinée équatoriale", "equatorial guinea"],
    "France": ["république française", "france"],
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


@dataclass
class Classification:
    country: str
    category: str
    subcategory: Optional[str] = None
    confidence: float = 0.5
    scores: Dict[str, float] = field(default_factory=dict)
    secondary_categories: List[str] = field(default_factory=list)


class DomainClassifier:
    """Score-based multi-signal classifier (filename > folder path > content)."""

    def __init__(self, default_country: str = "Gabon"):
        self.default_country = default_country

    def detect_country(self, doc: InternalDocument, rel_path: str = "") -> str:
        text = (rel_path + " " + doc.filename + " " + doc.raw_text[:50000]).lower()
        best, best_score = self.default_country, 0
        for country, aliases in COUNTRY_ALIASES.items():
            score = 0
            for a in aliases:
                if len(a) <= 3:
                    score += len(re.findall(rf"\b{re.escape(a)}\b", text))
                else:
                    score += text.count(a) * 2
            if score > best_score:
                best, best_score = country, score
        return best

    def classify(self, doc: InternalDocument, rel_path: str = "") -> Classification:
        filename = doc.filename.lower()
        folder = str(Path(rel_path).parent).lower() if rel_path else ""
        text = (doc.document_metadata.get("title") or "") + "\n" + doc.raw_text[:60000]
        text_l = text.lower()

        scores: Dict[str, float] = {c: 0.0 for c in CATEGORIES}

        # 1. Path hints: filename weighs more than folder
        for hint, cat in PATH_HINTS:
            if hint in filename or strip_accents(hint) in strip_accents(filename):
                scores[cat] = scores.get(cat, 0) + 12
            if folder and (hint in folder or strip_accents(hint) in strip_accents(folder)):
                scores[cat] = scores.get(cat, 0) + 5

        # 2. Content keywords (log-damped counts)
        for cat, meta in CATEGORIES.items():
            for kw in meta["keywords"]:
                n = text_l.count(kw)
                if n:
                    scores[cat] += min(4.0, 1.0 + n ** 0.5)

        # 3. Legal structure boost (many "Article N")
        n_articles = len(re.findall(r"\n\s*article\s+\d+", text_l))
        if n_articles >= 5:
            scores["droit"] += min(15.0, n_articles / 4)

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_cat, top_score = ranked[0]
        if top_score <= 0:
            top_cat = "general"
        total = sum(v for v in scores.values() if v > 0) or 1.0
        confidence = round(min(0.99, top_score / total + 0.2), 3) if top_score > 0 else 0.3

        secondary = [c for c, s in ranked[1:4] if s >= max(3.0, top_score * 0.25)]

        subcategory = None
        if top_cat == "droit" or n_articles >= 5:
            probe = (filename + " " + text_l[:3000])
            for hint, sub in LEGAL_SUBCATEGORY_HINTS:
                if hint in probe:
                    subcategory = sub
                    break

        return Classification(
            country=self.detect_country(doc, rel_path),
            category=top_cat,
            subcategory=subcategory,
            confidence=confidence,
            scores={k: round(v, 2) for k, v in ranked if v > 0},
            secondary_categories=secondary,
        )
