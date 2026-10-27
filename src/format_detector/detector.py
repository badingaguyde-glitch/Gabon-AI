"""Intelligent multi-step format detector using magic bytes, MIME, extension, encodings, and content inspection."""

from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import charset_normalizer
except ImportError:
    charset_normalizer = None


class FormatDetectionResult:
    def __init__(
        self,
        format_name: str,
        parser_name: str,
        confidence: float,
        mime_type: Optional[str] = None,
        encoding: str = "utf-8",
        is_binary: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.format_name = format_name
        self.parser_name = parser_name
        self.confidence = confidence
        self.mime_type = mime_type
        self.encoding = encoding
        self.is_binary = is_binary
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format_name,
            "parser": self.parser_name,
            "confidence": round(self.confidence, 4),
            "mime_type": self.mime_type,
            "encoding": self.encoding,
            "is_binary": self.is_binary,
            "details": self.details,
        }


def compute_file_sha256(file_path: str | Path) -> str:
    """Computes SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def detect_file_encoding(sample_bytes: bytes) -> str:
    """Detects text encoding from byte sample, prioritizing UTF-8 and preserving accents."""
    if not sample_bytes:
        return "utf-8"

    # Quick BOM checks
    if sample_bytes.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if sample_bytes.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if sample_bytes.startswith(b"\xfe\xff"):
        return "utf-16-be"

    # Try utf-8 strict
    try:
        sample_bytes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # Use charset_normalizer if available
    if charset_normalizer is not None:
        try:
            best = charset_normalizer.from_bytes(sample_bytes).best()
            if best and best.encoding:
                return best.encoding
        except Exception:
            pass

    # Fallbacks
    for enc in ("cp1252", "iso-8859-1", "latin-1"):
        try:
            sample_bytes.decode(enc)
            return enc
        except Exception:
            continue

    return "utf-8"


class FormatDetector:
    """Detects format of files using magic signatures, mime, extension, and content."""

    MAGIC_SIGNATURES = [
        (b"%PDF-", "pdf", "pdf_parser", "application/pdf", True),
        (b"PK\x03\x04", "zip_based", "archive_parser", "application/zip", True),  # May be DOCX/XLSX/ZIP
        (b"PK\x05\x06", "zip", "archive_parser", "application/zip", True),
        (b"PK\x07\x08", "zip", "archive_parser", "application/zip", True),
        (b"7z\xbc\xaf\x27\x1c", "7z", "archive_parser", "application/x-7z-compressed", True),
        (b"\x1f\x8b\x08", "gzip", "archive_parser", "application/gzip", True),
        (b"BZh", "bzip2", "archive_parser", "application/x-bzip2", True),
        (b"\xfd7zXZ\x00", "xz", "archive_parser", "application/x-xz", True),
        (b"PAR1", "parquet", "parquet_parser", "application/vnd.apache.parquet", True),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole2", "excel_parser", "application/x-ole-storage", True),  # DOC/XLS/PPT
    ]

    TEXT_EXTENSIONS = {
        ".txt": ("text", "text_parser"),
        ".md": ("markdown", "markdown_parser"),
        ".markdown": ("markdown", "markdown_parser"),
        ".rst": ("restructuredtext", "text_parser"),
        ".log": ("log", "text_parser"),
        ".tex": ("latex", "text_parser"),
        ".latex": ("latex", "text_parser"),
        ".adoc": ("asciidoc", "text_parser"),
        ".org": ("org_mode", "text_parser"),
        ".csv": ("csv", "csv_parser"),
        ".tsv": ("tsv", "csv_parser"),
        ".tab": ("tsv", "csv_parser"),
        ".json": ("json", "json_parser"),
        ".jsonl": ("jsonl", "jsonl_parser"),
        ".ndjson": ("jsonl", "jsonl_parser"),
        ".xml": ("xml", "xml_parser"),
        ".yaml": ("yaml", "yaml_parser"),
        ".yml": ("yaml", "yaml_parser"),
        ".toml": ("toml", "generic_parser"),
        ".html": ("html", "html_parser"),
        ".htm": ("html", "html_parser"),
        ".xhtml": ("html", "html_parser"),
        ".kml": ("kml", "xml_parser"),
        ".geojson": ("geojson", "json_parser"),
        ".gpx": ("gpx", "xml_parser"),
    }

    BINARY_EXTENSIONS = {
        ".pdf": ("pdf", "pdf_parser", "application/pdf"),
        ".docx": ("docx", "docx_parser", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ".doc": ("doc", "docx_parser", "application/msword"),
        ".xlsx": ("excel", "excel_parser", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ".xls": ("excel", "excel_parser", "application/vnd.ms-excel"),
        ".ods": ("ods", "excel_parser", "application/vnd.oasis.opendocument.spreadsheet"),
        ".odt": ("odt", "docx_parser", "application/vnd.oasis.opendocument.text"),
        ".parquet": ("parquet", "parquet_parser", "application/vnd.apache.parquet"),
        ".feather": ("feather", "parquet_parser", "application/x-feather"),
        ".dta": ("stata", "parquet_parser", "application/x-stata"),
        ".sav": ("spss", "parquet_parser", "application/x-spss-sav"),
        ".sas7bdat": ("sas", "parquet_parser", "application/x-sas-data"),
        ".zip": ("zip", "archive_parser", "application/zip"),
        ".tar": ("tar", "archive_parser", "application/x-tar"),
        ".gz": ("gzip", "archive_parser", "application/gzip"),
        ".tgz": ("tar_gz", "archive_parser", "application/x-tar"),
        ".7z": ("7z", "archive_parser", "application/x-7z-compressed"),
    }

    @classmethod
    def detect(cls, file_path: str | Path) -> FormatDetectionResult:
        path = Path(file_path)
        if not path.is_file():
            return FormatDetectionResult("missing", "generic_parser", 0.0)

        ext = path.suffix.lower()
        mime_guess, _ = mimetypes.guess_type(str(path))

        # Read first 16KB for header inspection
        sample_bytes = b""
        try:
            with open(path, "rb") as f:
                sample_bytes = f.read(16384)
        except Exception as e:
            return FormatDetectionResult(
                "unreadable", "generic_parser", 0.0, details={"error": str(e)}
            )

        # 1. Magic byte signatures
        for sig, fmt, parser, mime, is_bin in cls.MAGIC_SIGNATURES:
            if sample_bytes.startswith(sig):
                # Distinguish ZIP vs DOCX vs XLSX vs ODT vs ODS
                if fmt == "zip_based":
                    if ext in (".docx", ".docm"):
                        return FormatDetectionResult(
                            "docx", "docx_parser", 0.98,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "binary", True, {"zip_type": "docx"}
                        )
                    if ext in (".xlsx", ".xlsm"):
                        return FormatDetectionResult(
                            "excel", "excel_parser", 0.98,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "binary", True, {"zip_type": "xlsx"}
                        )
                    if ext in (".ods", ".odt"):
                        p = "excel_parser" if ext == ".ods" else "docx_parser"
                        return FormatDetectionResult(
                            ext[1:], p, 0.95, mime_guess, "binary", True
                        )
                    # Check inside zip header for docx / xlsx markers
                    if b"word/document.xml" in sample_bytes or b"[Content_Types].xml" in sample_bytes:
                        if b"word/" in sample_bytes:
                            return FormatDetectionResult("docx", "docx_parser", 0.95, mime_guess, "binary", True)
                        if b"xl/" in sample_bytes:
                            return FormatDetectionResult("excel", "excel_parser", 0.95, mime_guess, "binary", True)
                    return FormatDetectionResult("zip", "archive_parser", 0.95, "application/zip", "binary", True)

                if fmt == "ole2":
                    if ext in (".xls", ".xla"):
                        return FormatDetectionResult("excel", "excel_parser", 0.95, mime_guess, "binary", True)
                    if ext in (".doc", ".dot"):
                        return FormatDetectionResult("doc", "docx_parser", 0.95, mime_guess, "binary", True)
                    return FormatDetectionResult("ole2_excel", "excel_parser", 0.85, mime_guess, "binary", True)

                return FormatDetectionResult(fmt, parser, 0.99, mime, "binary", is_bin)

        # 2. Binary extension match
        if ext in cls.BINARY_EXTENSIONS:
            fmt, parser, mime = cls.BINARY_EXTENSIONS[ext]
            return FormatDetectionResult(fmt, parser, 0.90, mime, "binary", True)

        # 3. Text content inspection
        encoding = detect_file_encoding(sample_bytes)
        try:
            sample_text = sample_bytes.decode(encoding)
        except Exception:
            # Maybe raw binary without standard magic
            is_probably_binary = b"\x00" in sample_bytes[:1024]
            if is_probably_binary:
                return FormatDetectionResult("unknown_binary", "generic_parser", 0.4, mime_guess, "binary", True)
            sample_text = sample_bytes.decode("latin-1", errors="replace")
            encoding = "latin-1"

        # Check for JSON / JSONL
        stripped = sample_text.strip()
        if stripped.startswith(("{", "[")):
            try:
                # Try parsing full file or sample as JSON
                json.loads(stripped)
                return FormatDetectionResult("json", "json_parser", 0.95, "application/json", encoding, False)
            except Exception:
                # Could be JSONL if first line is valid JSON
                first_line = stripped.split("\n", 1)[0].strip()
                if first_line.startswith("{") and first_line.endswith("}"):
                    try:
                        json.loads(first_line)
                        return FormatDetectionResult("jsonl", "jsonl_parser", 0.90, "application/x-ndjson", encoding, False)
                    except Exception:
                        pass

        # Check for XML / HTML
        if stripped.startswith("<?xml") or stripped.startswith("<html") or "<!doctype html" in stripped.lower():
            if "<html" in stripped.lower() or "<!doctype html" in stripped.lower():
                return FormatDetectionResult("html", "html_parser", 0.95, "text/html", encoding, False)
            return FormatDetectionResult("xml", "xml_parser", 0.95, "application/xml", encoding, False)

        # Check for Markdown indicators (Headings, Markdown tables, bold, list)
        md_score = 0
        if any(line.startswith(("# ", "## ", "### ", "#### ")) for line in stripped.splitlines()[:20]):
            md_score += 3
        if "|" in stripped and "-|-" in stripped.replace(" ", ""):
            md_score += 3
        if "**" in stripped or "* " in stripped or "- " in stripped:
            md_score += 1
        if ext in (".md", ".markdown"):
            md_score += 4

        if md_score >= 3:
            return FormatDetectionResult("markdown", "markdown_parser", 0.90, "text/markdown", encoding, False)

        # Check for Delimited Tabular (CSV / TSV)
        if ext in (".csv", ".tsv", ".tab") or ("," in stripped or "\t" in stripped or ";" in stripped):
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample_text[:4096])
                if dialect.delimiter in (",", "\t", ";", "|"):
                    fmt = "tsv" if dialect.delimiter == "\t" else "csv"
                    return FormatDetectionResult(
                        fmt, "csv_parser", 0.88 if ext in (".csv", ".tsv") else 0.75,
                        "text/csv", encoding, False, {"delimiter": dialect.delimiter}
                    )
            except Exception:
                pass

        # Check for YAML
        if stripped.startswith("---") or ("\n- " in sample_text and ":" in sample_text):
            if ext in (".yaml", ".yml"):
                return FormatDetectionResult("yaml", "yaml_parser", 0.90, "text/yaml", encoding, False)

        # Known text extension
        if ext in cls.TEXT_EXTENSIONS:
            fmt, parser = cls.TEXT_EXTENSIONS[ext]
            return FormatDetectionResult(fmt, parser, 0.85, mime_guess or "text/plain", encoding, False)

        # Fallback to generic text or unknown
        return FormatDetectionResult(
            "unknown_text", "generic_parser", 0.65, mime_guess or "text/plain", encoding, False
        )
