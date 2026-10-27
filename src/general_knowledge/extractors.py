"""Specialized extractors turning heterogeneous documents into country-level knowledge units.

Knowledge unit types:
- chunk      : a self-contained passage of text (legal article, report section, dataset description...)
- indicator  : a numeric time series (e.g. World Bank WDI: one indicator, many years)
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from src.models import InternalDocument
from src.general_knowledge.taxonomy import wb_indicator_category

PAGE_MARKER = re.compile(r"-{2,}\s*\[Page\s+\d+\]\s*-{2,}")


# --------------------------------------------------------------------------- text utils
def clean_text(text: str) -> str:
    text = PAGE_MARKER.sub("\n", text or "")
    text = text.replace("\u00a0", " ").replace("\u202f", " ").replace("\ufeff", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # de-hyphenation across lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = 1400, min_chars: int = 200) -> List[str]:
    """Paragraph-aware chunking; long paragraphs are split on sentence boundaries."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    buf = ""
    for p in paragraphs:
        if len(p) > max_chars:
            sentences = re.split(r"(?<=[.!?;])\s+", p)
            for s in sentences:
                if len(buf) + len(s) + 1 > max_chars and len(buf) >= min_chars:
                    chunks.append(buf.strip())
                    buf = ""
                buf += (" " if buf else "") + s
            continue
        if len(buf) + len(p) + 2 > max_chars and len(buf) >= min_chars:
            chunks.append(buf.strip())
            buf = ""
        buf += ("\n\n" if buf else "") + p
    if buf.strip():
        if chunks and len(buf) < min_chars:
            chunks[-1] += "\n\n" + buf.strip()
        else:
            chunks.append(buf.strip())
    return chunks


def title_from_filename(filename: str) -> str:
    stem = filename
    for ext in (".crdownload", ".pdf", ".txt", ".md", ".csv", ".docx", ".json", ".xlsx"):
        if stem.lower().endswith(ext):
            stem = stem[: -len(ext)]
    stem = re.sub(r"\[\d+\]", "", stem)
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:1].upper() + stem[1:] if stem else filename


# --------------------------------------------------------------------------- World Bank
class WorldBankExtractor:
    """World Bank WDI 'API_XXX_DS2' CSV (4 metadata lines then wide year columns)."""

    @staticmethod
    def is_wdi_data(path: Path) -> bool:
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                head = "".join(f.readline() for _ in range(6))
            return '"Indicator Name"' in head and '"Country Code"' in head
        except Exception:
            return False

    @staticmethod
    def is_wdi_indicator_metadata(path: Path) -> bool:
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                head = f.readline()
            return "INDICATOR_CODE" in head and "SOURCE_NOTE" in head
        except Exception:
            return False

    @staticmethod
    def extract_indicators(path: Path) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = f.readlines()
        start = next(i for i, l in enumerate(lines) if l.startswith('"Country Name"'))
        reader = csv.reader(lines[start:])
        header = next(reader)
        year_cols = [(i, h) for i, h in enumerate(header) if re.fullmatch(r"\d{4}", h.strip())]
        indicators: List[Dict[str, Any]] = []
        for row in reader:
            if len(row) < 4 or not row[2].strip():
                continue
            values: Dict[str, float] = {}
            for i, year in year_cols:
                if i < len(row) and row[i].strip():
                    try:
                        v = float(row[i])
                        if not math.isnan(v):
                            values[year] = v
                    except ValueError:
                        pass
            if not values:
                continue
            code = row[3].strip()
            indicators.append({
                "country": row[0].strip(),
                "country_code": row[1].strip(),
                "indicator_name": row[2].strip(),
                "indicator_code": code,
                "category": wb_indicator_category(code),
                "values": values,
                "source_dataset": "World Bank - World Development Indicators",
            })
        return indicators

    @staticmethod
    def extract_definitions(path: Path) -> Dict[str, Dict[str, str]]:
        defs: Dict[str, Dict[str, str]] = {}
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            for row in csv.DictReader(f):
                code = (row.get("INDICATOR_CODE") or "").strip()
                if code:
                    defs[code] = {
                        "definition": (row.get("SOURCE_NOTE") or "").strip(),
                        "source_organization": (row.get("SOURCE_ORGANIZATION") or "").strip(),
                    }
        return defs


# --------------------------------------------------------------------------- DDI / survey metadata
class DDIExtractor:
    """DDI-JSON survey metadata (World Bank microdata catalog, e.g. DHS)."""

    FIELDS = [
        ("study_desc.title_statement.title", "Titre de l'enquête"),
        ("study_desc.title_statement.alternate_title", "Titre alternatif"),
        ("study_desc.authoring_entity", "Organisme producteur"),
        ("study_desc.study_info.abstract", "Résumé"),
        ("study_desc.study_info.geog_coverage", "Couverture géographique"),
        ("study_desc.study_info.analysis_unit", "Unité d'analyse"),
        ("study_desc.study_info.universe", "Population étudiée"),
        ("study_desc.study_info.coll_dates", "Dates de collecte"),
        ("study_desc.study_info.keywords", "Mots-clés"),
        ("study_desc.study_info.topics", "Thèmes"),
        ("study_desc.method.data_collection.sampling_procedure", "Procédure d'échantillonnage"),
        ("study_desc.method.data_collection.coll_mode", "Mode de collecte"),
        ("study_desc.method.data_collection.research_instrument", "Questionnaires"),
        ("study_desc.method.data_collection.data_collectors", "Collecteurs de données"),
        ("study_desc.method.analysis_info.response_rate", "Taux de réponse"),
        ("study_desc.production_statement.funding_agencies", "Financement"),
        ("study_desc.series_statement.series_info", "Série"),
    ]

    @staticmethod
    def is_ddi(doc: InternalDocument) -> bool:
        head = doc.raw_text.lstrip()[:400]
        return head.startswith("{") and '"study_desc"' in doc.raw_text[:200000] and '"doc_desc"' in head

    @staticmethod
    def _get(data: Any, dotted: str) -> Any:
        cur = data
        for part in dotted.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur

    @staticmethod
    def _flatten(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            parts = [DDIExtractor._flatten(v) for v in value]
            return "; ".join(p for p in parts if p)
        if isinstance(value, dict):
            parts = []
            for k, v in value.items():
                fv = DDIExtractor._flatten(v)
                if fv and k not in ("uri", "vocab", "vocab_uri", "affiliation_uri"):
                    parts.append(fv if k in ("name", "keyword", "topic", "start", "end") else f"{k}: {fv}")
            return ", ".join(parts)
        return str(value)

    def extract(self, doc: InternalDocument) -> Tuple[str, List[Dict[str, str]]]:
        data = json.loads(doc.raw_text)
        title = self._flatten(self._get(data, "study_desc.title_statement.title")) or title_from_filename(doc.filename)
        sections: List[Dict[str, str]] = []
        for path, label in self.FIELDS:
            val = clean_text(self._flatten(self._get(data, path)))
            if val and len(val) > 3:
                sections.append({"section": label, "text": val})
        return title, sections


# --------------------------------------------------------------------------- legal texts
ARTICLE_RE = re.compile(
    r"(?:^|\n)\s*(Article\s+(?:premier|unique|1er|\d+(?:\s*(?:bis|ter|quater))?(?:[\-\.]\d+)*))\s*[:.\-–]?\s*",
    re.IGNORECASE,
)


class LegalTextExtractor:
    """Splits a legal text into articles with their hierarchical context (Titre / Chapitre / Section)."""

    HEADING_RE = re.compile(r"^\s*((?:TITRE|LIVRE|CHAPITRE|SECTION|SOUS-SECTION|PARAGRAPHE)\s+[^\n]{1,120})$",
                            re.IGNORECASE | re.MULTILINE)

    def extract(self, doc: InternalDocument) -> Tuple[str, List[Dict[str, str]]]:
        text = clean_text(doc.raw_text)
        title = self._guess_title(doc, text)
        matches = list(ARTICLE_RE.finditer(text))
        articles: List[Dict[str, str]] = []
        if len(matches) < 2:
            return title, []

        preamble = text[: matches[0].start()].strip()
        if len(preamble) > 80:
            articles.append({"article": "Préambule / Dispositions introductives", "context": "", "text": preamble[:6000]})

        current_ctx: Dict[str, str] = {}
        levels = ["LIVRE", "TITRE", "CHAPITRE", "SECTION", "SOUS-SECTION", "PARAGRAPHE"]
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[m.end():end].strip()
            ctx_for_this = " > ".join(current_ctx[l] for l in levels if l in current_ctx)[:300]
            # headings found at the end of this body belong to the FOLLOWING articles
            heads = list(self.HEADING_RE.finditer(body))
            if heads:
                body_main = body[:heads[0].start()].strip()
                for h in heads:
                    level = h.group(1).split()[0].upper()
                    if level in levels:
                        for lower in levels[levels.index(level):]:
                            current_ctx.pop(lower, None)
                    current_ctx[level] = h.group(1).strip()
            else:
                body_main = body
            if len(body_main) < 5:
                continue
            art_label = re.sub(r"\s+", " ", m.group(1)).strip().capitalize()
            articles.append({
                "article": art_label,
                "context": ctx_for_this,
                "text": body_main[:6000],
            })
        return title, articles

    @staticmethod
    def _guess_title(doc: InternalDocument, text: str) -> str:
        meta_title = (doc.document_metadata.get("title") or "").strip()
        head = text[:2500]
        m = re.search(r"((?:Loi|Ordonnance|Décret|Decret)\s+n\s*[°ºo]?\s*[\w/\-]+[^\n]{0,180})", head, re.IGNORECASE)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
        if "constitution" in doc.filename.lower():
            yr = re.search(r"(19|20)\d{2}", doc.filename)
            return f"Constitution de la République Gabonaise{' (' + yr.group(0) + ')' if yr else ''}"
        if meta_title and len(meta_title) > 5 and not meta_title.lower().startswith(("microsoft", "untitled")):
            return meta_title
        return title_from_filename(doc.filename)


# --------------------------------------------------------------------------- tabular datasets
class TabularDatasetSummarizer:
    """Describes a scientific/statistical table: schema, size, numeric stats, categorical top values."""

    NA = {"", "na", "n/a", "nan", "null", "none", "-"}

    def summarize(self, doc: InternalDocument, readme_text: str = "") -> Dict[str, Any]:
        if not doc.tables:
            return {}
        tab = doc.tables[0]
        cols = tab.columns
        rows = tab.rows
        numeric: Dict[str, Dict[str, float]] = {}
        categorical: Dict[str, List[Tuple[str, int]]] = {}
        for ci, col in enumerate(cols[:40]):
            vals = [str(r[ci]).strip() for r in rows if ci < len(r)]
            vals = [v for v in vals if v.lower() not in self.NA]
            if not vals:
                continue
            nums = []
            for v in vals:
                try:
                    nums.append(float(v.replace(",", ".")))
                except ValueError:
                    pass
            if len(nums) >= 0.8 * len(vals) and len(nums) >= 3:
                numeric[col] = {
                    "min": round(min(nums), 4), "max": round(max(nums), 4),
                    "mean": round(sum(nums) / len(nums), 4), "n": len(nums),
                }
            else:
                counts: Dict[str, int] = {}
                for v in vals:
                    counts[v] = counts.get(v, 0) + 1
                if 1 < len(counts) <= max(50, len(vals) // 2) or len(counts) == 1:
                    categorical[col] = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
        rows_kept = len(rows)
        return {
            "columns": cols,
            "rows_analyzed": rows_kept,
            "numeric_stats": numeric,
            "categorical_top_values": categorical,
            "readme": clean_text(readme_text)[:6000] if readme_text else "",
        }

    @staticmethod
    def describe(title: str, summary: Dict[str, Any], country: str) -> str:
        lines = [f"Jeu de données : {title} ({country})."]
        if summary.get("readme"):
            lines.append("Description : " + summary["readme"][:2500])
        lines.append(f"Colonnes ({len(summary.get('columns', []))}) : {', '.join(summary.get('columns', [])[:40])}.")
        lines.append(f"Nombre de lignes analysées : {summary.get('rows_analyzed', 0)}.")
        for col, st in list(summary.get("numeric_stats", {}).items())[:15]:
            lines.append(f"- {col} : min {st['min']}, max {st['max']}, moyenne {st['mean']} (n={st['n']}).")
        for col, top in list(summary.get("categorical_top_values", {}).items())[:10]:
            lines.append(f"- {col} : valeurs principales " + ", ".join(f"{v} ({c})" for v, c in top[:6]) + ".")
        return "\n".join(lines)


def find_readme(file_path: Path) -> str:
    """Looks for a README describing a dataset in the same folder (or a <stem>_README.md file)."""
    candidates = [file_path.with_name(file_path.stem + "_README.md")]
    candidates += [p for p in file_path.parent.glob("*") if p.is_file() and p.name.lower().startswith("readme")]
    for c in candidates:
        if c.exists() and c.is_file():
            try:
                return c.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
    return ""
