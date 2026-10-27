"""Extensible Parser Registry with plugin architecture for registering custom parsers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Type

from src.models import InternalDocument
from src.format_detector import FormatDetector, FormatDetectionResult
from src.parsers.base_parser import BaseParser
from src.parsers.text_parser import TextParser
from src.parsers.markdown_parser import MarkdownParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.docx_parser import DocxParser
from src.parsers.csv_parser import CsvParser
from src.parsers.excel_parser import ExcelParser
from src.parsers.json_parser import JsonParser
from src.parsers.jsonl_parser import JsonlParser
from src.parsers.xml_parser import XmlParser
from src.parsers.yaml_parser import YamlParser
from src.parsers.html_parser import HtmlParser
from src.parsers.parquet_parser import ParquetParser
from src.parsers.archive_parser import ArchiveParser
from src.parsers.generic_parser import GenericParser


class ParserRegistry:
    """Central registry of modular parsers enabling dynamic plugin registration."""

    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._format_map: Dict[str, BaseParser] = {}
        self._generic_parser = GenericParser()

        # Register default parsers
        self.register_parser(TextParser())
        self.register_parser(MarkdownParser())
        self.register_parser(PdfParser())
        self.register_parser(DocxParser())
        self.register_parser(CsvParser())
        self.register_parser(ExcelParser())
        self.register_parser(JsonParser())
        self.register_parser(JsonlParser())
        self.register_parser(XmlParser())
        self.register_parser(YamlParser())
        self.register_parser(HtmlParser())
        self.register_parser(ParquetParser())

        # Archive parser needs access to registry
        archive_p = ArchiveParser(self)
        self.register_parser(archive_p)

        self.register_parser(self._generic_parser)

    def register_parser(self, parser: BaseParser) -> None:
        """Registers a parser instance and associates its supported formats."""
        self._parsers[parser.name] = parser
        for fmt in parser.supported_formats:
            self._format_map[fmt.lower()] = parser

    def get_parser_by_name(self, name: str) -> Optional[BaseParser]:
        return self._parsers.get(name)

    def get_parser_for_format(self, format_name: str) -> BaseParser:
        fmt = (format_name or "").lower()
        if fmt in self._format_map:
            return self._format_map[fmt]
        return self._generic_parser

    def select_parser(self, file_path: str | Path) -> tuple[BaseParser, FormatDetectionResult]:
        """Detects format and returns matching parser and detection metadata."""
        detection = FormatDetector.detect(file_path)

        # Check by suggested parser name first
        if detection.parser_name in self._parsers:
            return self._parsers[detection.parser_name], detection

        # Check by format name
        if detection.format_name in self._format_map:
            return self._format_map[detection.format_name], detection

        # Fallback to can_parse search
        for parser in self._parsers.values():
            if parser.can_parse(file_path, detection.format_name):
                return parser, detection

        return self._generic_parser, detection

    def parse_file(self, file_path: str | Path, source_id: str) -> InternalDocument:
        """Parses any file into standard InternalDocument."""
        parser, detection = self.select_parser(file_path)
        doc = parser.parse(
            file_path=file_path,
            source_id=source_id,
            detected_format=detection.format_name,
            encoding=detection.encoding,
        )
        doc.detected_mime = detection.mime_type
        return doc


# Global default instance
default_registry = ParserRegistry()
