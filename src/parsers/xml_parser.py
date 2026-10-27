"""XML, KML, and GPX parser extracting hierarchical nodes, coordinates, and structured tags."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class XmlParser(BaseParser):
    name = "xml_parser"
    supported_formats = ["xml", "kml", "gpx"]

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

        fmt = detected_format or "xml"
        doc = self.create_empty_doc(p, source_id, fmt, encoding=enc)

        structured_records: List[Dict[str, Any]] = []
        text_lines: List[str] = []

        try:
            tree = ET.fromstring(content_str)
            # Traverse nodes
            for elem in tree.iter():
                tag = elem.tag.split("}")[-1]  # remove namespace
                text = elem.text.strip() if elem.text and elem.text.strip() else ""
                if text:
                    text_lines.append(f"{tag}: {text}")
                    if elem.attrib:
                        structured_records.append({"tag": tag, "text": text, "attributes": elem.attrib})
                    else:
                        structured_records.append({"tag": tag, "text": text})
        except Exception as e:
            doc.parsing_warnings.append(f"XML parse warning: {e}")
            if BeautifulSoup is not None:
                soup = BeautifulSoup(content_str, "xml")
                text_lines = [t.strip() for t in soup.stripped_strings]
            else:
                text_lines = [re.sub(r"<[^>]+>", "", content_str)]

        doc.structured_data = structured_records
        doc.raw_text = "\n".join(text_lines)
        doc.paragraphs = text_lines
        doc.sections = [
            DocumentSection(
                title="XML Content",
                level=1,
                content="\n".join(text_lines[:100]),
            )
        ]

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc
