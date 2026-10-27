"""Country-centric, incremental and deduplicated knowledge store + document-to-knowledge builder.

Layout:
knowledge/
├── index.json                         # doc_id -> {country, category, subcategory, kind, title, files...}
├── chunk_hashes.json                  # normalized text hash -> chunk_id (cross-document dedup)
├── _shared/indicator_definitions.json # indicator code -> definition (country independent)
└── <country>/
    ├── indicators.json                # code -> {name, category, values{year: {value, sources}}, conflicts}
    └── <category>/<doc_id>.json       # document record with its chunks
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from src.models import InternalDocument
from src.general_knowledge.classifier import DomainClassifier, Classification, strip_accents
from src.general_knowledge.extractors import (
    WorldBankExtractor, DDIExtractor, LegalTextExtractor, TabularDatasetSummarizer,
    clean_text, chunk_text, title_from_filename, find_readme,
)

TABULAR_FORMATS = {
    "csv", "tsv", "tab", "excel", "xlsx", "xls", "ods", "ole2", "ole2_excel",
    "parquet", "feather", "stata", "dta", "spss", "sav", "sas", "sas7bdat",
}


def slugify(s: str) -> str:
    s = strip_accents(s).lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_") or "unknown"


def text_hash(s: str) -> str:
    norm = re.sub(r"\W+", " ", strip_accents(s).lower()).strip()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


class KnowledgeStore:
    def __init__(self, base_dir: str | Path):
        self.root = Path(base_dir) / "knowledge"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index: Dict[str, Dict[str, Any]] = _load(self.root / "index.json", {})
        self.chunk_hashes: Dict[str, str] = _load(self.root / "chunk_hashes.json", {})
        self.definitions: Dict[str, Dict[str, str]] = _load(self.root / "_shared" / "indicator_definitions.json", {})
        self._indicators_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ documents
    def save_document(self, record: Dict[str, Any]) -> Dict[str, int]:
        doc_id = record["doc_id"]
        unique, dup = 0, 0
        for ch in record["chunks"]:
            h = text_hash(ch["text"])
            ch["text_hash"] = h
            owner = self.chunk_hashes.get(h)
            if owner and not owner.startswith(doc_id + "-"):
                ch["duplicate_of"] = owner
                dup += 1
            else:
                self.chunk_hashes[h] = ch["chunk_id"]
                ch.pop("duplicate_of", None)
                unique += 1

        prev = self.index.get(doc_id, {})
        files = sorted(set(prev.get("source_files", [])) | set(record.get("source_files", [])))
        record["source_files"] = files
        path = self.root / slugify(record["country"]) / record["category"] / f"{doc_id}.json"
        # if category changed after a re-run, remove the stale file
        if prev.get("path") and prev["path"] != str(path.relative_to(self.root)):
            stale = self.root / prev["path"]
            if stale.exists():
                stale.unlink()
        _save(path, record)
        self.index[doc_id] = {
            "country": record["country"], "category": record["category"],
            "subcategory": record.get("subcategory"), "kind": record["kind"], "title": record["title"],
            "source_files": files, "n_chunks": len(record["chunks"]), "unique_chunks": unique,
            "path": str(path.relative_to(self.root)), "updated_at": _now(),
        }
        return {"unique": unique, "duplicates": dup}

    def iter_documents(self):
        for doc_id, meta in self.index.items():
            p = self.root / meta["path"]
            if p.exists():
                yield json.loads(p.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ indicators
    def _indicators(self, country: str) -> Dict[str, Any]:
        key = slugify(country)
        if key not in self._indicators_cache:
            self._indicators_cache[key] = _load(self.root / key / "indicators.json", {})
        return self._indicators_cache[key]

    def merge_indicators(self, country: str, items: List[Dict[str, Any]], doc_id: str) -> Dict[str, int]:
        store = self._indicators(country)
        stats = {"new_values": 0, "confirmed_values": 0, "conflicts": 0, "indicators": len(items)}
        for it in items:
            rec = store.setdefault(it["indicator_code"], {
                "indicator_code": it["indicator_code"], "indicator_name": it["indicator_name"],
                "category": it["category"], "source_dataset": it.get("source_dataset"),
                "values": {}, "conflicts": [],
            })
            rec["category"] = it["category"]
            for year, v in it["values"].items():
                cur = rec["values"].get(year)
                if cur is None:
                    rec["values"][year] = {"value": v, "sources": [doc_id]}
                    stats["new_values"] += 1
                elif abs(cur["value"] - v) <= 1e-9 * max(1.0, abs(v)):
                    if doc_id not in cur["sources"]:
                        cur["sources"].append(doc_id)
                    stats["confirmed_values"] += 1
                else:
                    known = {(c["year"], c["value"]) for c in rec["conflicts"]}
                    if (year, v) not in known:
                        rec["conflicts"].append({"year": year, "value": v, "source": doc_id,
                                                 "kept_value": cur["value"], "status": "requires_review"})
                        stats["conflicts"] += 1
        return stats

    def merge_definitions(self, defs: Dict[str, Dict[str, str]]) -> int:
        n = 0
        for code, d in defs.items():
            if code not in self.definitions or not self.definitions[code].get("definition"):
                self.definitions[code] = d
                n += 1
        return n

    def all_indicators(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for d in self.root.iterdir():
            if d.is_dir() and not d.name.startswith("_"):
                out[d.name] = self._indicators(d.name)
        return out

    def save(self) -> None:
        _save(self.root / "index.json", self.index)
        _save(self.root / "chunk_hashes.json", self.chunk_hashes)
        _save(self.root / "_shared" / "indicator_definitions.json", self.definitions)
        for key, data in self._indicators_cache.items():
            if data:
                _save(self.root / key / "indicators.json", data)


class KnowledgeBuilder:
    """Routes every parsed document to the right extractor and stores country/category knowledge."""

    def __init__(self, base_dir: str | Path, default_country: str = "Gabon"):
        self.store = KnowledgeStore(base_dir)
        self.classifier = DomainClassifier(default_country)
        self.legal = LegalTextExtractor()
        self.ddi = DDIExtractor()
        self.tabular = TabularDatasetSummarizer()

    def process(self, doc: InternalDocument, file_path: Path, rel_path: str, sha256: str,
                dry_run: bool = False) -> Dict[str, Any]:
        doc_id = f"DOC-{sha256[:12]}"
        cls: Classification = self.classifier.classify(doc, rel_path)
        base = {
            "doc_id": doc_id, "country": cls.country, "category": cls.category,
            "subcategory": cls.subcategory, "secondary_categories": cls.secondary_categories,
            "classification_confidence": cls.confidence, "language": doc.language,
            "source_files": [rel_path or file_path.name], "sha256": sha256, "format": doc.format,
            "processed_at": _now(),
        }

        # 1. World Bank indicator data / definitions
        if WorldBankExtractor.is_wdi_data(file_path):
            items = WorldBankExtractor.extract_indicators(file_path)
            country = items[0]["country"] if items else cls.country
            stats = {} if dry_run else self.store.merge_indicators(country, items, doc_id)
            return {**base, "country": country, "category": "multi", "kind": "indicators",
                    "n_indicators": len(items), **stats}
        if WorldBankExtractor.is_wdi_indicator_metadata(file_path):
            defs = WorldBankExtractor.extract_definitions(file_path)
            n = 0 if dry_run else self.store.merge_definitions(defs)
            return {**base, "category": "multi", "kind": "indicator_definitions", "n_definitions": len(defs), "new": n}

        chunks: List[Dict[str, Any]] = []
        title = title_from_filename(doc.filename)
        kind = "text"

        # 2. Survey metadata (DDI JSON)
        if DDIExtractor.is_ddi(doc):
            kind = "survey_metadata"
            title, sections = self.ddi.extract(doc)
            for s in sections:
                for part in chunk_text(s["text"]):
                    chunks.append({"section": s["section"], "text": part})

        # 3. Legal texts (article-level)
        if kind == "text" and (cls.category == "droit" or cls.scores.get("droit", 0) >= 15):
            ltitle, articles = self.legal.extract(doc)
            if len(articles) >= 3:
                kind = "legal_text"
                title = ltitle
                topic = cls.category if cls.category != "droit" else None
                base["category"] = "droit"
                if topic and topic not in base["secondary_categories"]:
                    base["secondary_categories"] = [topic] + base["secondary_categories"]
                for a in articles:
                    chunks.append({"article": a["article"], "context": a["context"], "text": a["text"]})

        # 4. Tabular datasets
        if kind == "text" and doc.tables and doc.format in TABULAR_FORMATS:
            kind = "dataset"
            readme = find_readme(file_path)
            summary = self.tabular.summarize(doc, readme)
            if readme:
                first = next((l.strip("# ").strip() for l in readme.splitlines() if l.strip().startswith("#")), "")
                if first:
                    title = f"{first} — {file_path.name}"
            base["dataset_summary"] = summary
            chunks.append({"section": "Description du jeu de données",
                           "text": self.tabular.describe(title, summary, cls.country)})

        # 5. Generic text (reports, README, markdown, txt, docx, html...)
        if kind == "text":
            meta_title = (doc.document_metadata.get("title") or "").strip()
            if meta_title and len(meta_title) > 5:
                title = meta_title
            md_title = next((l.strip("# ").strip() for l in doc.raw_text.splitlines()[:5] if l.startswith("#")), "")
            if md_title:
                title = md_title
            if doc.sections and len(doc.sections) > 1:
                for sec in doc.sections:
                    for part in chunk_text(clean_text(sec.content)):
                        chunks.append({"section": sec.title, "text": part})
            else:
                for part in chunk_text(clean_text(doc.raw_text)):
                    chunks.append({"section": "", "text": part})

        chunks = [c for c in chunks if len(c["text"].strip()) >= 40]
        for i, c in enumerate(chunks, 1):
            c["chunk_id"] = f"{doc_id}-C{i:04d}"

        record = {**base, "kind": kind, "title": title, "chunks": chunks}
        stats = {"unique": len(chunks), "duplicates": 0} if dry_run else self.store.save_document(record)
        return {**base, "category": record["category"], "kind": kind, "title": title,
                "n_chunks": len(chunks), **stats}

    def save(self) -> None:
        self.store.save()
