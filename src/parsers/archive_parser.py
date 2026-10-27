"""Archive parser (ZIP, TAR, GZ, 7z) performing non-destructive temporary extraction of inner files."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from typing import List, Optional
import zipfile

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language


class ArchiveParser(BaseParser):
    name = "archive_parser"
    supported_formats = ["zip", "tar", "gzip", "tar_gz", "7z", "bzip2", "xz"]

    def __init__(self, registry=None):
        self.registry = registry

    def set_registry(self, registry):
        self.registry = registry

    def _extract_archive(self, file_path: Path, target_dir: Path, max_depth: int = 4) -> List[Path]:
        extracted_files: List[Path] = []
        name_lower = file_path.name.lower()

        if name_lower.endswith(".zip") or zipfile.is_zipfile(file_path):
            try:
                with zipfile.ZipFile(file_path, "r") as z:
                    for member in z.namelist():
                        if not member.startswith(("/", "\\")) and ".." not in member:
                            z.extract(member, target_dir)
            except Exception:
                pass
        elif name_lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
            try:
                with tarfile.open(file_path, "r:*") as t:
                    t.extractall(target_dir)
            except Exception:
                pass
        elif name_lower.endswith(".7z"):
            try:
                import py7zr
                with py7zr.SevenZipFile(file_path, mode="r") as z:
                    z.extractall(path=target_dir)
            except Exception:
                pass

        # Check for nested archives inside target_dir and extract them recursively
        if max_depth > 0:
            nested_archives = []
            for root, _, files in os.walk(target_dir):
                for f in files:
                    fp = Path(root) / f
                    if fp.name.lower().endswith((".zip", ".tar", ".tar.gz", ".tgz", ".7z")) and fp != file_path:
                        nested_archives.append(fp)

            for n_arch in nested_archives:
                sub_dir = n_arch.parent / f"extracted_{n_arch.stem}"
                sub_dir.mkdir(parents=True, exist_ok=True)
                self._extract_archive(n_arch, sub_dir, max_depth=max_depth - 1)
                try:
                    n_arch.unlink()  # Remove inner archive file after extracting its contents
                except Exception:
                    pass

        # Collect all extracted regular files
        for root, _, files in os.walk(target_dir):
            for f in files:
                extracted_files.append(Path(root) / f)

        return extracted_files

    def parse(
        self,
        file_path: str | Path,
        source_id: str,
        detected_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> InternalDocument:
        p = Path(file_path)
        doc = self.create_empty_doc(p, source_id, detected_format or "zip", encoding="binary")

        temp_dir = Path(tempfile.mkdtemp(prefix="bio_archive_"))
        try:
            inner_files = self._extract_archive(p, temp_dir)
            doc.document_metadata["extracted_files_count"] = len(inner_files)
            doc.document_metadata["extracted_files"] = [str(f.relative_to(temp_dir)) for f in inner_files]

            all_sub_texts: List[str] = []
            all_tables: List[TableData] = []
            all_paragraphs: List[str] = []
            sections: List[DocumentSection] = []

            for idx, inner_p in enumerate(inner_files, start=1):
                if inner_p.is_file():
                    sub_source_id = f"{source_id}_f{idx:02d}"
                    if self.registry:
                        try:
                            sub_doc = self.registry.parse_file(inner_p, source_id=sub_source_id)
                            all_sub_texts.append(f"=== File: {inner_p.name} ===\n{sub_doc.raw_text}")
                            all_tables.extend(sub_doc.tables)
                            all_paragraphs.extend(sub_doc.paragraphs)
                            sections.append(
                                DocumentSection(
                                    title=f"Archive Item: {inner_p.name}",
                                    level=1,
                                    content=sub_doc.raw_text[:2000],
                                )
                            )
                        except Exception as e:
                            doc.parsing_warnings.append(f"Failed to parse inner file {inner_p.name}: {e}")
                    else:
                        # Simple text fallback
                        try:
                            t = inner_p.read_text(encoding="utf-8", errors="replace")
                            all_sub_texts.append(f"=== File: {inner_p.name} ===\n{t}")
                        except Exception:
                            pass

            doc.raw_text = "\n\n".join(all_sub_texts)
            doc.tables = all_tables
            doc.paragraphs = all_paragraphs
            doc.sections = sections

            lang, conf = detect_text_language(doc.raw_text)
            doc.language = lang
            doc.language_confidence = conf
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return doc
