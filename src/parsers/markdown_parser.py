"""Hierarchical Markdown parser preserving section headings, lists, tables, and scientific metadata."""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Optional

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding


class MarkdownParser(BaseParser):
    name = "markdown_parser"
    supported_formats = ["markdown", "md"]

    def _parse_markdown_tables(self, text: str, source_id: str) -> List[TableData]:
        tables: List[TableData] = []
        lines = text.splitlines()
        i = 0
        table_counter = 1

        while i < len(lines):
            line = lines[i].strip()
            if "|" in line and i + 1 < len(lines) and re.match(r"^\|?\s*[-:]+[-| :]*$", lines[i + 1].strip()):
                # Start of table
                header_line = line
                headers = [col.strip() for col in header_line.split("|")]
                headers = [h for h in headers if h]  # drop leading/trailing empty

                rows = []
                j = i + 2
                while j < len(lines) and "|" in lines[j]:
                    row_line = lines[j].strip()
                    row_cells = [cell.strip() for cell in row_line.split("|")]
                    # remove leading/trailing empties from markdown table borders
                    if row_line.startswith("|") and row_cells and row_cells[0] == "":
                        row_cells.pop(0)
                    if row_line.endswith("|") and row_cells and row_cells[-1] == "":
                        row_cells.pop(-1)
                    if any(c != "" for c in row_cells):
                        rows.append(row_cells)
                    j += 1

                if headers and rows:
                    tables.append(
                        TableData(
                            table_id=f"TABLE-{table_counter:03d}",
                            columns=headers,
                            rows=rows,
                            source_id=source_id,
                        )
                    )
                    table_counter += 1
                i = j
            else:
                i += 1

        return tables

    def _parse_sections(self, text: str) -> List[DocumentSection]:
        lines = text.splitlines()
        sections: List[DocumentSection] = []
        current_sec: Optional[DocumentSection] = None
        current_lines: List[str] = []

        heading_re = re.compile(r"^(#{1,6})\s+(.*)$")

        for line in lines:
            m = heading_re.match(line.strip())
            if m:
                # Save previous section
                if current_sec:
                    current_sec.content = "\n".join(current_lines).strip()
                    sections.append(current_sec)
                elif current_lines and any(l.strip() for l in current_lines):
                    # Intro section before first heading
                    intro_content = "\n".join(current_lines).strip()
                    if intro_content:
                        sections.append(
                            DocumentSection(title="Overview", level=1, content=intro_content)
                        )

                hashes, title = m.groups()
                level = len(hashes)
                current_sec = DocumentSection(title=title.strip(), level=level, content="")
                current_lines = []
            else:
                current_lines.append(line)

        if current_sec:
            current_sec.content = "\n".join(current_lines).strip()
            sections.append(current_sec)
        elif current_lines:
            intro_content = "\n".join(current_lines).strip()
            if intro_content:
                sections.append(DocumentSection(title="Main", level=1, content=intro_content))

        return sections

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

        doc = self.create_empty_doc(p, source_id, "markdown", encoding=enc)
        doc.raw_text = content
        doc.sections = self._parse_sections(content)
        doc.tables = self._parse_markdown_tables(content, source_id)

        # Paragraphs
        doc.paragraphs = [
            p.strip() for p in re.split(r"\n\s*\n", content) if p.strip() and not p.strip().startswith("#")
        ]

        lang, conf = detect_text_language(content)
        doc.language = lang
        doc.language_confidence = conf

        return doc
