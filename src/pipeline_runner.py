"""Main orchestration pipeline for intelligent, incremental, multi-format biodiversity processing."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models import (
    InternalDocument,
    SpeciesRecord,
    Fact,
    Observation,
    Conflict,
    ChangeLogEntry,
)
from src.format_detector import FormatDetector, compute_file_sha256
from src.parsers.parser_registry import default_registry, ParserRegistry
from src.species_detector import SpeciesDetector
from src.registries import SourceRegistry, EntityRegistry, normalize_species_name
from src.information_extraction import InformationExtractor
from src.merging import IntelligentMergeEngine, MergeResult
from src.legal import LegalExtractor, LegalDocumentRecord
from src.storage import KnowledgeBaseStorage
from src.general_knowledge import KnowledgeBuilder
from src.general_knowledge.training_generator import CountryTrainingDatasetGenerator


class BiodiversityPipeline:
    """End-to-end incremental and cumulative pipeline for Gabon biodiversity and general-knowledge base."""

    def __init__(
        self,
        output_dir: str | Path = ".",
        parser_registry: Optional[ParserRegistry] = None,
        country: str = "Gabon",
    ):
        self.output_dir = Path(output_dir).resolve()
        self.metadata_dir = self.output_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.country = country

        self.storage = KnowledgeBaseStorage(self.output_dir)
        self.parser_registry = parser_registry or default_registry
        self.species_detector = SpeciesDetector()
        self.info_extractor = InformationExtractor()
        self.legal_extractor = LegalExtractor()
        self.knowledge_builder = KnowledgeBuilder(self.output_dir, default_country=self.country)
        self.history_dir = self.output_dir / "Histoire"
        from src.general_knowledge.wiki_crawler import WikipediaHistoryCrawler
        self.wiki_crawler = WikipediaHistoryCrawler(output_dir=self.history_dir)

        # Registries
        self.source_registry = SourceRegistry(self.metadata_dir / "source_registry.json")
        self.entity_registry = EntityRegistry(self.metadata_dir / "entity_registry.json")
        self.merge_engine = IntelligentMergeEngine(self.metadata_dir / "change_log.jsonl")

        # In-memory working database
        self.species_records: Dict[str, SpeciesRecord] = self.storage.load_all_species()
        self.legal_records: Dict[str, Any] = self.storage.load_all_laws()
        self.all_conflicts: List[Conflict] = []
        self.review_required_files: List[Dict[str, Any]] = []

    def reset_database(self) -> None:
        """Clears all stored species, metadata, legal records, and knowledge/ to restart with a clean slate."""
        import shutil
        print("[RESET] Clearing species/, metadata/, legal/, knowledge/, and datasets/ folders...")
        for folder_name in ["species", "metadata", "legal", "knowledge", "datasets"]:
            p = self.output_dir / folder_name
            if p.exists():
                shutil.rmtree(p)
                p.mkdir(parents=True, exist_ok=True)

        for top_file in ["all_species.json", "all_facts.json", "all_laws.json", "species_documents.jsonl", "validation_report.json", "validation_report.md"]:
            tf = self.output_dir / top_file
            if tf.exists():
                tf.unlink()

        self.source_registry = SourceRegistry(self.metadata_dir / "source_registry.json")
        self.entity_registry = EntityRegistry(self.metadata_dir / "entity_registry.json")
        self.knowledge_builder = KnowledgeBuilder(self.output_dir, default_country=self.country)
        self.merge_engine = IntelligentMergeEngine(self.metadata_dir / "change_log.jsonl")
        self.species_records = {}
        self.legal_records = {}
        self.all_conflicts = []
        self.review_required_files = []
        print("[RESET] Database has been completely reset.")

    def run(
        self,
        input_dir: str | Path,
        dry_run: bool = False,
        force: bool = False,
        skip_wiki: bool = False,
    ) -> Dict[str, Any]:
        input_path = Path(input_dir).resolve()
        if not input_path.exists():
            print(f"Error: input directory does not exist: {input_path}")
            return {"status": "error", "message": "Input directory not found"}

        # 0. Wikipedia History Crawler & Cross-references acquisition
        if not skip_wiki:
            if not dry_run:
                print("[PHASE 0] Acquisition des pages Wikipédia Histoire du Gabon & Cross-references...")
                self.wiki_crawler.crawl_and_download()
            else:
                print("[PHASE 0 - DRY RUN] Inventaire des documents d'Histoire Wikipédia :")
                self.wiki_crawler.list_existing_history_documents()
        else:
            print("[PHASE 0] Étape Wikipédia sautée (--skip-wiki activé).")
            self.wiki_crawler.list_existing_history_documents()

        # Collect all files recursively from input_dir and from Histoire/pdf
        all_candidate_files: List[Path] = []
        for root, dirs, files in os.walk(input_path):
            dirs[:] = [d for d in dirs if not d.startswith((".", "_")) and d not in ("metadata", "species", "legal", "scratch", ".gemini")]
            for f in files:
                if not f.startswith((".", "_")) and not f.endswith((".pyc", ".git")):
                    all_candidate_files.append(Path(root) / f)

        # Include history PDFs if Histoire/pdf exists and is outside input_path
        history_pdf_dir = self.history_dir / "pdf"
        if history_pdf_dir.exists():
            for f in history_pdf_dir.glob("*.pdf"):
                if f not in all_candidate_files and not any(f.samefile(c) for c in all_candidate_files if c.exists()):
                    all_candidate_files.append(f)

        summary_stats = {
            "total_files_scanned": len(all_candidate_files),
            "new_resources": 0,
            "already_known_resources": 0,
            "new_species": 0,
            "updated_species": 0,
            "new_facts": 0,
            "duplicate_facts": 0,
            "new_observations": 0,
            "conflicts_count": 0,
            "total_species": len(self.species_records),
            "output_files_added": 0,
            "output_files_updated": 0,
        }

        prospective_species_updates: Dict[str, Dict[str, Any]] = {}
        prospective_new_species: List[str] = []

        print(f"\n========================================")
        print(f"GABON BIODIVERSITY PIPELINE ({'DRY-RUN' if dry_run else 'EXECUTION'})")
        print(f"Input Directory: {input_path}")
        print(f"Total Files Found: {len(all_candidate_files)}")
        if force:
            print("Force Reprocessing: ENABLED")
        print(f"========================================\n")

        total_files = len(all_candidate_files)
        for idx, file_p in enumerate(all_candidate_files, 1):
            # 1. Compute SHA-256 for idempotence check
            try:
                sha256 = compute_file_sha256(file_p)
            except Exception as e:
                print(f"[{idx}/{total_files}] ERROR reading {file_p.name}: {e}")
                self.review_required_files.append({"file": str(file_p), "reason": f"File read error: {e}"})
                continue

            # 2. Check source registry (unless force is True)
            if not force and self.source_registry.is_known_hash(sha256):
                summary_stats["already_known_resources"] += 1
                print(f"[{idx}/{total_files}] SKIP (Already processed): {file_p.name}")
                continue

            # 3. Format detection & Parsing
            summary_stats["new_resources"] += 1
            source_id = self.source_registry.allocate_source_id() if not dry_run else f"SRC-DRY-{summary_stats['new_resources']:03d}"

            try:
                doc = self.parser_registry.parse_file(file_p, source_id=source_id)
            except Exception as e:
                print(f"[{idx}/{total_files}] ERROR parsing {file_p.name}: {e}")
                self.review_required_files.append({"file": str(file_p), "reason": f"Parsing exception: {e}"})
                continue

            if doc.format in ("unsupported", "unknown_binary") and not doc.raw_text:
                print(f"[{idx}/{total_files}] WARN (Unsupported binary): {file_p.name}")
                self.review_required_files.append({"file": str(file_p), "reason": "Unsupported binary or unreadable content"})
                continue

            # 4. Process in general-knowledge builder (country-centric, multi-category)
            try:
                rel_p = str(file_p.relative_to(input_path))
            except Exception:
                rel_p = file_p.name
            kb_res = self.knowledge_builder.process(doc, file_p, rel_p, sha256, dry_run=dry_run)

            # 5. Check for Legal / Regulatory Texts (legacy legal folder)
            is_legal = self.legal_extractor.is_legal_document(doc)
            if is_legal:
                try:
                    legal_rec = self.legal_extractor.extract_legal_document(doc, doc_counter=len(self.legal_records) + 1)
                    if not dry_run:
                        self.legal_records[legal_rec.doc_id] = legal_rec
                        self.storage.save_legal_record(legal_rec)
                    summary_stats["legal_documents_processed"] = summary_stats.get("legal_documents_processed", 0) + 1
                except Exception as e:
                    self.review_required_files.append({"file": str(file_p), "reason": f"Legal extraction exception: {e}"})

            # 6. Domain segregation prior to Species Detection
            doc_category = kb_res.get("category", "")
            secondary_cats = kb_res.get("secondary_categories", [])
            rel_p_lower = rel_p.lower()

            # Determine whether the document belongs to biodiversity/ecology domain
            has_biological_table = False
            for tab in doc.tables:
                col_lower = [str(c).lower().strip() if c is not None else "" for c in tab.columns]
                if any(c in ("genus", "genre") for c in col_lower) and any(c in ("species", "espèce", "espece", "species_name") for c in col_lower):
                    has_biological_table = True
                    break
                if any(c in ("scientific_name", "nom_scientifique", "taxon") for c in col_lower):
                    has_biological_table = True
                    break

            is_biodiversity = (
                not is_legal
                and (
                    doc_category in ("biodiversite", "environnement")
                    or "biodiversite" in secondary_cats
                    or any(kw in rel_p_lower for kw in ("biodivers", "amphibi", "mammif", "soundscape", "faune", "flore", "fauna", "flora", "foret", "forêt", "forest"))
                    or has_biological_table
                )
            )

            # Only allow free-text binomial extraction for biodiversity documents
            species_mentions = self.species_detector.detect_in_document(doc, allow_freetext=is_biodiversity)
            file_species_count = len(species_mentions)

            cat_info = f" | Cat: {kb_res.get('category')}" if kb_res.get('category') else ""
            print(f"[{idx}/{total_files}] {'DRY-RUN' if dry_run else 'PROCESSED'}: {file_p.name} -> Format: {doc.format} | Species: {file_species_count}{' | Legal' if is_legal else ''}{cat_info}")

            # 7. Entity Resolution, Extraction, and Merging for each species
            for canonical_name, mentions in species_mentions.items():
                # Extract taxonomy clues from document context
                tax_clues = self.info_extractor.extract_taxonomy_clues(doc, species_name=canonical_name)

                species_id, is_new = self.entity_registry.resolve_or_create(
                    scientific_name=canonical_name,
                    class_name=tax_clues.get("class_name"),
                    order_name=tax_clues.get("order_name"),
                    family_name=tax_clues.get("family_name"),
                    synonyms=tax_clues.get("synonyms"),
                    common_names=tax_clues.get("common_names"),
                    iucn_status=tax_clues.get("iucn_status"),
                )

                if not is_new:
                    self.entity_registry.update_taxonomy_if_better(
                        species_id=species_id,
                        class_name=tax_clues.get("class_name"),
                        order_name=tax_clues.get("order_name"),
                        family_name=tax_clues.get("family_name"),
                        iucn_status=tax_clues.get("iucn_status"),
                    )

                ent_record = self.entity_registry.get_species_record(species_id) or {}
                norm_name = ent_record.get("normalized_name", normalize_species_name(canonical_name))
                category = ent_record.get("category", "unclassified")
                taxonomy = ent_record.get("taxonomy", {})
                synonyms = ent_record.get("synonyms", [])
                common_names = ent_record.get("common_names", {"en": [], "fr": []})
                iucn_status = ent_record.get("iucn_status")

                # Extract facts & observations
                facts, observations = self.info_extractor.extract_from_document(doc, species_name=canonical_name)

                if dry_run:
                    if is_new:
                        if canonical_name not in prospective_new_species:
                            prospective_new_species.append(canonical_name)
                            summary_stats["new_species"] += 1
                    else:
                        info = prospective_species_updates.setdefault(canonical_name, {"facts": 0, "obs": 0})
                        info["facts"] += len(facts)
                        info["obs"] += len(observations)
                    summary_stats["new_facts"] += len(facts)
                    summary_stats["new_observations"] += len(observations)
                else:
                    existing_sp = self.species_records.get(species_id)
                    merged_record, merge_res = self.merge_engine.merge_species_data(
                        existing_record=existing_sp,
                        species_id=species_id,
                        scientific_name=canonical_name,
                        normalized_name=norm_name,
                        category=category,
                        taxonomy=taxonomy,
                        synonyms=synonyms,
                        common_names=common_names,
                        iucn_status=iucn_status,
                        facts=facts,
                        observations=observations,
                        source_id=source_id,
                    )

                    self.species_records[species_id] = merged_record
                    if merge_res.is_new:
                        summary_stats["new_species"] += 1
                        summary_stats["output_files_added"] += 1
                    else:
                        summary_stats["updated_species"] += 1
                        summary_stats["output_files_updated"] += 1

                    summary_stats["new_facts"] += merge_res.new_facts_count
                    summary_stats["duplicate_facts"] += merge_res.duplicate_facts_count
                    summary_stats["new_observations"] += merge_res.new_observations_count
                    if merge_res.conflicts_detected:
                        self.all_conflicts.extend(merge_res.conflicts_detected)

            # Register source if normal run
            if not dry_run:
                self.source_registry.register_source(
                    sha256_hash=sha256,
                    filename=file_p.name,
                    file_path=str(file_p.resolve()),
                    detected_format=doc.format,
                    species_count=file_species_count,
                    status="processed",
                    warnings=doc.parsing_warnings,
                )

        summary_stats["total_species"] = len(self.species_records) + len(prospective_new_species) if dry_run else len(self.species_records)
        summary_stats["conflicts_count"] = len(self.all_conflicts)
        summary_stats["legal_documents_total"] = len(self.legal_records)

        # 7. Save & Synchronize if not dry-run
        if not dry_run:
            self.source_registry.save()
            self.entity_registry.save()
            self.storage.synchronize_all_outputs(self.species_records, self.all_conflicts, self.legal_records)
            self.storage.generate_validation_report(summary_stats, self.all_conflicts, self.review_required_files)

            # 8. Save country-centric knowledge store
            self.knowledge_builder.save()

            # 9. Generate AI model training datasets (Primary axis: COUNTRY, Secondary axis: CATEGORY)
            print("\n[TRAINING DATASETS] Generating general-knowledge training datasets by country and category...")
            country_gen = CountryTrainingDatasetGenerator(self.output_dir)
            ds_stats = country_gen.generate()
            print(f"[TRAINING DATASETS] Finished: {ds_stats.get('sft_examples', 0)} SFT examples, {ds_stats.get('rag_chunks', 0)} RAG passages across {len(ds_stats.get('by_country_and_category', {}))} country/categories.")

        # Print detailed report
        self._print_summary_report(summary_stats, prospective_new_species, prospective_species_updates, dry_run)

        return summary_stats

    def _print_summary_report(
        self,
        stats: Dict[str, Any],
        prospective_new_species: List[str],
        prospective_updates: Dict[str, Dict[str, Any]],
        dry_run: bool,
    ) -> None:
        if dry_run:
            print("========================================")
            print("DRY-RUN PREVIEW (NO FILES MODIFIED)")
            print("========================================")
            print(f"NEW FILES TO PROCESS : {stats['new_resources']}")
            print(f"ALREADY PROCESSED    : {stats['already_known_resources']}")
            print(f"\nNEW SPECIES DETECTED ({len(prospective_new_species)}):")
            for sp in prospective_new_species:
                print(f"  + {sp}")

            print(f"\nEXISTING SPECIES TO ENRICH ({len(prospective_updates)}):")
            for sp, info in prospective_updates.items():
                print(f"  - {sp} -> +{info['facts']} facts, +{info['obs']} observations")

            if self.review_required_files:
                print(f"\nFILES REQUIRING REVIEW ({len(self.review_required_files)}):")
                for rf in self.review_required_files:
                    print(f"  * {rf['file']}: {rf['reason']}")
            print("========================================\n")
        else:
            print("========================================")
            print("PIPELINE COMPLETE")
            print("========================================")
            print(f"New resources       : {stats['new_resources']}")
            print(f"Already known       : {stats['already_known_resources']}")
            print(f"New species         : {stats['new_species']}")
            print(f"Updated species     : {stats['updated_species']}")
            print(f"New facts           : {stats['new_facts']}")
            print(f"Duplicate facts     : {stats['duplicate_facts']}")
            print(f"New observations    : {stats['new_observations']}")
            print(f"Conflicts detected  : {stats['conflicts_count']}")
            print(f"Human review needed : {len(self.review_required_files)}")
            print(f"Output files added  : {stats['output_files_added']}")
            print(f"Output files updated: {stats['output_files_updated']}")
            print(f"Total Database Size : {stats['total_species']} species")
            print("========================================\n")
