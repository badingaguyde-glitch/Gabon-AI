"""Comprehensive end-to-end and unit tests for the incremental multi-format pipeline."""

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from src.format_detector import FormatDetector, compute_file_sha256
from src.parsers.parser_registry import default_registry
from src.species_detector import SpeciesDetector
from src.registries import SourceRegistry, EntityRegistry
from src.information_extraction import InformationExtractor
from src.merging import IntelligentMergeEngine
from src.pipeline_runner import BiodiversityPipeline


class TestBiodiversityPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="bio_test_")
        self.temp_path = Path(self.temp_dir)
        self.input_dir = self.temp_path / "input"
        self.output_dir = self.temp_path / "output"
        self.input_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_format_detector(self):
        # Markdown
        md_file = self.input_dir / "sample.md"
        md_file.write_text("# Gorilla gorilla\nDiet: herbivore\n", encoding="utf-8")
        res = FormatDetector.detect(md_file)
        self.assertEqual(res.format_name, "markdown")
        self.assertEqual(res.parser_name, "markdown_parser")

        # JSON
        json_file = self.input_dir / "sample.json"
        json_file.write_text('{"scientific_name": "Pan troglodytes"}', encoding="utf-8")
        res = FormatDetector.detect(json_file)
        self.assertEqual(res.format_name, "json")

        # CSV
        csv_file = self.input_dir / "sample.csv"
        csv_file.write_text("species,location,count\nGorilla gorilla,Lopé,45\n", encoding="utf-8")
        res = FormatDetector.detect(csv_file)
        self.assertEqual(res.format_name, "csv")

    def test_species_detection(self):
        detector = SpeciesDetector()
        text = "During our census in Lopé National Park, we observed Gorilla gorilla and Pan troglodytes eating fruits."
        mentions = detector.detect_in_text(text)
        detected_names = {m.canonical_name for m in mentions}
        self.assertIn("Gorilla gorilla", detected_names)
        self.assertIn("Pan troglodytes", detected_names)

    def test_multi_format_and_archive_parsing(self):
        # Create a ZIP archive with multiple files
        zip_path = self.input_dir / "archive.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("elephants.md", "# Loxodonta cyclotis\nHabitat: tropical rainforest\nPopulation: 1200\n")
            z.writestr("counts.csv", "Species,Location,Count,Year\nLoxodonta cyclotis,Ivindo,42,2022\n")

        doc = default_registry.parse_file(zip_path, source_id="SRC-TEST-01")
        self.assertIn("Loxodonta cyclotis", doc.raw_text)
        self.assertTrue(len(doc.tables) >= 1)

    def test_incremental_cumulative_enrichment(self):
        pipeline = BiodiversityPipeline(output_dir=self.output_dir)

        # Batch 1: Initial study
        batch1_file = self.input_dir / "gorilla_initial.md"
        batch1_file.write_text("""# Gorilla gorilla

## Diet
Gorilla gorilla is a herbivore.

## Habitat
Inhabits forest ecosystems in Gabon.
""", encoding="utf-8")

        stats1 = pipeline.run(input_dir=self.input_dir)
        self.assertEqual(stats1["new_species"], 1)
        self.assertEqual(stats1["new_resources"], 1)

        gorilla_json_path = self.output_dir / "species" / "mammals" / "gorilla_gorilla.json"
        self.assertTrue(gorilla_json_path.is_file())

        with open(gorilla_json_path, "r", encoding="utf-8") as f:
            g_data = json.load(f)
            self.assertEqual(g_data["version"], 1)
            self.assertIn("herbivore", g_data["facts"]["diet"]["type"]["value"])

        # Batch 2: Idempotence test (re-running with same files changes nothing)
        stats2 = pipeline.run(input_dir=self.input_dir)
        self.assertEqual(stats2["new_resources"], 0)
        self.assertEqual(stats2["already_known_resources"], 1)
        self.assertEqual(stats2["new_species"], 0)

        # Batch 3: Adding new enriched study + observations
        batch2_file = self.input_dir / "gorilla_study_2.md"
        batch2_file.write_text("""# Gorilla gorilla

## Diet
Gorilla gorilla consumes fruits, leaves, stems, seeds and is a frugivore.

## Habitat
Gorilla gorilla lives in lowland moist tropical forest.

## Observations
| Species | Location | Count | Year |
|---|---|---|---|
| Gorilla gorilla | Lopé | 52 | 2021 |
| Gorilla gorilla | Loango | 18 | 2023 |
""", encoding="utf-8")

        # Also add a new species from a new category (Arachnida)
        arachnid_file = self.input_dir / "scorpion.json"
        arachnid_file.write_text(json.dumps({
            "scientific_name": "Pandinus imperator",
            "class": "Arachnida",
            "diet": "carnivore",
            "food_items": ["insects"],
            "location": "Monts de Cristal"
        }), encoding="utf-8")

        stats3 = pipeline.run(input_dir=self.input_dir)
        self.assertEqual(stats3["new_resources"], 2)
        self.assertEqual(stats3["new_species"], 1)  # Pandinus imperator
        self.assertEqual(stats3["updated_species"], 1)  # Gorilla gorilla

        # Verify dynamic category creation: species/arachnids/pandinus_imperator.json
        scorpion_json_path = self.output_dir / "species" / "arachnids" / "pandinus_imperator.json"
        self.assertTrue(scorpion_json_path.is_file())

        # Verify Gorilla gorilla is enriched without duplicate files
        with open(gorilla_json_path, "r", encoding="utf-8") as f:
            g_data2 = json.load(f)
            self.assertEqual(g_data2["version"], 2)
            # Diet type should be enriched
            diet_types = g_data2["facts"]["diet"]["type"]["value"]
            self.assertIn("herbivore", diet_types)
            self.assertIn("frugivore", diet_types)
            # Food items should be present
            food_items = g_data2["facts"]["diet"]["food_items"]["value"]
            self.assertIn("fruits", food_items)
            self.assertIn("leaves", food_items)
            # Observations should be added
            self.assertTrue(len(g_data2["observations"]) >= 2)

        # Check synchronized outputs
        all_sp_path = self.output_dir / "all_species.json"
        all_facts_path = self.output_dir / "all_facts.json"
        rag_jsonl_path = self.output_dir / "species_documents.jsonl"
        changelog_path = self.output_dir / "metadata" / "change_log.jsonl"
        val_rep_path = self.output_dir / "validation_report.md"

        self.assertTrue(all_sp_path.is_file())
        self.assertTrue(all_facts_path.is_file())
        self.assertTrue(rag_jsonl_path.is_file())
        self.assertTrue(changelog_path.is_file())
        self.assertTrue(val_rep_path.is_file())

        with open(all_sp_path, "r", encoding="utf-8") as f:
            all_sp = json.load(f)
            self.assertEqual(all_sp["total_species"], 2)


if __name__ == "__main__":
    unittest.main()
