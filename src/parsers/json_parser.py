"""JSON and GeoJSON structured data parser converting nested records into internal document model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models import InternalDocument, DocumentSection
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding


class JsonParser(BaseParser):
    name = "json_parser"
    supported_formats = ["json", "geojson"]

    def _flatten_json_to_text(self, obj: Any, prefix: str = "") -> List[str]:
        lines: List[str] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                key_name = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    lines.extend(self._flatten_json_to_text(v, key_name))
                else:
                    lines.append(f"{key_name}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                key_name = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    lines.extend(self._flatten_json_to_text(item, key_name))
                else:
                    lines.append(f"{key_name}: {item}")
        else:
            lines.append(f"{prefix}: {obj}")
        return lines

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
            data = json.loads(content_str)
        except Exception:
            try:
                content_str = raw_bytes.decode("latin-1", errors="replace")
                data = json.loads(content_str)
                enc = "latin-1"
            except Exception as e:
                doc = self.create_empty_doc(p, source_id, "json", encoding=enc)
                doc.parsing_warnings.append(f"Invalid JSON: {e}")
                doc.raw_text = raw_bytes.decode("latin-1", errors="replace")
                return doc

        doc = self.create_empty_doc(p, source_id, detected_format or "json", encoding=enc)

        if isinstance(data, list):
            doc.structured_data = data
        elif isinstance(data, dict):
            # Check GeoJSON
            if data.get("type") == "FeatureCollection":
                doc.structured_data = [
                    {**f.get("properties", {}), "geometry": f.get("geometry", {})}
                    for f in data.get("features", [])
                ]
            else:
                doc.structured_data = [data]
        else:
            doc.structured_data = [{"value": data}]

        text_lines = self._flatten_json_to_text(data)
        doc.raw_text = "\n".join(text_lines)
        doc.paragraphs = text_lines
        doc.sections = [
            DocumentSection(
                title="Structured JSON",
                level=1,
                content="\n".join(text_lines[:150]),
            )
        ]

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc
