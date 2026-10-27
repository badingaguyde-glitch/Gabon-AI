"""Word document (.docx, .doc, .odt) parser extracting headings, paragraphs, and tables."""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Optional
import zipfile
import xml.etree.ElementTree as ET

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language


class DocxParser(BaseParser):
    name = "docx_parser"
    supported_formats = ["docx", "doc", "odt", "rtf"]

    def _parse_with_docx(self, file_path: Path, source_id: str) -> InternalDocument:
        import docx

        doc_obj = docx.Document(str(file_path))
        doc = self.create_empty_doc(file_path, source_id, "docx", encoding="utf-8")

        sections: List[DocumentSection] = []
        current_sec: Optional[DocumentSection] = None
        paragraphs_text: List[str] = []

        for p in doc_obj.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            style_name = p.style.name.lower() if p.style else ""
            if "heading 1" in style_name or "heading 2" in style_name or "heading 3" in style_name:
                level = 1 if "heading 1" in style_name else (2 if "heading 2" in style_name else 3)
                if current_sec:
                    sections.append(current_sec)
                current_sec = DocumentSection(title=text, level=level, content="")
            else:
                if current_sec:
                    current_sec.content = (current_sec.content + "\n" + text).strip()
                paragraphs_text.append(text)

        if current_sec:
            sections.append(current_sec)

        # Tables
        tables: List[TableData] = []
        for idx, table in enumerate(doc_obj.tables, start=1):
            rows_data = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                rows_data.append(row_data)
            if rows_data:
                headers = rows_data[0]
                body_rows = rows_data[1:] if len(rows_data) > 1 else rows_data
                tables.append(
                    TableData(
                        table_id=f"TABLE-{idx:03d}",
                        columns=headers,
                        rows=body_rows,
                        source_id=source_id,
                    )
                )

        doc.sections = sections or [DocumentSection(title="Body", level=1, content="\n\n".join(paragraphs_text))]
        doc.paragraphs = paragraphs_text
        doc.tables = tables
        doc.raw_text = "\n\n".join(paragraphs_text)

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc

    def _parse_with_zip_xml(self, file_path: Path, source_id: str) -> InternalDocument:
        """Fallback for docx/odt by unzipping word/document.xml or content.xml."""
        doc = self.create_empty_doc(file_path, source_id, "docx", encoding="utf-8")
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                xml_filename = "word/document.xml" if "word/document.xml" in z.namelist() else "content.xml"
                if xml_filename in z.namelist():
                    xml_content = z.read(xml_filename)
                    tree = ET.fromstring(xml_content)
                    texts = [elem.text for elem in tree.iter() if elem.text and elem.text.strip()]
                    full_text = " ".join(texts)
                    doc.raw_text = full_text
                    doc.paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]
                    doc.sections = [DocumentSection(title="Body", level=1, content=full_text)]
                    lang, conf = detect_text_language(full_text)
                    doc.language = lang
                    doc.language_confidence = conf
        except Exception as e:
            doc.parsing_warnings.append(f"Zip XML extraction fallback failed: {e}")
        return doc

    def parse(
        self,
        file_path: str | Path,
        source_id: str,
        detected_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> InternalDocument:
        p = Path(file_path)
        try:
            return self._parse_with_docx(p, source_id)
        except Exception:
            return self._parse_with_zip_xml(p, source_id)
