"""CSV/TSV tabular data parser with delimiter sniffing and structured record generation."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language
from src.format_detector import detect_file_encoding


class CsvParser(BaseParser):
    name = "csv_parser"
    supported_formats = ["csv", "tsv", "tab"]

    def parse(
        self,
        file_path: str | Path,
        source_id: str,
        detected_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> InternalDocument:
        p = Path(file_path)
        file_size = p.stat().st_size

        # For encoding and delimiter sniffing, read just first 64KB
        with open(p, "rb") as f:
            sample_bytes = f.read(65536)

        enc = encoding or detect_file_encoding(sample_bytes)
        try:
            sample_text = sample_bytes.decode(enc)
        except Exception:
            sample_text = sample_bytes.decode("latin-1", errors="replace")
            enc = "latin-1"

        doc = self.create_empty_doc(p, source_id, detected_format or "csv", encoding=enc)

        # Sniff delimiter
        delimiter = ","
        if "\t" in sample_text and sample_text.count("\t") > sample_text.count(","):
            delimiter = "\t"
        elif ";" in sample_text and sample_text.count(";") > sample_text.count(","):
            delimiter = ";"
        else:
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample_text[:8192])
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ","

        headers: List[str] = []
        body_rows: List[List[str]] = []
        max_rows_to_keep = 25000 if file_size > 10 * 1024 * 1024 else 100000

        with open(p, "r", encoding=enc, errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for r_idx, row in enumerate(reader):
                if not any(cell.strip() for cell in row):
                    continue
                if not headers:
                    headers = [h.strip() for h in row]
                else:
                    if len(body_rows) < max_rows_to_keep:
                        body_rows.append([cell.strip() for cell in row])
                    else:
                        break

        if not headers:
            doc.raw_text = sample_text
            return doc

        # Create TableData
        table = TableData(
            table_id="TABLE-001",
            columns=headers,
            rows=body_rows,
            source_id=source_id,
        )
        doc.tables = [table]

        # Convert to structured dictionary records (sample for text view, full in TableData)
        structured_records: List[Dict[str, Any]] = []
        text_lines: List[str] = []
        for idx, row in enumerate(body_rows):
            if idx < 5000:
                rec = {}
                for col_idx, col_name in enumerate(headers):
                    val = row[col_idx].strip() if col_idx < len(row) else ""
                    rec[col_name] = val
                structured_records.append(rec)

                # Human-readable summary line for semantic extraction
                if idx < 100:
                    rec_str = ", ".join(f"{k}: {v}" for k, v in rec.items() if v)
                    if rec_str:
                        text_lines.append(rec_str)

        doc.structured_data = structured_records
        doc.raw_text = f"CSV Table with {len(headers)} columns and {len(body_rows)} rows.\nColumns: {', '.join(headers)}\n\n" + "\n".join(text_lines)
        doc.paragraphs = text_lines

        doc.sections = [
            DocumentSection(
                title="Tabular Data",
                level=1,
                content=f"Columns: {', '.join(headers)}\n\n" + "\n".join(text_lines[:100]),
            )
        ]

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc
