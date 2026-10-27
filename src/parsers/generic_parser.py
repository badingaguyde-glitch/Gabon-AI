"""Generic fallback parser attempting text decode with multiple encodings or binary analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.models import InternalDocument, DocumentSection
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding


class GenericParser(BaseParser):
    name = "generic_parser"
    supported_formats = ["unknown_text", "unknown_binary", "generic", "dat", "raw", "data", "export", "result"]

    def can_parse(self, file_path: str | Path, detected_format: str) -> bool:
        return True  # Fallback for anything

    def parse(
        self,
        file_path: str | Path,
        source_id: str,
        detected_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> InternalDocument:
        p = Path(file_path)
        with open(p, "rb") as f:
            raw_bytes = f.read()

        enc = encoding or detect_file_encoding(raw_bytes)
        try:
            content = raw_bytes.decode(enc)
        except Exception:
            content = raw_bytes.decode("latin-1", errors="replace")
            enc = "latin-1"

        doc = self.create_empty_doc(p, source_id, detected_format or "generic_text", encoding=enc)
        doc.raw_text = content
        doc.paragraphs = [line.strip() for line in content.splitlines() if line.strip()]
        doc.sections = [DocumentSection(title="Generic Document Content", level=1, content=content)]

        lang, conf = detect_text_language(content)
        doc.language = lang
        doc.language_confidence = conf

        return doc
