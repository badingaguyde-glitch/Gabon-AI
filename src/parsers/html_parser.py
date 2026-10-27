"""HTML and web page parser extracting headings, structured paragraphs, and HTML tables."""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Optional

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class HtmlParser(BaseParser):
    name = "html_parser"
    supported_formats = ["html", "htm", "xhtml"]

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

        doc = self.create_empty_doc(p, source_id, "html", encoding=enc)

        if BeautifulSoup is not None:
            soup = BeautifulSoup(content_str, "html.parser")

            # Page title
            title_elem = soup.find("title")
            if title_elem and title_elem.string:
                doc.document_metadata["title"] = title_elem.string.strip()

            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()

            # Extract HTML tables
            tables: List[TableData] = []
            for idx, html_tab in enumerate(soup.find_all("table"), start=1):
                headers = [th.get_text().strip() for th in html_tab.find_all("th")]
                body_rows = []
                for tr in html_tab.find_all("tr"):
                    cells = [td.get_text().strip() for td in tr.find_all("td")]
                    if cells:
                        body_rows.append(cells)

                if body_rows:
                    if not headers and body_rows:
                        headers = [f"col_{i+1}" for i in range(len(body_rows[0]))]
                    tables.append(
                        TableData(
                            table_id=f"TABLE-{idx:03d}",
                            columns=headers,
                            rows=body_rows,
                            source_id=source_id,
                        )
                    )
            doc.tables = tables

            # Headings and sections
            sections: List[DocumentSection] = []
            current_sec: Optional[DocumentSection] = None
            for elem in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                if elem.name in ("h1", "h2", "h3"):
                    level = int(elem.name[1])
                    if current_sec:
                        sections.append(current_sec)
                    current_sec = DocumentSection(title=elem.get_text().strip(), level=level, content="")
                else:
                    t = elem.get_text().strip()
                    if t:
                        if current_sec:
                            current_sec.content = (current_sec.content + "\n" + t).strip()
                        doc.paragraphs.append(t)

            if current_sec:
                sections.append(current_sec)

            doc.sections = sections or [DocumentSection(title="Body", level=1, content="\n\n".join(doc.paragraphs))]
            doc.raw_text = soup.get_text(separator="\n").strip()
        else:
            # Simple regex fallback
            clean_text = re.sub(r"<[^>]+>", " ", content_str)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            doc.raw_text = clean_text
            doc.paragraphs = [p.strip() for p in clean_text.split(". ") if p.strip()]
            doc.sections = [DocumentSection(title="Body", level=1, content=clean_text)]

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc
