"""JSON Lines / NDJSON streaming data parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models import InternalDocument, DocumentSection
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding


class JsonlParser(BaseParser):
    name = "jsonl_parser"
    supported_formats = ["jsonl", "ndjson"]

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
            content_str = raw_bytes.decode(enc)
        except Exception:
            content_str = raw_bytes.decode("latin-1", errors="replace")
            enc = "latin-1"

        doc = self.create_empty_doc(p, source_id, "jsonl", encoding=enc)
        records: List[Dict[str, Any]] = []
        text_lines: List[str] = []

        for line_num, line in enumerate(content_str.splitlines(), start=1):
            line_s = line.strip()
            if not line_s:
                continue
            try:
                obj = json.loads(line_s)
                if isinstance(obj, dict):
                    records.append(obj)
                    line_text = ", ".join(f"{k}: {v}" for k, v in obj.items())
                else:
                    records.append({"item": obj})
                    line_text = str(obj)
                text_lines.append(line_text)
            except Exception as e:
                doc.parsing_warnings.append(f"Line {line_num} JSON error: {e}")

        doc.structured_data = records
        doc.raw_text = "\n".join(text_lines)
        doc.paragraphs = text_lines
        doc.sections = [
            DocumentSection(
                title="JSON Lines Records",
                level=1,
                content="\n".join(text_lines[:100]),
            )
        ]

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc
