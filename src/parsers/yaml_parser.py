"""YAML configuration and structured dataset parser."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from src.models import InternalDocument, DocumentSection
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding


class YamlParser(BaseParser):
    name = "yaml_parser"
    supported_formats = ["yaml", "yml"]

    def _flatten(self, obj: Any, prefix: str = "") -> List[str]:
        lines = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_str = f"{prefix}.{k}" if prefix else str(k)
                if isinstance(v, (dict, list)):
                    lines.extend(self._flatten(v, k_str))
                else:
                    lines.append(f"{k_str}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                k_str = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    lines.extend(self._flatten(item, k_str))
                else:
                    lines.append(f"{k_str}: {item}")
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
        except Exception:
            content_str = raw_bytes.decode("latin-1", errors="replace")
            enc = "latin-1"

        doc = self.create_empty_doc(p, source_id, "yaml", encoding=enc)

        try:
            data = yaml.safe_load(content_str)
            if isinstance(data, list):
                doc.structured_data = data
            elif isinstance(data, dict):
                doc.structured_data = [data]
            else:
                doc.structured_data = [{"value": data}]

            text_lines = self._flatten(data)
            doc.raw_text = "\n".join(text_lines)
            doc.paragraphs = text_lines
        except Exception as e:
            doc.parsing_warnings.append(f"YAML parse error: {e}")
            doc.raw_text = content_str
            doc.paragraphs = [p for p in content_str.splitlines() if p.strip()]

        doc.sections = [DocumentSection(title="YAML Content", level=1, content=doc.raw_text)]
        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc
