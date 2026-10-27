"""Excel spreadsheet (.xlsx, .xls, .ods) parser extracting all sheets into tables and structured records."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
import zipfile

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language


class ExcelParser(BaseParser):
    name = "excel_parser"
    supported_formats = ["excel", "xlsx", "xls", "ods", "ole2", "ole2_excel"]

    def _parse_with_pandas(self, file_path: Path, source_id: str) -> Optional[InternalDocument]:
        import pandas as pd

        try:
            excel_file = pd.ExcelFile(str(file_path))
        except Exception:
            return None

        doc = self.create_empty_doc(file_path, source_id, "excel", encoding="utf-8")
        tables: List[TableData] = []
        structured_records: List[Dict[str, Any]] = []
        text_lines: List[str] = []

        for sheet_idx, sheet_name in enumerate(excel_file.sheet_names, start=1):
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                df = df.fillna("")
                headers = [str(col).strip() for col in df.columns]
                rows = df.astype(str).values.tolist()

                clean_rows = []
                for r in rows:
                    if any(cell.strip() for cell in r):
                        clean_rows.append([c.strip() for c in r])

                tables.append(
                    TableData(
                        table_id=f"SHEET-{sheet_idx:02d}",
                        columns=headers,
                        rows=clean_rows,
                        source_id=source_id,
                        caption=sheet_name,
                    )
                )

                for r in clean_rows:
                    rec = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
                    rec["_sheet"] = sheet_name
                    structured_records.append(rec)
                    line_str = f"[{sheet_name}] " + ", ".join(f"{k}: {v}" for k, v in rec.items() if v and not k.startswith("_"))
                    text_lines.append(line_str)
            except Exception as e:
                doc.parsing_warnings.append(f"Failed to parse sheet '{sheet_name}': {e}")

        doc.tables = tables
        doc.structured_data = structured_records
        doc.raw_text = "\n".join(text_lines)
        doc.paragraphs = text_lines
        doc.sections = [
            DocumentSection(
                title=f"Spreadsheet ({len(tables)} sheets)",
                level=1,
                content="\n".join(text_lines[:100]),
            )
        ]

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc

    def _parse_xlsx_raw_xml(self, file_path: Path, source_id: str) -> InternalDocument:
        """Fallback for .xlsx by directly parsing sharedStrings.xml and sheet1.xml."""
        doc = self.create_empty_doc(file_path, source_id, "excel", encoding="utf-8")
        shared_strings: List[str] = []
        text_lines: List[str] = []

        try:
            with zipfile.ZipFile(file_path, "r") as z:
                # Read shared strings if present
                if "xl/sharedStrings.xml" in z.namelist():
                    tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                    ns = {"ns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                    for si in tree.findall(".//ns:si", ns) or tree.findall(".//si"):
                        t = si.find(".//ns:t", ns) if tree.find(".//ns:t", ns) is not None else si.find(".//t")
                        shared_strings.append(t.text.strip() if (t is not None and t.text) else "")

                # Read sheet1.xml
                sheet_files = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]
                for s_file in sheet_files:
                    tree = ET.fromstring(z.read(s_file))
                    for row in tree.findall(".//{*}row"):
                        row_cells = []
                        for cell in row.findall(".//{*}c"):
                            cell_type = cell.attrib.get("t")
                            v = cell.find(".//{*}v")
                            val = v.text if v is not None and v.text else ""
                            if cell_type == "s" and val.isdigit() and int(val) < len(shared_strings):
                                val = shared_strings[int(val)]
                            row_cells.append(val)
                        if any(c.strip() for c in row_cells):
                            text_lines.append(" | ".join(row_cells))

            doc.raw_text = "\n".join(text_lines)
            doc.paragraphs = text_lines
            doc.sections = [DocumentSection(title="Extracted Spreadsheet", level=1, content=doc.raw_text)]
            lang, conf = detect_text_language(doc.raw_text)
            doc.language = lang
            doc.language_confidence = conf
        except Exception as e:
            doc.parsing_warnings.append(f"Direct XML spreadsheet parse failed: {e}")

        return doc

    def parse(
        self,
        file_path: str | Path,
        source_id: str,
        detected_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> InternalDocument:
        p = Path(file_path)

        # Try pandas first
        res = self._parse_with_pandas(p, source_id)
        if res is not None and (res.tables or res.raw_text):
            return res

        # Fallback to direct XML parsing if xlsx
        return self._parse_xlsx_raw_xml(p, source_id)
