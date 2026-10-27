"""Intelligent incremental merge engine performing multi-level deduplication, granularity enhancement, and conflict detection."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models import (
    SpeciesRecord,
    Fact,
    Observation,
    Conflict,
    ChangeLogEntry,
    SourceProvenance,
)


class MergeResult:
    def __init__(self, species_id: str, is_new: bool = False):
        self.species_id = species_id
        self.is_new = is_new
        self.new_facts_count = 0
        self.duplicate_facts_count = 0
        self.merged_sources_count = 0
        self.new_observations_count = 0
        self.conflicts_detected: List[Conflict] = []
        self.changes: List[ChangeLogEntry] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "species_id": self.species_id,
            "is_new": self.is_new,
            "new_facts": self.new_facts_count,
            "duplicate_facts": self.duplicate_facts_count,
            "merged_sources": self.merged_sources_count,
            "new_observations": self.new_observations_count,
            "conflicts": [c.to_dict() for c in self.conflicts_detected],
            "changes_count": len(self.changes),
        }


class IntelligentMergeEngine:
    """Incremental merge engine for species facts, observations, and conflict detection."""

    def __init__(self, change_log_file: Optional[str | Path] = None):
        self.change_log_file = Path(change_log_file) if change_log_file else None
        self._conflict_counter = 1

    def _next_conflict_id(self) -> str:
        cid = f"CONFLICT-{self._conflict_counter:04d}"
        self._conflict_counter += 1
        return cid

    def _log_change(self, record: SpeciesRecord, action: str, field: str, old_val: Any, new_val: Any, source_id: str, result: MergeResult) -> None:
        entry = ChangeLogEntry(
            species_id=record.species_id,
            action=action,
            field=field,
            old_value=deepcopy(old_val),
            new_value=deepcopy(new_val),
            source_id=source_id,
        )
        result.changes.append(entry)

        if self.change_log_file:
            self.change_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.change_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def _is_more_specific(self, general: str, specific: str) -> bool:
        """Returns True if 'specific' provides more precise terminology than 'general'."""
        g = general.lower().strip()
        s = specific.lower().strip()
        if g == s:
            return False
        # Specific contains the general string (e.g. 'forêt' in 'forêt tropicale humide')
        if g in s:
            return True
        if "forest" in g and ("lowland" in s or "rainforest" in s or "primary" in s or "moist" in s):
            return True
        return False

    def merge_fact_into_record(
        self,
        record: SpeciesRecord,
        new_fact: Fact,
        source_id: str,
        result: MergeResult,
    ) -> None:
        """Intelligently merges a scientific fact into the existing record."""
        cat = new_fact.category
        pred = new_fact.predicate

        if cat not in record.facts:
            record.facts[cat] = {}

        # If predicate does not exist yet -> simply add
        if pred not in record.facts[cat]:
            record.facts[cat][pred] = new_fact.to_dict()
            record.sources = list(sorted(set(record.sources + [source_id])))
            result.new_facts_count += 1
            self._log_change(record, "fact_added", f"{cat}.{pred}", None, new_fact.value, source_id, result)
            return

        existing_fact_dict = record.facts[cat][pred]
        existing_val = existing_fact_dict.get("value")
        new_val = new_fact.value

        # CASE 1: List-based facts (e.g., diet.food_items, diet.type) -> union of unique items
        if isinstance(existing_val, list) and isinstance(new_val, list):
            existing_set = set(str(x).lower() for x in existing_val)
            new_unique = [item for item in new_val if str(item).lower() not in existing_set]

            if not new_unique:
                # Exact duplicates: merge sources and boost consensus confidence
                if source_id not in existing_fact_dict["sources"]:
                    existing_fact_dict["sources"].append(source_id)
                    existing_fact_dict["sources"].sort()
                    existing_fact_dict["confidence"] = min(0.99, existing_fact_dict.get("confidence", 0.9) + 0.03)
                    result.duplicate_facts_count += 1
                    result.merged_sources_count += 1
                    self._log_change(record, "sources_merged", f"{cat}.{pred}", existing_fact_dict["sources"][:-1], existing_fact_dict["sources"], source_id, result)
                return

            # Enrich list with new unique items
            merged_list = list(existing_val) + new_unique
            old_copy = list(existing_val)
            existing_fact_dict["value"] = merged_list
            if source_id not in existing_fact_dict["sources"]:
                existing_fact_dict["sources"].append(source_id)
                existing_fact_dict["sources"].sort()

            result.new_facts_count += 1
            self._log_change(record, "fact_enriched", f"{cat}.{pred}", old_copy, merged_list, source_id, result)
            return

        # CASE 2: String values (e.g., habitat.type, status)
        if isinstance(existing_val, str) and isinstance(new_val, str):
            if existing_val.lower().strip() == new_val.lower().strip():
                # Identical string fact: merge sources
                if source_id not in existing_fact_dict["sources"]:
                    existing_fact_dict["sources"].append(source_id)
                    existing_fact_dict["sources"].sort()
                    existing_fact_dict["confidence"] = min(0.99, existing_fact_dict.get("confidence", 0.9) + 0.03)
                    result.duplicate_facts_count += 1
                    result.merged_sources_count += 1
                    self._log_change(record, "sources_merged", f"{cat}.{pred}", existing_fact_dict["sources"][:-1], existing_fact_dict["sources"], source_id, result)
                return

            # Check if new value is more specific / precise
            if self._is_more_specific(existing_val, new_val):
                old_v = existing_val
                existing_fact_dict["value"] = new_val
                existing_fact_dict["sources"].append(source_id)
                existing_fact_dict["sources"] = list(sorted(set(existing_fact_dict["sources"])))
                result.new_facts_count += 1
                self._log_change(record, "fact_refined", f"{cat}.{pred}", old_v, new_val, source_id, result)
                return

            # If existing value is more specific than new general mention -> keep existing, just attach source
            if self._is_more_specific(new_val, existing_val):
                if source_id not in existing_fact_dict["sources"]:
                    existing_fact_dict["sources"].append(source_id)
                    existing_fact_dict["sources"].sort()
                    result.merged_sources_count += 1
                return

            # Potential Conflict / Divergence
            conflict = Conflict(
                conflict_id=self._next_conflict_id(),
                species_id=record.species_id,
                field=f"{cat}.{pred}",
                values=[
                    {"value": existing_val, "sources": existing_fact_dict["sources"]},
                    {"value": new_val, "sources": [source_id]},
                ],
                status="requires_review",
            )
            record.conflicts.append(conflict)
            result.conflicts_detected.append(conflict)
            self._log_change(record, "conflict_detected", f"{cat}.{pred}", existing_val, new_val, source_id, result)
            return

        # CASE 3: Numeric / Dictionary values
        if existing_val == new_val:
            if source_id not in existing_fact_dict["sources"]:
                existing_fact_dict["sources"].append(source_id)
                existing_fact_dict["sources"].sort()
                result.duplicate_facts_count += 1
                result.merged_sources_count += 1
            return

        # Numeric divergence
        conflict = Conflict(
            conflict_id=self._next_conflict_id(),
            species_id=record.species_id,
            field=f"{cat}.{pred}",
            values=[
                {"value": existing_val, "sources": existing_fact_dict["sources"]},
                {"value": new_val, "sources": [source_id]},
            ],
            status="requires_review",
        )
        record.conflicts.append(conflict)
        result.conflicts_detected.append(conflict)
        self._log_change(record, "conflict_detected", f"{cat}.{pred}", existing_val, new_val, source_id, result)

    def merge_observation_into_record(
        self,
        record: SpeciesRecord,
        new_obs: Observation,
        result: MergeResult,
    ) -> None:
        """Deduplicates and appends distinct field observations."""
        # Check if an observation with identical year, location, and count already exists
        for existing in record.observations:
            same_loc = (existing.location or "").lower() == (new_obs.location or "").lower()
            same_year = existing.year == new_obs.year
            same_count = existing.count == new_obs.count
            same_src = existing.source_id == new_obs.source_id

            if same_loc and same_year and same_count and same_src:
                # Exact identical duplicate observation
                return

        record.observations.append(new_obs)
        if new_obs.source_id and new_obs.source_id not in record.sources:
            record.sources.append(new_obs.source_id)
            record.sources.sort()
        result.new_observations_count += 1
        self._log_change(
            record,
            "observation_added",
            "observations",
            None,
            f"{new_obs.location} ({new_obs.year}): {new_obs.count}",
            new_obs.source_id,
            result,
        )

    def merge_species_data(
        self,
        existing_record: Optional[SpeciesRecord],
        species_id: str,
        scientific_name: str,
        normalized_name: str,
        category: str,
        taxonomy: Dict[str, str],
        synonyms: List[str],
        common_names: Dict[str, List[str]],
        iucn_status: Optional[str],
        facts: List[Fact],
        observations: List[Observation],
        source_id: str,
    ) -> Tuple[SpeciesRecord, MergeResult]:
        """Performs incremental merge of a species entity, updating version and changelog."""
        if existing_record is None:
            # BRAND NEW SPECIES
            result = MergeResult(species_id=species_id, is_new=True)
            record = SpeciesRecord(
                species_id=species_id,
                scientific_name=scientific_name,
                normalized_name=normalized_name,
                category=category,
                taxonomy=taxonomy,
                synonyms=synonyms,
                common_names=common_names,
                iucn_status=iucn_status,
                sources=[source_id] if source_id else [],
                version=1,
            )
            self._log_change(record, "species_created", "entity", None, scientific_name, source_id, result)

            for f in facts:
                self.merge_fact_into_record(record, f, source_id, result)
            for obs in observations:
                self.merge_observation_into_record(record, obs, result)

            return record, result

        # EXISTING SPECIES: INCREMENTAL ENRICHMENT
        result = MergeResult(species_id=species_id, is_new=False)
        record = existing_record

        # Update taxonomy & synonyms if new ones discovered
        if not record.iucn_status and iucn_status:
            record.iucn_status = iucn_status
        for syn in synonyms:
            if syn not in record.synonyms:
                record.synonyms.append(syn)
        for lang, names in common_names.items():
            record.common_names.setdefault(lang, [])
            for n in names:
                if n not in record.common_names[lang]:
                    record.common_names[lang].append(n)

        # Merge facts
        for f in facts:
            self.merge_fact_into_record(record, f, source_id, result)

        # Merge observations
        for obs in observations:
            self.merge_observation_into_record(record, obs, result)

        if source_id and source_id not in record.sources:
            record.sources.append(source_id)
            record.sources.sort()

        if result.new_facts_count > 0 or result.new_observations_count > 0:
            record.version += 1
            record.updated_at = datetime.now(timezone.utc).isoformat()

        return record, result
