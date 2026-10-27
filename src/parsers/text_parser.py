"""Parser for text files, LaTeX, AsciiDoc, RST, Org-mode, and log files."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

from src.models import InternalDocument, DocumentSection
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding


class TextParser(BaseParser):
    name = "text_parser"
    supported_formats = [
        "text", "txt", "restructuredtext", "rst", "latex", "tex",
        "asciidoc", "adoc", "org_mode", "org", "log"
    ]

    def _clean_latex(self, text: str) -> str:
        """Strips basic LaTeX tags for cleaner scientific text extraction."""
        # Remove comments
        text = re.sub(r"%.*$", "", text, flags=re.MULTILINE)
        # Remove commands like \textbf{...}, \emph{...}
        text = re.sub(r"\\[a-zA-Z]+\*?(?:\[.*?\])?\{([^}]*)\}", r"\1", text)
        # Remove standalone commands \section, \begin, \end
        text = re.sub(r"\\[a-zA-Z]+\*?(?:\[.*?\])?", "", text)
        return text

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

        fmt = detected_format or "text"
        cleaned_content = content
        if fmt in ("latex", "tex"):
            cleaned_content = self._clean_latex(content)

        doc = self.create_empty_doc(p, source_id, fmt, encoding=enc)
        doc.raw_text = content

        # Break into sections based on simple delimiters or headers
        lines = cleaned_content.splitlines()
        paragraphs = []
        current_para = []

        for line in lines:
            if not line.strip():
                if current_para:
                    paragraphs.append(" ".join(current_para))
                    current_para = []
            else:
                current_para.append(line.strip())
        if current_para:
            paragraphs.append(" ".join(current_para))

        doc.paragraphs = paragraphs

        # Create basic sections
        if paragraphs:
            doc.sections = [
                DocumentSection(title="Body", level=1, content="\n\n".join(paragraphs))
            ]

        lang, conf = detect_text_language(cleaned_content)
        doc.language = lang
        doc.language_confidence = conf

        return doc
