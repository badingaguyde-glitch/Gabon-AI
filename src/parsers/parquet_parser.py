"""Parser for statistical and columnar formats (Parquet, Feather, Stata DTA, SAS, SPSS SAV)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language


class ParquetParser(BaseParser):
    name = "parquet_parser"
    supported_formats = ["parquet", "feather", "stata", "dta", "spss", "sav", "sas", "sas7bdat"]

    def parse(
        self,
        file_path: str | Path,
        source_id: str,
        detected_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> InternalDocument:
        p = Path(file_path)
        fmt = detected_format or "parquet"
        doc = self.create_empty_doc(p, source_id, fmt, encoding="binary")

        try:
            import pandas as pd
            df = None
            if fmt == "parquet":
                df = pd.read_parquet(p)
            elif fmt == "feather":
                df = pd.read_feather(p)
            elif fmt in ("stata", "dta"):
                df = pd.read_stata(p)
            elif fmt in ("spss", "sav"):
                df = pd.read_spss(p)
            elif fmt in ("sas", "sas7bdat"):
                df = pd.read_sas(p)
            else:
                df = pd.read_parquet(p)

            df = df.fillna("")
            headers = [str(c) for c in df.columns]
            rows = df.astype(str).values.tolist()

            doc.tables = [
                TableData(
                    table_id="TABLE-001",
                    columns=headers,
                    rows=rows[:5000],  # cap for memory
                    source_id=source_id,
                )
            ]

            records: List[Dict[str, Any]] = []
            text_lines: List[str] = []
            for r in rows[:500]:
                rec = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
                records.append(rec)
                text_lines.append(", ".join(f"{k}: {v}" for k, v in rec.items() if v))

            doc.structured_data = records
            doc.raw_text = "\n".join(text_lines)
            doc.paragraphs = text_lines
            doc.sections = [DocumentSection(title="Columnar Dataset", level=1, content=doc.raw_text[:2000])]
        except Exception as e:
            doc.parsing_warnings.append(f"Columnar data parse error: {e}")

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc
