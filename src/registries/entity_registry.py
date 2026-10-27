"""Global persistent entity registry maintaining stable species IDs and taxonomy categories."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


def normalize_species_name(name: str) -> str:
    """Normalizes a scientific binomial name into a clean slug (e.g. 'Gorilla gorilla' -> 'gorilla_gorilla')."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s_-]", "", name.strip().lower())
    return re.sub(r"[\s-]+", "_", cleaned)


class EntityRegistry:
    """Manages metadata/entity_registry.json with stable SPECIES-XXXXXX IDs and category assignment."""

    def __init__(
        self,
        registry_file: str | Path,
        categories_file: Optional[str | Path] = None,
        reference_taxonomy_file: Optional[str | Path] = None,
    ):
        self.registry_file = Path(registry_file)
        self.categories_map: Dict[str, List[str]] = {}
        self.kingdom_defaults: Dict[str, Dict[str, str]] = {}
        self.species: Dict[str, Dict[str, Any]] = {}  # species_id -> record
        self.name_to_id: Dict[str, str] = {}  # normalized scientific / synonym -> species_id
        self._next_id: int = 1

        cat_path = categories_file or Path(__file__).resolve().parent.parent.parent / "resources" / "categories.json"
        if Path(cat_path).is_file():
            self._load_categories(cat_path)

        ref_path = reference_taxonomy_file or Path(__file__).resolve().parent.parent.parent / "resources" / "reference_taxonomy.json"
        if Path(ref_path).is_file():
            self._seed_reference_taxonomy(ref_path)

        self.load()

    def _load_categories(self, path: str | Path) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.categories_map = data.get("categories", {})
                self.kingdom_defaults = data.get("kingdom_defaults", {})
        except Exception as e:
            print(f"Warning loading categories: {e}")

    def _seed_reference_taxonomy(self, path: str | Path) -> None:
        """Pre-populates internal taxonomy cache from reference_taxonomy.json if needed."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._seed_data = {sp["scientific_name"].lower(): sp for sp in data.get("species", [])}
        except Exception:
            self._seed_data = {}

    def load(self) -> None:
        if not self.registry_file.is_file():
            return
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for sp in data.get("species", []):
                    sid = sp["species_id"]
                    self.species[sid] = sp

                    norm_sci = sp["normalized_name"]
                    self.name_to_id[norm_sci] = sid
                    self.name_to_id[sp["scientific_name"].lower()] = sid

                    for syn in sp.get("synonyms", []):
                        self.name_to_id[normalize_species_name(syn)] = sid
                        self.name_to_id[syn.lower()] = sid

                    if sid.startswith("SPECIES-"):
                        try:
                            num = int(sid.split("-")[1])
                            if num >= self._next_id:
                                self._next_id = num + 1
                        except ValueError:
                            pass
        except Exception as e:
            print(f"Warning loading entity registry: {e}")

    def save(self) -> None:
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_species": len(self.species),
            "species": list(self.species.values()),
        }
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def determine_category(
        self,
        class_name: Optional[str] = None,
        order_name: Optional[str] = None,
        family_name: Optional[str] = None,
        scientific_name: Optional[str] = None,
    ) -> str:
        """Determines the category directory dynamically (e.g. mammals, arachnids, etc.)."""
        candidates = [class_name, order_name, family_name]
        for candidate in candidates:
            if not candidate:
                continue
            cand_lower = candidate.strip().lower()
            for cat, aliases in self.categories_map.items():
                if cand_lower == cat or cand_lower in aliases:
                    return cat

        # If class is provided, dynamically create new slug category (e.g. "Arachnida" -> "arachnids")
        if class_name:
            c_slug = class_name.strip().lower()
            if c_slug.endswith("a"):
                return c_slug[:-1] + "s"  # Arachnida -> arachnids
            return c_slug

        # Check seed taxonomy
        if scientific_name and hasattr(self, "_seed_data"):
            ref = self._seed_data.get(scientific_name.lower())
            if ref and ref.get("class"):
                return self.determine_category(class_name=ref.get("class"))

        # Check known Gabonese vertebrate & floral genera if still unclassified
        if scientific_name:
            genus = scientific_name.strip().split()[0].capitalize()
            # Amphibians
            if genus in ("Acanthixalus", "Afrixalus", "Alexteroon", "Amnirana", "Arthroleptis", 
                         "Astylosternus", "Cardioglossa", "Conraua", "Hemisus", "Hyperolius", 
                         "Leptopelis", "Nectophryne", "Opisthothylax", "Phlyctimantis", 
                         "Phrynobatrachus", "Ptychadena", "Xenopus", "Silurana"):
                return "amphibians"
            # Mammals
            if genus in ("Arctocebus", "Arctocephalus", "Balaenoptera", "Bdeogale", "Canis", "Capra", 
                         "Cephalophus", "Cercocebus", "Cercopithecus", "Civettictis", "Colobus", 
                         "Crossarchus", "Delphinus", "Eidolon", "Equus", "Euoticus", "Felis", 
                         "Galagoides", "Gazella", "Genetta", "Globicephala", "Gorilla", "Grampus", 
                         "Hippopotamus", "Hyaena", "Hydrictis", "Hyemoschus", "Kobus", "Lophocebus", 
                         "Loxodonta", "Loxodanta", "Lupulella", "Mandrillus", "Manis", "Miopithecus", 
                         "Nandinia", "Nanger", "Orcinus", "Pan", "Panthera", "Peponocephala", 
                         "Phataginus", "Philantomba", "Physeter", "Potamochoerus", "Profelis", 
                         "Protoxerus", "Pseudorca", "Redunca", "Sciurocheirus", "Smutsia", "Sousa", 
                         "Stenella", "Syncerus", "Tragelaphus", "Trichechus", "Tursiops", "Vulpes"):
                return "mammals"
            # Birds
            if genus in ("Accipiter", "Agapornis", "Agelastes", "Aquila", "Aviceda", "Balearica", 
                         "Circaetus", "Circus", "Dryotriorchis", "Elanus", "Eupodotis", "Francolinus", 
                         "Glaucidium", "Guttera", "Gypohierax", "Haliaeetus", "Hieraaetus", 
                         "Himantornis", "Jubula", "Lissotis", "Lophaetus", "Macheiramphus", "Melierax", 
                         "Milvus", "Neotis", "Otus", "Pernis", "Picathartes", "Poicephalus", 
                         "Polyboroides", "Psittacus", "Ptilopsis", "Scotopelia", "Spheniscus", 
                         "Spizaetus", "Stephanoaetus", "Strix", "Terathopius", "Torgos", "Turtur", 
                         "Urotriorchis"):
                return "birds"
            # Reptiles
            if genus in ("Calabaria", "Caretta", "Chelonia", "Crocodylus", "Dermochelys", 
                         "Eretmochelys", "Kinixys", "Lepidochelys", "Mecistops", "Osteolaemus", 
                         "Python", "Trioceros", "Varanus"):
                return "reptiles"
            # Fish
            if genus in ("Carcharodon", "Pristis", "Rhincodon", "Schizoculina", "Anomocora", "Phyllangia"):
                return "fish"
            # Plants
            if genus in ("Aucoumea", "Cyathea", "Dichapetalum", "Scaphopetalum", "Thomandersia", "Dialium"):
                return "plants"
            # Arachnids
            if genus in ("Amblyomma", "Haemaphysalis", "Hyalomma", "Ixodes", "Rhipicentor", "Rhipicephalus"):
                return "arachnids"

        return "unclassified"

    def allocate_species_id(self) -> str:
        sid = f"SPECIES-{self._next_id:06d}"
        self._next_id += 1
        return sid

    def resolve_or_create(
        self,
        scientific_name: str,
        class_name: Optional[str] = None,
        order_name: Optional[str] = None,
        family_name: Optional[str] = None,
        synonyms: Optional[List[str]] = None,
        common_names: Optional[Dict[str, List[str]]] = None,
        iucn_status: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """Resolves an existing species or registers a new entity.

        Returns: (species_id, is_newly_created)
        """
        norm_name = normalize_species_name(scientific_name)
        sci_lower = scientific_name.strip().lower()

        # Check exact matches
        if norm_name in self.name_to_id:
            return self.name_to_id[norm_name], False
        if sci_lower in self.name_to_id:
            return self.name_to_id[sci_lower], False

        # Check synonyms
        if synonyms:
            for syn in synonyms:
                norm_syn = normalize_species_name(syn)
                if norm_syn in self.name_to_id:
                    return self.name_to_id[norm_syn], False
                if syn.lower() in self.name_to_id:
                    return self.name_to_id[syn.lower()], False

        # If in seed reference data, import taxonomic details
        ref_entry = getattr(self, "_seed_data", {}).get(sci_lower, {})
        final_class = class_name or ref_entry.get("class")
        final_order = order_name or ref_entry.get("order")
        final_family = family_name or ref_entry.get("family")
        final_iucn = iucn_status or ref_entry.get("iucn_status")

        all_synonyms = set(synonyms or [])
        all_synonyms.update(ref_entry.get("synonyms", []))

        merged_common: Dict[str, List[str]] = {"en": [], "fr": []}
        if common_names:
            for lang, names in common_names.items():
                merged_common.setdefault(lang, []).extend(names)
        if "common_names" in ref_entry:
            for lang, names in ref_entry["common_names"].items():
                merged_common.setdefault(lang, []).extend(names)

        category = self.determine_category(
            class_name=final_class,
            order_name=final_order,
            family_name=final_family,
            scientific_name=scientific_name,
        )

        if not final_class and category in self.kingdom_defaults:
            final_class = self.kingdom_defaults[category].get("class", "")

        new_id = self.allocate_species_id()
        record = {
            "species_id": new_id,
            "scientific_name": scientific_name.strip(),
            "normalized_name": norm_name,
            "category": category,
            "taxonomy": {
                "class": final_class or "",
                "order": final_order or "",
                "family": final_family or "",
            },
            "synonyms": list(sorted(all_synonyms)),
            "common_names": {k: list(sorted(set(v))) for k, v in merged_common.items()},
            "iucn_status": final_iucn,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self.species[new_id] = record
        self.name_to_id[norm_name] = new_id
        self.name_to_id[sci_lower] = new_id
        for syn in all_synonyms:
            self.name_to_id[normalize_species_name(syn)] = new_id
            self.name_to_id[syn.lower()] = new_id

        return new_id, True

    def get_species_record(self, species_id: str) -> Optional[Dict[str, Any]]:
        return self.species.get(species_id)

    def update_taxonomy_if_better(
        self,
        species_id: str,
        class_name: Optional[str] = None,
        order_name: Optional[str] = None,
        family_name: Optional[str] = None,
        iucn_status: Optional[str] = None,
    ) -> bool:
        rec = self.species.get(species_id)
        if not rec:
            return False
        changed = False
        tax = rec.setdefault("taxonomy", {})
        if class_name and not tax.get("class"):
            tax["class"] = class_name
            changed = True
        if order_name and not tax.get("order"):
            tax["order"] = order_name
            changed = True
        if family_name and not tax.get("family"):
            tax["family"] = family_name
            changed = True
        if iucn_status and not rec.get("iucn_status"):
            rec["iucn_status"] = iucn_status
            changed = True
        if rec.get("category") == "unclassified":
            new_cat = self.determine_category(
                class_name=tax.get("class"),
                order_name=tax.get("order"),
                family_name=tax.get("family"),
                scientific_name=rec.get("scientific_name"),
            )
            if new_cat != "unclassified":
                rec["category"] = new_cat
                changed = True
        return changed
