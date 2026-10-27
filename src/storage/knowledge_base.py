"""Storage manager ensuring synchronized output generation for species files, RAG datasets, and validation reports."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from src.models import SpeciesRecord, Conflict, ChangeLogEntry, Observation


class KnowledgeBaseStorage:
    """Manages the structured file system and derived output synchronization."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.species_dir = self.base_dir / "species"
        self.metadata_dir = self.base_dir / "metadata"
        self.species_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def load_all_species(self) -> Dict[str, SpeciesRecord]:
        """Loads all existing species JSON files from the species/ directory."""
        records: Dict[str, SpeciesRecord] = {}
        for json_file in self.species_dir.glob("*/*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sid = data["species_id"]

                    # Reconstruct Observation objects
                    raw_obs = data.get("observations", [])
                    obs_objs = []
                    for o in raw_obs:
                        if isinstance(o, dict):
                            obs_objs.append(Observation(
                                observation_id=o.get("observation_id", ""),
                                location=o.get("location"),
                                park_name=o.get("park_name"),
                                coordinates=o.get("coordinates"),
                                year=o.get("year"),
                                date=o.get("date"),
                                count=o.get("count"),
                                count_type=o.get("count_type"),
                                method=o.get("method"),
                                observers=o.get("observers", []),
                                notes=o.get("notes"),
                                source_id=o.get("source_id", ""),
                                metadata=o.get("metadata", {}),
                            ))
                        else:
                            obs_objs.append(o)

                    # Reconstruct Conflict objects
                    raw_conflicts = data.get("conflicts", [])
                    conf_objs = []
                    for c in raw_conflicts:
                        if isinstance(c, dict):
                            conf_objs.append(Conflict(
                                conflict_id=c.get("conflict_id", ""),
                                species_id=c.get("species_id", sid),
                                field=c.get("field", ""),
                                values=c.get("values", []),
                                status=c.get("status", "requires_review"),
                                resolution_notes=c.get("resolution_notes"),
                                detected_at=c.get("detected_at", ""),
                            ))
                        else:
                            conf_objs.append(c)

                    rec = SpeciesRecord(
                        species_id=sid,
                        scientific_name=data["scientific_name"],
                        normalized_name=data["normalized_name"],
                        category=data.get("category", "unclassified"),
                        taxonomy=data.get("taxonomy", {}),
                        synonyms=data.get("synonyms", []),
                        common_names=data.get("common_names", {"en": [], "fr": []}),
                        iucn_status=data.get("iucn_status"),
                        facts=data.get("facts", {}),
                        observations=obs_objs,
                        sources=data.get("sources", []),
                        conflicts=conf_objs,
                        version=data.get("version", 1),
                        created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
                        updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                    )
                    records[sid] = rec
            except Exception as e:
                print(f"Warning loading species file {json_file}: {e}")

        return records

    def save_species(self, record: SpeciesRecord) -> Path:
        """Saves or updates individual species JSON in its category subfolder."""
        category_dir = self.species_dir / record.category
        category_dir.mkdir(parents=True, exist_ok=True)

        target_file = category_dir / f"{record.normalized_name}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2, ensure_ascii=False)

        return target_file

    def save_legal_record(self, record: Any) -> Path:
        """Saves a legal document JSON in the legal/ folder."""
        legal_dir = self.base_dir / "legal"
        legal_dir.mkdir(parents=True, exist_ok=True)
        rec_dict = record.to_dict() if hasattr(record, "to_dict") else record
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", rec_dict.get("doc_id", "law").lower())
        target_file = legal_dir / f"{slug}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(rec_dict, f, indent=2, ensure_ascii=False)
        return target_file

    def load_all_laws(self) -> Dict[str, Any]:
        """Loads all existing legal JSON files from legal/."""
        laws = {}
        legal_dir = self.base_dir / "legal"
        if not legal_dir.exists():
            return laws
        for json_file in legal_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    did = data.get("doc_id", json_file.stem)
                    laws[did] = data
            except Exception:
                pass
        return laws

    def synchronize_all_outputs(
        self,
        species_records: Dict[str, SpeciesRecord],
        conflicts: List[Conflict],
        legal_records: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Path]:
        """Regenerates all_species.json, all_facts.json, all_laws.json, species_documents.jsonl, and metadata files."""
        legal_records = legal_records or {}
        output_paths: Dict[str, Path] = {}

        # 1. Save all individual species JSONs
        for rec in species_records.values():
            self.save_species(rec)

        # 2. all_species.json
        all_species_file = self.base_dir / "all_species.json"
        all_sp_data = {
            "total_species": len(species_records),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "species": [rec.to_dict() for rec in species_records.values()],
        }
        with open(all_species_file, "w", encoding="utf-8") as f:
            json.dump(all_sp_data, f, indent=2, ensure_ascii=False)
        output_paths["all_species"] = all_species_file

        # 3. all_facts.json
        all_facts_file = self.base_dir / "all_facts.json"
        all_facts_list: List[Dict[str, Any]] = []
        for rec in species_records.values():
            for cat_name, preds in rec.facts.items():
                for pred_name, fact_dict in preds.items():
                    all_facts_list.append({
                        "species_id": rec.species_id,
                        "scientific_name": rec.scientific_name,
                        "category": cat_name,
                        "predicate": pred_name,
                        **fact_dict,
                    })

        with open(all_facts_file, "w", encoding="utf-8") as f:
            json.dump({
                "total_facts": len(all_facts_list),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "facts": all_facts_list,
            }, f, indent=2, ensure_ascii=False)
        output_paths["all_facts"] = all_facts_file

        # 4. species_documents.jsonl for AI / RAG datasets
        rag_file = self.base_dir / "species_documents.jsonl"
        with open(rag_file, "w", encoding="utf-8") as f:
            for rec in species_records.values():
                # Construct clean textual summary for RAG indexing
                common_fr = ", ".join(rec.common_names.get("fr", []))
                common_en = ", ".join(rec.common_names.get("en", []))
                tax_info = f"Class: {rec.taxonomy.get('class', '')}, Order: {rec.taxonomy.get('order', '')}, Family: {rec.taxonomy.get('family', '')}"

                facts_summary = []
                for cat_name, preds in rec.facts.items():
                    for pred_name, f_dict in preds.items():
                        facts_summary.append(f"{cat_name.capitalize()} ({pred_name}): {f_dict.get('value')} (Sources: {', '.join(f_dict.get('sources', []))})")

                obs_summary = []
                for obs in rec.observations:
                    loc = obs.location if hasattr(obs, "location") else obs.get("location")
                    yr = obs.year if hasattr(obs, "year") else obs.get("year")
                    cnt = obs.count if hasattr(obs, "count") else obs.get("count")
                    meth = obs.method if hasattr(obs, "method") else obs.get("method")
                    obs_summary.append(f"- Location: {loc or 'Gabon'}, Year: {yr or 'N/A'}, Count: {cnt or 'N/A'}, Method: {meth or 'N/A'}")

                rag_doc = {
                    "id": rec.species_id,
                    "title": f"{rec.scientific_name} - Gabon Biodiversity Profile",
                    "scientific_name": rec.scientific_name,
                    "normalized_name": rec.normalized_name,
                    "category": rec.category,
                    "common_names_fr": common_fr,
                    "common_names_en": common_en,
                    "iucn_status": rec.iucn_status,
                    "taxonomy": tax_info,
                    "facts": facts_summary,
                    "observations_count": len(rec.observations),
                    "observations": obs_summary[:20],
                    "sources": rec.sources,
                    "text": (
                        f"Species: {rec.scientific_name}\n"
                        f"French Names: {common_fr}\n"
                        f"English Names: {common_en}\n"
                        f"Taxonomy: {tax_info}\n"
                        f"IUCN Status: {rec.iucn_status or 'Not Evaluated'}\n\n"
                        f"Scientific Facts:\n" + "\n".join(facts_summary) + "\n\n"
                        f"Field Observations in Gabon:\n" + "\n".join(obs_summary)
                    ),
                    "metadata": {
                        "species_id": rec.species_id,
                        "version": rec.version,
                        "sources_count": len(rec.sources),
                        "updated_at": rec.updated_at,
                    }
                }
                f.write(json.dumps(rag_doc, ensure_ascii=False) + "\n")
        output_paths["species_documents_jsonl"] = rag_file

        # 5. all_laws.json and legal documents
        all_laws_file = self.base_dir / "all_laws.json"
        legal_list = [l.to_dict() if hasattr(l, "to_dict") else l for l in legal_records.values()]
        with open(all_laws_file, "w", encoding="utf-8") as f:
            json.dump({
                "total_laws": len(legal_list),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "laws": legal_list,
            }, f, indent=2, ensure_ascii=False)
        output_paths["all_laws"] = all_laws_file

        # Append legal documents to species_documents.jsonl for complete environmental RAG
        for l_rec in legal_records.values():
            l_dict = l_rec.to_dict() if hasattr(l_rec, "to_dict") else l_rec
            art_texts = [f"Article {a.get('article_number')}: {a.get('content')}" for a in l_dict.get("articles", [])]
            legal_rag_doc = {
                "id": l_dict.get("doc_id"),
                "title": f"{l_dict.get('law_number') or 'Texte Juridique'} - {l_dict.get('title')}",
                "doc_type": "legal_framework",
                "law_number": l_dict.get("law_number"),
                "articles_count": len(l_dict.get("articles", [])),
                "general_sanctions": l_dict.get("general_sanctions", []),
                "text": (
                    f"Document Juridique: {l_dict.get('title')}\n"
                    f"Référence: {l_dict.get('law_number') or 'N/A'}\n"
                    f"Type: {l_dict.get('doc_type')}\n"
                    f"Sanctions Principales: {', '.join(l_dict.get('general_sanctions', [])[:10])}\n\n"
                    f"Articles:\n" + "\n\n".join(art_texts[:50])
                ),
                "metadata": {
                    "doc_id": l_dict.get("doc_id"),
                    "source_id": l_dict.get("source_id"),
                }
            }
            with open(rag_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(legal_rag_doc, ensure_ascii=False) + "\n")

        # 6. metadata/conflicts.json
        conflicts_file = self.metadata_dir / "conflicts.json"
        with open(conflicts_file, "w", encoding="utf-8") as f:
            json.dump({
                "total_conflicts": len(conflicts),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "conflicts": [c.to_dict() if hasattr(c, "to_dict") else c for c in conflicts],
            }, f, indent=2, ensure_ascii=False)
        output_paths["conflicts"] = conflicts_file

        return output_paths

    def generate_validation_report(
        self,
        summary_stats: Dict[str, Any],
        conflicts: List[Conflict],
        review_required_files: List[Dict[str, Any]],
    ) -> Tuple[Path, Path]:
        """Creates validation_report.json and human-readable validation_report.md."""
        rep_json = self.base_dir / "validation_report.json"
        rep_md = self.base_dir / "validation_report.md"

        report_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary_stats,
            "conflicts_count": len(conflicts),
            "conflicts": [c.to_dict() if hasattr(c, "to_dict") else c for c in conflicts],
            "review_required_files": review_required_files,
        }

        with open(rep_json, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        # Markdown report
        md_content = f"""# Gabon Biodiversity Pipeline - Validation Report

**Generated at**: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`

## 📊 Summary Statistics

| Metric | Count |
|---|---|
| New Resources Processed | {summary_stats.get('new_resources', 0)} |
| Already Known Resources (Skipped) | {summary_stats.get('already_known_resources', 0)} |
| Total Species in Database | {summary_stats.get('total_species', 0)} |
| New Species Created | {summary_stats.get('new_species', 0)} |
| Existing Species Enriched | {summary_stats.get('updated_species', 0)} |
| New Scientific Facts | {summary_stats.get('new_facts', 0)} |
| Duplicate / Confirmed Facts | {summary_stats.get('duplicate_facts', 0)} |
| Field Observations Recorded | {summary_stats.get('new_observations', 0)} |
| Potential Conflicts Flagged | {len(conflicts)} |
| Files Requiring Human Review | {len(review_required_files)} |

## ⚠️ Conflicts Requiring Human Review ({len(conflicts)})

"""
        if conflicts:
            for c in conflicts:
                c_dict = c.to_dict() if hasattr(c, "to_dict") else c
                md_content += f"- **[{c_dict.get('conflict_id')}]** Species `{c_dict.get('species_id')}` - Field `{c_dict.get('field')}`\n"
                for v in c_dict.get("values", []):
                    md_content += f"  - Value: `{v.get('value')}` (Sources: {', '.join(v.get('sources', []))})\n"
        else:
            md_content += "_No active scientific contradictions detected._\n"

        if review_required_files:
            md_content += f"\n## 📁 Files Requiring Review ({len(review_required_files)})\n\n"
            for rf in review_required_files:
                md_content += f"- `{rf.get('file')}`: {rf.get('reason')}\n"

        with open(rep_md, "w", encoding="utf-8") as f:
            f.write(md_content)

        return rep_json, rep_md
