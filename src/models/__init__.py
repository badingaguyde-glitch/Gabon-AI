"""Data models for internal representation of documents, facts, entities, and logs."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import uuid


@dataclass
class SourceProvenance:
    source_id: str
    filename: str
    file_path: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    table_id: Optional[str] = None
    line_number: Optional[int] = None
    extracted_text_snippet: Optional[str] = None
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TableData:
    table_id: str
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    source_id: str = ""
    caption: Optional[str] = None
    page: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentSection:
    title: str
    level: int = 1
    content: str = ""
    subsections: List[DocumentSection] = field(default_factory=list)
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "level": self.level,
            "content": self.content,
            "subsections": [s.to_dict() for s in self.subsections],
            "page_start": self.page_start,
            "page_end": self.page_end,
        }


@dataclass
class InternalDocument:
    source_id: str
    filename: str
    file_path: str
    sha256: str
    format: str
    detected_mime: Optional[str] = None
    encoding: str = "utf-8"
    language: str = "en"
    language_confidence: float = 1.0
    document_metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[DocumentSection] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    structured_data: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
    parsing_warnings: List[str] = field(default_factory=list)
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "sha256": self.sha256,
            "format": self.format,
            "detected_mime": self.detected_mime,
            "encoding": self.encoding,
            "language": self.language,
            "language_confidence": self.language_confidence,
            "document_metadata": self.document_metadata,
            "sections": [s.to_dict() for s in self.sections],
            "paragraphs": self.paragraphs,
            "tables": [t.to_dict() for t in self.tables],
            "structured_data": self.structured_data,
            "raw_text_length": len(self.raw_text),
            "parsing_warnings": self.parsing_warnings,
            "ingested_at": self.ingested_at,
        }


@dataclass
class Fact:
    fact_id: str
    category: str  # e.g., 'diet', 'habitat', 'population', 'morphology', 'conservation', 'reproduction', 'behavior'
    predicate: str  # e.g., 'type', 'food_items', 'canopy_level', 'status', 'gestation_period'
    value: Any
    sources: List[str] = field(default_factory=list)  # list of source_ids
    provenance: List[SourceProvenance] = field(default_factory=list)
    confidence: float = 0.95
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "category": self.category,
            "predicate": self.predicate,
            "value": self.value,
            "sources": list(sorted(set(self.sources))),
            "provenance": [p.to_dict() if hasattr(p, "to_dict") else p for p in self.provenance],
            "confidence": round(self.confidence, 4),
            "metadata": self.metadata,
        }


@dataclass
class Observation:
    observation_id: str
    location: Optional[str] = None
    park_name: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None  # {"lat": ..., "lon": ...}
    year: Optional[int] = None
    date: Optional[str] = None
    count: Optional[Union[int, float]] = None
    count_type: Optional[str] = None  # 'individuals', 'nests', 'groups', 'dung', 'footprints'
    method: Optional[str] = None  # 'transect', 'camera_trap', 'direct_sighting', 'acoustic', etc.
    observers: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    source_id: str = ""
    provenance: Optional[SourceProvenance] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.provenance:
            res["provenance"] = self.provenance.to_dict() if hasattr(self.provenance, "to_dict") else self.provenance
        return res


@dataclass
class Conflict:
    conflict_id: str
    species_id: str
    field: str
    values: List[Dict[str, Any]] = field(default_factory=list)  # [{"value": ..., "source_id": ..., "context": ...}]
    status: str = "requires_review"  # 'requires_review', 'resolved', 'contextual_variation'
    resolution_notes: Optional[str] = None
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChangeLogEntry:
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    species_id: str = ""
    action: str = ""  # 'species_created', 'fact_added', 'fact_updated', 'sources_merged', 'observation_added', 'conflict_detected'
    field: str = ""
    old_value: Any = None
    new_value: Any = None
    source_id: str = ""
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SpeciesRecord:
    species_id: str
    scientific_name: str
    normalized_name: str
    category: str
    taxonomy: Dict[str, str] = field(default_factory=dict)  # kingdom, phylum, class, order, family, genus
    synonyms: List[str] = field(default_factory=list)
    common_names: Dict[str, List[str]] = field(default_factory=lambda: {"en": [], "fr": []})
    iucn_status: Optional[str] = None
    facts: Dict[str, Any] = field(default_factory=dict)  # organized by category/predicate
    observations: List[Observation] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "species_id": self.species_id,
            "scientific_name": self.scientific_name,
            "normalized_name": self.normalized_name,
            "category": self.category,
            "taxonomy": self.taxonomy,
            "synonyms": list(sorted(set(self.synonyms))),
            "common_names": {k: list(sorted(set(v))) for k, v in self.common_names.items()},
            "iucn_status": self.iucn_status,
            "facts": self.facts,
            "observations": [obs.to_dict() if hasattr(obs, "to_dict") else obs for obs in self.observations],
            "sources": list(sorted(set(self.sources))),
            "conflicts": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.conflicts],
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
