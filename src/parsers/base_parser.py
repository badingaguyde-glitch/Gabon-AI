"""Base class and common utilities for all format parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from src.models import InternalDocument, DocumentSection, TableData
from src.format_detector import compute_file_sha256, detect_file_encoding

# Simple language detection heuristic (FR vs EN vs other) if langdetect is not installed
FRENCH_WORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "dans", "en", "au", "aux",
    "est", "sont", "avec", "pour", "par", "sur", "cette", "ces", "ce", "espece",
    "especes", "foret", "forets", "gabon", "national", "parc", "faune", "flore",
    "population", "habitat", "regime", "alimentaire", "menaces", "conservation"
}

ENGLISH_WORDS = {
    "the", "a", "an", "in", "on", "at", "by", "for", "with", "from", "of", "to",
    "is", "are", "was", "were", "and", "this", "these", "that", "species", "forest",
    "forests", "gabon", "national", "park", "wildlife", "population", "habitat",
    "diet", "threats", "conservation", "study", "results", "methods", "observations"
}


def detect_text_language(text: str) -> tuple[str, float]:
    """Detects text language (primarily French vs English) with confidence score."""
    if not text or len(text.strip()) < 10:
        return "en", 0.5

    # Check for langdetect
    try:
        from langdetect import detect_langs
        langs = detect_langs(text[:5000])
        if langs:
            top = langs[0]
            return top.lang, float(top.prob)
    except Exception:
        pass

    # Heuristic word match
    words = re.findall(r"\b[a-zA-ZàâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ]{2,}\b", text.lower()[:10000])
    if not words:
        return "en", 0.5

    fr_hits = sum(1 for w in words if w in FRENCH_WORDS)
    en_hits = sum(1 for w in words if w in ENGLISH_WORDS)
    total_hits = fr_hits + en_hits

    if total_hits == 0:
        return "en", 0.6

    if fr_hits > en_hits:
        conf = fr_hits / total_hits
        return "fr", min(0.99, max(0.6, conf))
    else:
        conf = en_hits / total_hits
        return "en", min(0.99, max(0.6, conf))


class BaseParser(ABC):
    """Abstract base class for all content parsers."""

    name: str = "base_parser"
    supported_formats: List[str] = []

    def can_parse(self, file_path: str | Path, detected_format: str) -> bool:
        """Determines if this parser can handle the given file."""
        return detected_format in self.supported_formats

    @abstractmethod
    def parse(
        self,
        file_path: str | Path,
        source_id: str,
        detected_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> InternalDocument:
        """Parses the file into a standardized InternalDocument."""
        pass

    def extract_metadata(self, file_path: str | Path) -> Dict[str, Any]:
        """Extracts low-level file metadata."""
        p = Path(file_path)
        stat = p.stat()
        return {
            "file_size_bytes": stat.st_size,
            "filename": p.name,
            "suffix": p.suffix,
        }

    def create_empty_doc(
        self,
        file_path: str | Path,
        source_id: str,
        format_name: str,
        encoding: str = "utf-8",
    ) -> InternalDocument:
        p = Path(file_path)
        sha = compute_file_sha256(p)
        return InternalDocument(
            source_id=source_id,
            filename=p.name,
            file_path=str(p.resolve()),
            sha256=sha,
            format=format_name,
            encoding=encoding,
            document_metadata=self.extract_metadata(p),
        )
