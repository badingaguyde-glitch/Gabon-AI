#!/usr/bin/env python3
"""CLI entry point for the Gabon Biodiversity Incremental Pipeline."""

import argparse
from pathlib import Path
import sys

# Ensure immediate unbuffered output in all terminals and logs
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

# Ensure root directory is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline_runner import BiodiversityPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Gabon Biodiversity Incremental Knowledge Pipeline (Multi-Format, Deduplicated, RAG Ready)"
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=str,
        default="data",
        help="Path to the disorganized input folder containing scientific documents (PDF, MD, CSV, XLSX, JSON, etc.)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=".",
        help="Path to the output directory where species/, metadata/, and RAG datasets will be generated/updated.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run analysis and show prospective updates/new species without modifying files.",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force reprocessing of all files even if already recorded in source_registry.json.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset entire database (clears species/, metadata/, legal/, knowledge/, datasets/) before running.",
    )
    parser.add_argument(
        "--country",
        "-c",
        type=str,
        default="Gabon",
        help="Primary country axis for knowledge organization (default: Gabon).",
    )
    parser.add_argument(
        "--skip-wiki",
        action="store_true",
        help="Skip the Wikipedia History crawler step.",
    )

    args = parser.parse_args()

    input_path = Path(args.input_dir)
    # If default 'data' doesn't exist, check 'input' or current dir
    if not input_path.exists():
        if Path("input").exists():
            input_path = Path("input")
        else:
            input_path = Path("data")
            input_path.mkdir(parents=True, exist_ok=True)

    pipeline = BiodiversityPipeline(output_dir=args.output_dir, country=args.country)
    if args.reset:
        pipeline.reset_database()
    pipeline.run(input_dir=input_path, dry_run=args.dry_run, force=args.force, skip_wiki=args.skip_wiki)


if __name__ == "__main__":
    main()
