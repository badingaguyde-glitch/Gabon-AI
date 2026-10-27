"""Global persistent source registry ensuring idempotence and tracking processed documents by SHA-256."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SourceRegistry:
    """Manages metadata/source_registry.json with SHA256 indexing."""

    def __init__(self, registry_file: str | Path):
        self.registry_file = Path(registry_file)
        self.sources: Dict[str, Dict[str, Any]] = {}  # source_id -> metadata
        self.hash_to_source_id: Dict[str, str] = {}  # sha256 -> source_id
        self._next_id: int = 1
        self.load()

    def load(self) -> None:
        if not self.registry_file.is_file():
            return
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                sources_list = data.get("sources", [])
                for s in sources_list:
                    sid = s["source_id"]
                    self.sources[sid] = s
                    if "sha256" in s:
                        self.hash_to_source_id[s["sha256"]] = sid
                    # Track next numeric ID
                    if sid.startswith("SRC-"):
                        try:
                            num = int(sid.split("-")[1])
                            if num >= self._next_id:
                                self._next_id = num + 1
                        except ValueError:
                            pass
        except Exception as e:
            print(f"Warning loading source registry {self.registry_file}: {e}")

    def save(self) -> None:
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_sources": len(self.sources),
            "sources": list(self.sources.values()),
        }
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def is_known_hash(self, sha256_hash: str) -> bool:
        """Returns True if this exact file content hash has already been processed."""
        return sha256_hash in self.hash_to_source_id

    def get_source_id_by_hash(self, sha256_hash: str) -> Optional[str]:
        return self.hash_to_source_id.get(sha256_hash)

    def allocate_source_id(self) -> str:
        sid = f"SRC-{self._next_id:06d}"
        self._next_id += 1
        return sid

    def register_source(
        self,
        sha256_hash: str,
        filename: str,
        file_path: str,
        detected_format: str,
        species_count: int = 0,
        status: str = "processed",
        warnings: Optional[List[str]] = None,
    ) -> str:
        """Registers a newly processed source and returns its assigned source_id."""
        existing_id = self.get_source_id_by_hash(sha256_hash)
        if existing_id:
            # Update metadata if needed
            self.sources[existing_id]["status"] = status
            self.sources[existing_id]["last_seen_at"] = datetime.now(timezone.utc).isoformat()
            return existing_id

        new_id = self.allocate_source_id()
        record = {
            "source_id": new_id,
            "filename": filename,
            "file_path": file_path,
            "sha256": sha256_hash,
            "format": detected_format,
            "status": status,
            "species_count": species_count,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "warnings": warnings or [],
        }
        self.sources[new_id] = record
        self.hash_to_source_id[sha256_hash] = new_id
        return new_id
