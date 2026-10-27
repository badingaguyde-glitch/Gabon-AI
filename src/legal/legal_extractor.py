"""Legal and environmental regulatory text parser and extractor for Gabon laws, decrees, and codes."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from src.models import InternalDocument, SourceProvenance


@dataclass
class LegalArticle:
    article_number: str
    title: Optional[str] = None
    content: str = ""
    topic: Optional[str] = None  # 'wildlife_protection', 'hunting_regulation', 'penalties_sanctions', 'park_governance', 'forestry'
    mentioned_species: List[str] = field(default_factory=list)
    mentioned_parks: List[str] = field(default_factory=list)
    penalties: List[Dict[str, Any]] = field(default_factory=list)  # [{'fine_min': ..., 'fine_max': ..., 'prison_min': ..., 'prison_max': ...}]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LegalDocumentRecord:
    doc_id: str
    law_number: Optional[str] = None  # e.g., 'Loi n° 016/2001', 'Loi n° 003/2007'
    title: str = ""
    doc_type: str = "loi"  # 'loi', 'decret', 'arrete', 'convention', 'code', 'reglement'
    date_enacted: Optional[str] = None
    ministry_or_authority: Optional[str] = None
    summary: str = ""
    articles: List[LegalArticle] = field(default_factory=list)
    protected_species_lists: Dict[str, List[str]] = field(default_factory=lambda: {"integral": [], "partial": []})
    general_sanctions: List[str] = field(default_factory=list)
    source_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "law_number": self.law_number,
            "title": self.title,
            "doc_type": self.doc_type,
            "date_enacted": self.date_enacted,
            "ministry_or_authority": self.ministry_or_authority,
            "summary": self.summary,
            "total_articles": len(self.articles),
            "articles": [a.to_dict() if hasattr(a, "to_dict") else a for a in self.articles],
            "protected_species_lists": self.protected_species_lists,
            "general_sanctions": self.general_sanctions,
            "source_id": self.source_id,
            "created_at": self.created_at,
        }


class LegalExtractor:
    """Detects, segments, and structures legal texts, forestry codes, and park regulations in Gabon."""

    LAW_PATTERNS = [
        r"\b(Loi\s+n[°o]?\s*[\d\w\/\-]+(?:\s+du\s+[\d\w\s]+)?)\b",
        r"\b(Décret\s+n[°o]?\s*[\d\w\/\-]+(?:\s+du\s+[\d\w\s]+)?)\b",
        r"\b(Arrêté\s+n[°o]?\s*[\d\w\/\-]+(?:\s+du\s+[\d\w\s]+)?)\b",
        r"\b(Code\s+Forestier|Code\s+de\s+l'Environnement|Code\s+Pénal)\b",
    ]

    SANCTION_REGEX = re.compile(
        r"(?:amende|emprisonnement|peine|punie?|passible|confiscation|prison)\s+(?:de\s+)?([^.;\n]+(?:francs?|FCFA|mois|ans?|années?))",
        re.IGNORECASE
    )

    ARTICLE_SPLIT_REGEX = re.compile(
        r"(?:^|\n)\s*(Article\s+(?:unique|\d+(?:[a-zA-Z\-]|\s*er)?))\s*[:.\-]?\s*(.*?)(?=\n\s*Article|\Z)",
        re.DOTALL | re.IGNORECASE
    )

    def is_legal_document(self, doc: InternalDocument) -> bool:
        """Determines if the document contains legal/regulatory provisions (Loi, Décret, Code, Articles)."""
        text = doc.raw_text[:10000].lower()
        legal_indicators = [
            "code forestier", "parcs nationaux", "loi n°", "loi no", "décret n°", "décret no",
            "arrêté n°", "république gabonaise", "l'assemblée nationale", "le président de la république",
            "promulgue la loi", "sanctions pénales", "infractions", "espèces intégralement protégées",
            "espèces partiellement protégées", "permis de chasse", "eaux et forêts", "anpn", "ministère"
        ]
        score = sum(1 for ind in legal_indicators if ind in text)
        has_articles = len(self.ARTICLE_SPLIT_REGEX.findall(doc.raw_text)) >= 2
        return score >= 2 or has_articles

    def extract_legal_document(self, doc: InternalDocument, doc_counter: int = 1) -> LegalDocumentRecord:
        text = doc.raw_text
        doc_id = f"LAW-{doc_counter:04d}"

        # 1. Detect law number and type
        law_num = None
        for pat in self.LAW_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                law_num = m.group(1).strip()
                break

        doc_type = "loi"
        if law_num:
            lower = law_num.lower()
            if "décret" in lower:
                doc_type = "decret"
            elif "arrêté" in lower:
                doc_type = "arrete"
            elif "code" in lower:
                doc_type = "code"

        # 2. Extract title / header
        first_lines = [l.strip() for l in text.splitlines() if l.strip()][:10]
        title = first_lines[0] if first_lines else "Texte Juridique / Réglementaire"
        for line in first_lines:
            if any(k in line.lower() for k in ["portant", "relative à", "relatif à", "code", "protection"]):
                title = line
                break

        # 3. Extract articles
        articles: List[LegalArticle] = []
        raw_articles = self.ARTICLE_SPLIT_REGEX.findall(text)

        protected_species_integral = []
        protected_species_partial = []
        general_sanctions = []

        for art_num_raw, art_content in raw_articles:
            art_content_clean = art_content.strip()

            # Classify article topic
            content_lower = art_content_clean.lower()
            topic = "general"
            if any(k in content_lower for k in ["faune", "espèce", "animal", "chasse", "braconnage"]):
                topic = "wildlife_protection"
            elif any(k in content_lower for k in ["parc", "réserve", "aire protégée", "anpn"]):
                topic = "park_governance"
            elif any(k in content_lower for k in ["peine", "amende", "emprisonnement", "sanction", "puni"]):
                topic = "penalties_sanctions"
            elif any(k in content_lower for k in ["forêt", "bois", "concession", "abattage", "permis"]):
                topic = "forestry"

            # Check sanctions
            sanctions_found = []
            for s_match in self.SANCTION_REGEX.finditer(art_content_clean):
                sanct_text = s_match.group(0).strip()
                sanctions_found.append({"raw": sanct_text})
                general_sanctions.append(f"{art_num_raw}: {sanct_text}")

            # Check integral vs partial protection mentions
            if "intégralement protég" in content_lower or "classe a" in content_lower:
                topic = "wildlife_protection"
            if "partiellement protég" in content_lower or "classe b" in content_lower:
                topic = "wildlife_protection"

            art = LegalArticle(
                article_number=art_num_raw.strip(),
                content=art_content_clean,
                topic=topic,
                penalties=sanctions_found,
            )
            articles.append(art)

        record = LegalDocumentRecord(
            doc_id=doc_id,
            law_number=law_num,
            title=title,
            doc_type=doc_type,
            summary=f"Document juridique comportant {len(articles)} articles identifiés.",
            articles=articles,
            protected_species_lists={
                "integral": protected_species_integral,
                "partial": protected_species_partial,
            },
            general_sanctions=general_sanctions[:50],
            source_id=doc.source_id,
        )

        return record
