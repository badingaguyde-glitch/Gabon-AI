"""Information extraction module extracting structured scientific facts and field observations."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.models import (
    InternalDocument,
    Fact,
    Observation,
    SourceProvenance,
    TableData,
)
from src.normalization import (
    normalize_park_name,
    normalize_iucn_status,
    normalize_diet_type,
    normalize_measurement_unit,
    GABON_PARKS,
)

# Common scientific concepts keywords in French and English
SECTION_TOPIC_KEYWORDS = {
    "diet": ["diet", "alimentation", "régime alimentaire", "food", "nutrition", "feeding", "prey", "proies"],
    "habitat": ["habitat", "ecology", "écologie", "vegetation", "environment", "milieu", "biotope"],
    "population": ["population", "abundance", "abondance", "density", "densité", "census", "estimate", "effectif"],
    "distribution": ["distribution", "range", "repartition", "répartition", "localities", "occurrences", "presence"],
    "conservation": ["conservation", "threats", "menaces", "status", "statut", "protection", "iucn", "poaching", "braconnage"],
    "morphology": ["morphology", "morphologie", "measurements", "mensurations", "size", "taille", "weight", "poids", "mass"],
    "reproduction": ["reproduction", "breeding", "gestation", "litter", "portée", "mating"],
    "behavior": ["behavior", "behaviour", "comportement", "social", "activity", "activité"],
}

FOOD_ITEM_PATTERNS = [
    r"\b(fruits?|leaves|feuilles?|stems?|tiges?|seeds?|graines?|bark|écorces?|roots?|racines?|flowers?|fleurs?|insects?|insectes?|ants?|fourmis?|termites?|fish|poissons?|mammals?|mammifères?|birds?|oiseaux?|fungi|champignons?|herbs?|herbes?)\b"
]


class InformationExtractor:
    """Extracts structured scientific facts and observations for detected species."""

    def __init__(self):
        self._fact_counter = 1
        self._obs_counter = 1

    def _next_fact_id(self) -> str:
        fid = f"FACT-{self._fact_counter:06d}"
        self._fact_counter += 1
        return fid

    def _next_obs_id(self) -> str:
        oid = f"OBS-{self._obs_counter:06d}"
        self._obs_counter += 1
        return oid

    def _classify_section_topic(self, title: str) -> Optional[str]:
        title_lower = title.lower()
        for topic, keywords in SECTION_TOPIC_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                return topic
        return None

    def extract_from_table(
        self,
        table: TableData,
        species_name: str,
        source_id: str,
    ) -> List[Observation]:
        """Extracts field observations from tabular rows."""
        observations: List[Observation] = []
        if not table.columns or not table.rows:
            return observations

        col_lower = [str(c).lower() if c is not None else "" for c in table.columns]

        # Identify key column indices
        sp_col = next((i for i, c in enumerate(col_lower) if any(k in c for k in ["specie", "espèce", "taxon", "animal"])), None)
        loc_col = next((i for i, c in enumerate(col_lower) if any(k in c for k in ["loc", "site", "park", "parc", "station", "place"])), None)
        count_col = next((i for i, c in enumerate(col_lower) if any(k in c for k in ["count", "number", "nombre", "effectif", "individuals", "ind", "obs", "total"])), None)
        year_col = next((i for i, c in enumerate(col_lower) if any(k in c for k in ["year", "an", "année", "date", "period"])), None)
        method_col = next((i for i, c in enumerate(col_lower) if any(k in c for k in ["method", "méthode", "type", "protocol"])), None)

        for r_idx, row in enumerate(table.rows, start=1):
            row_str = " ".join(str(cell) for cell in row)
            # Check if this row mentions the species
            if species_name.lower() in row_str.lower() or (sp_col is not None and sp_col < len(row) and species_name.lower() in str(row[sp_col]).lower()):
                location = str(row[loc_col]).strip() if loc_col is not None and loc_col < len(row) else None
                count_val = None
                if count_col is not None and count_col < len(row):
                    raw_count = str(row[count_col]).strip()
                    m = re.search(r"(\d+(?:\.\d+)?)", raw_count)
                    if m:
                        count_val = float(m.group(1)) if "." in m.group(1) else int(m.group(1))

                year_val = None
                if year_col is not None and year_col < len(row):
                    raw_year = str(row[year_col]).strip()
                    m = re.search(r"\b(19\d\d|20\d\d)\b", raw_year)
                    if m:
                        year_val = int(m.group(1))

                method_val = str(row[method_col]).strip() if method_col is not None and method_col < len(row) else None

                park_normalized = normalize_park_name(location) if location else None

                prov = SourceProvenance(
                    source_id=source_id,
                    filename="",
                    table_id=table.table_id,
                    page=table.page,
                    line_number=r_idx,
                    extracted_text_snippet=f"Table row: {row_str[:150]}",
                )

                obs = Observation(
                    observation_id=self._next_obs_id(),
                    location=location,
                    park_name=park_normalized,
                    year=year_val,
                    count=count_val,
                    count_type="individuals" if count_val is not None else None,
                    method=method_val,
                    source_id=source_id,
                    provenance=prov,
                )
                observations.append(obs)

        return observations

    def extract_from_text(
        self,
        text: str,
        species_name: str,
        source_id: str,
        section_title: str = "",
        page: Optional[int] = None,
    ) -> Tuple[List[Fact], List[Observation]]:
        """Extracts facts and observations from a snippet/paragraph/section mentioning species."""
        facts: List[Fact] = []
        observations: List[Observation] = []

        if not text:
            return facts, observations

        topic = self._classify_section_topic(section_title)
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if len(s.strip()) > 5]

        for s in sentences:
            s_lower = s.lower()

            # 1. Diet extraction
            if topic == "diet" or any(k in s_lower for k in ["diet", "eats", "consumes", "consumme", "mange", "nourrit", "frugivore", "herbivore", "folivore", "carnivore"]):
                # Extract diet type
                for dtype in ["herbivore", "frugivore", "folivore", "carnivore", "insectivore", "omnivore", "piscivore"]:
                    if dtype in s_lower:
                        norm_dtype = normalize_diet_type(dtype)
                        prov = SourceProvenance(source_id=source_id, filename="", section=section_title, page=page, extracted_text_snippet=s[:150])
                        facts.append(
                            Fact(
                                fact_id=self._next_fact_id(),
                                category="diet",
                                predicate="type",
                                value=[norm_dtype],
                                sources=[source_id],
                                provenance=[prov],
                            )
                        )

                # Extract food items
                items_found = set()
                for pat in FOOD_ITEM_PATTERNS:
                    for m in re.finditer(pat, s_lower):
                        items_found.add(m.group(1))

                if items_found:
                    prov = SourceProvenance(source_id=source_id, filename="", section=section_title, page=page, extracted_text_snippet=s[:150])
                    facts.append(
                        Fact(
                            fact_id=self._next_fact_id(),
                            category="diet",
                            predicate="food_items",
                            value=list(sorted(items_found)),
                            sources=[source_id],
                            provenance=[prov],
                        )
                    )

            # 2. Habitat extraction
            if topic == "habitat" or any(k in s_lower for k in ["habitat", "forest", "forêt", "savanna", "savane", "swamp", "canopy", "mangrove"]):
                hab_matches = []
                if "tropical" in s_lower or "rainforest" in s_lower or "forêt tropicale" in s_lower:
                    if "lowland" in s_lower or "basse altitude" in s_lower:
                        hab_matches.append("lowland moist tropical forest")
                    else:
                        hab_matches.append("tropical rainforest")
                elif "primary forest" in s_lower or "forêt primaire" in s_lower:
                    hab_matches.append("primary forest")
                elif "secondary forest" in s_lower or "forêt secondaire" in s_lower:
                    hab_matches.append("secondary forest")
                elif "savanna" in s_lower or "savane" in s_lower:
                    hab_matches.append("savanna")
                elif "mangrove" in s_lower:
                    hab_matches.append("mangrove")

                if hab_matches:
                    for h in hab_matches:
                        prov = SourceProvenance(source_id=source_id, filename="", section=section_title, page=page, extracted_text_snippet=s[:150])
                        facts.append(
                            Fact(
                                fact_id=self._next_fact_id(),
                                category="habitat",
                                predicate="type",
                                value=h,
                                sources=[source_id],
                                provenance=[prov],
                            )
                        )

            # 3. Population extraction & Observation extraction
            if topic in ("population", "distribution") or any(k in s_lower for k in ["population", "individuals", "individus", "estimated", "estimée", "observed", "observé", "census"]):
                m_count = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:individuals|individus|animals|animaux|specimens|spécimens|head|têtes)?\b", s, re.IGNORECASE)
                m_year = re.search(r"\b(19\d\d|20\d\d)\b", s)

                # Check for Gabon Park mentions
                found_park = None
                for p_key, p_canonical in GABON_PARKS.items():
                    if p_key in s_lower:
                        found_park = p_canonical
                        break

                if m_count:
                    cnt = float(m_count.group(1).replace(",", "."))
                    cnt_val = int(cnt) if cnt.is_integer() else cnt

                    yr = int(m_year.group(1)) if m_year else None

                    # If specific location / year is attached, record as Observation
                    prov = SourceProvenance(source_id=source_id, filename="", section=section_title, page=page, extracted_text_snippet=s[:150])
                    if found_park or yr:
                        obs = Observation(
                            observation_id=self._next_obs_id(),
                            location=found_park or "Gabon",
                            park_name=found_park,
                            year=yr,
                            count=cnt_val,
                            count_type="individuals",
                            source_id=source_id,
                            provenance=prov,
                        )
                        observations.append(obs)
                    else:
                        facts.append(
                            Fact(
                                fact_id=self._next_fact_id(),
                                category="population",
                                predicate="estimate",
                                value=cnt_val,
                                sources=[source_id],
                                provenance=[prov],
                                metadata={"year": yr, "location": found_park},
                            )
                        )

            # 4. Conservation & IUCN status
            if topic == "conservation" or any(k in s_lower for k in ["iucn", "status", "statut", "endangered", "menacé", "threat", "menace", "poaching", "braconnage"]):
                for status_name in ["critically endangered", "en danger critique", "endangered", "en danger", "vulnerable", "vulnérable", "near threatened", "least concern"]:
                    if status_name in s_lower:
                        st = normalize_iucn_status(status_name)
                        if st:
                            prov = SourceProvenance(source_id=source_id, filename="", section=section_title, page=page, extracted_text_snippet=s[:150])
                            facts.append(
                                Fact(
                                    fact_id=self._next_fact_id(),
                                    category="conservation",
                                    predicate="iucn_status",
                                    value=st,
                                    sources=[source_id],
                                    provenance=[prov],
                                )
                            )

            # 5. Morphometrics / Measurements
            if topic == "morphology" or any(k in s_lower for k in ["weight", "poids", "mass", "length", "longueur", "height", "hauteur"]):
                m_meas = re.search(r"(\d+(?:[.,]\d+)?(?:\s*-\s*\d+(?:[.,]\d+)?)?\s*(?:kg|g|cm|m|mm|kgs|kilograms))\b", s, re.IGNORECASE)
                if m_meas:
                    norm_val = normalize_measurement_unit(m_meas.group(1))
                    pred = "weight" if norm_val.get("unit") == "kg" else "length"
                    prov = SourceProvenance(source_id=source_id, filename="", section=section_title, page=page, extracted_text_snippet=s[:150])
                    facts.append(
                        Fact(
                            fact_id=self._next_fact_id(),
                            category="morphology",
                            predicate=pred,
                            value=norm_val,
                            sources=[source_id],
                            provenance=[prov],
                        )
                    )

        # 6. Generic scientific fact extraction for any unclassified section/topic
        if topic and topic not in ("diet", "habitat", "population", "distribution", "conservation", "morphology"):
            if sentences:
                prov = SourceProvenance(source_id=source_id, filename="", section=section_title, page=page, extracted_text_snippet=text[:150])
                facts.append(
                    Fact(
                        fact_id=self._next_fact_id(),
                        category=topic,
                        predicate="details",
                        value=text.strip(),
                        sources=[source_id],
                        provenance=[prov],
                    )
                )

        return facts, observations

    def extract_taxonomy_clues(self, doc: InternalDocument, species_name: str) -> Dict[str, Any]:
        """Extracts taxonomic clues (Kingdom, Phylum, Class, Order, Family, IUCN, Synonyms) from document text or structured records."""
        clues: Dict[str, Any] = {
            "class_name": None,
            "order_name": None,
            "family_name": None,
            "synonyms": [],
            "common_names": {"en": [], "fr": []},
            "iucn_status": None,
        }

        # 1. Structured records (JSON, YAML, CSV, CITES guide)
        for rec in doc.structured_data:
            rec_sp = str(rec.get("scientific_name", rec.get("species", ""))).strip().lower()
            if not rec_sp or species_name.lower() in rec_sp or rec_sp in species_name.lower():
                if "class" in rec or "classe" in rec:
                    clues["class_name"] = str(rec.get("class", rec.get("classe", ""))).strip()
                if "order" in rec or "ordre" in rec:
                    clues["order_name"] = str(rec.get("order", rec.get("ordre", ""))).strip()
                if "family" in rec or "famille" in rec:
                    clues["family_name"] = str(rec.get("family", rec.get("famille", ""))).strip()
                if "iucn_status" in rec or "status" in rec or "statut" in rec:
                    st = normalize_iucn_status(str(rec.get("iucn_status", rec.get("status", rec.get("statut", "")))))
                    if st:
                        clues["iucn_status"] = st
                if "common_name" in rec or "nom_commun" in rec or "common_name_fr" in rec:
                    cn = str(rec.get("common_name", rec.get("nom_commun", rec.get("common_name_fr", "")))).strip()
                    if cn:
                        clues["common_names"]["fr"].append(cn)
                if "common_name_en" in rec:
                    cn_en = str(rec["common_name_en"]).strip()
                    if cn_en:
                        clues["common_names"]["en"].append(cn_en)
                if "synonyms" in rec and isinstance(rec["synonyms"], list):
                    clues["synonyms"].extend(rec["synonyms"])

        # 1b. Check tables for columns like Class, Order, Family
        sp_l = species_name.lower()
        sp_parts = sp_l.split()
        genus_cand = sp_parts[0] if sp_parts else ""
        epithet_cand = sp_parts[1] if len(sp_parts) > 1 else ""

        for tab in doc.tables:
            col_l = [str(c).lower().strip() if c is not None else "" for c in tab.columns]
            cls_col = next((i for i, c in enumerate(col_l) if c in ("class", "classe")), None)
            ord_col = next((i for i, c in enumerate(col_l) if c in ("order", "ordre")), None)
            fam_col = next((i for i, c in enumerate(col_l) if c in ("family", "famille")), None)
            gen_col = next((i for i, c in enumerate(col_l) if c in ("genus", "genre")), None)
            sp_col = next((i for i, c in enumerate(col_l) if c in ("species", "espèce", "espece", "species_name")), None)
            sci_col = next((i for i, c in enumerate(col_l) if any(k in c for k in ("scientific_name", "nom_scientifique", "taxon"))), None)

            if fam_col is not None or cls_col is not None or ord_col is not None:
                for r in tab.rows:
                    matches = False
                    if sci_col is not None and sci_col < len(r) and r[sci_col] is not None:
                        if sp_l in str(r[sci_col]).lower():
                            matches = True
                    elif gen_col is not None and sp_col is not None and gen_col < len(r) and sp_col < len(r):
                        if (str(r[gen_col]).strip().lower() == genus_cand and 
                            str(r[sp_col]).strip().lower() == epithet_cand):
                            matches = True
                    if matches:
                        if cls_col is not None and cls_col < len(r) and r[cls_col] and not clues["class_name"]:
                            c_val = str(r[cls_col]).strip()
                            if c_val and c_val.lower() not in ("nan", "null", "none"):
                                clues["class_name"] = c_val.capitalize()
                        if ord_col is not None and ord_col < len(r) and r[ord_col] and not clues["order_name"]:
                            o_val = str(r[ord_col]).strip()
                            if o_val and o_val.lower() not in ("nan", "null", "none"):
                                clues["order_name"] = o_val.capitalize()
                        if fam_col is not None and fam_col < len(r) and r[fam_col] and not clues["family_name"]:
                            f_val = str(r[fam_col]).strip()
                            if f_val and f_val.lower() not in ("nan", "null", "none"):
                                clues["family_name"] = f_val.capitalize()
                        if clues["class_name"] and clues["family_name"]:
                            break

        # 1c. Infer class from family if missing
        if clues["family_name"] and not clues["class_name"]:
            fam_l = clues["family_name"].lower()
            if fam_l in ("arthroleptidae", "hyperoliidae", "bufonidae", "ranidae", "pipidae", "phrynobatrachidae", "ptychadenidae", "hemisotidae", "conrauidae", "dicroglossidae"):
                clues["class_name"] = "Amphibia"
            elif fam_l in ("hominidae", "cercopithecidae", "bovidae", "elephantidae", "felidae", "suidae", "tragulidae", "mustelidae", "viverridae", "herpestidae", "pteropodidae", "lorisidae", "manidae", "sciuridae", "hystricidae", "leporidae"):
                clues["class_name"] = "Mammalia"
            elif fam_l in ("phasianidae", "columbidae", "musophagidae", "bucerotidae", "accipitridae", "pycnonotidae"):
                clues["class_name"] = "Aves"
            elif fam_l in ("crocodylidae", "cheloniidae", "dermochelyidae", "pythonidae", "viperidae", "colubridae", "testudinidae"):
                clues["class_name"] = "Reptilia"

        # 2. Textual patterns in sections and raw text
        full_text = doc.raw_text
        patterns = {
            "class_name": r"\b(?:Class|Classe)\s*[:=]\s*([A-Za-z]+)\b",
            "order_name": r"\b(?:Order|Ordre)\s*[:=]\s*([A-Za-z]+)\b",
            "family_name": r"\b(?:Family|Famille)\s*[:=]\s*([A-Za-z]+)\b",
            "iucn_status": r"\b(?:IUCN|UICN|Status|Statut)\s*[:=]?\s*(CR|EN|VU|NT|LC|DD|Critically Endangered|Endangered|Vulnerable|Near Threatened|Least Concern|En danger critique|En danger|Vulnérable)\b",
        }

        for key, pat in patterns.items():
            if not clues[key]:
                m = re.search(pat, full_text, re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    if key == "iucn_status":
                        clues[key] = normalize_iucn_status(val)
                    else:
                        clues[key] = val.capitalize()

        return clues

    def extract_from_document(
        self,
        doc: InternalDocument,
        species_name: str,
    ) -> Tuple[List[Fact], List[Observation]]:
        """Runs full factual and observational extraction on InternalDocument for a target species."""
        all_facts: List[Fact] = []
        all_obs: List[Observation] = []

        # 0. Extract structured facts directly from doc.structured_data
        for rec in doc.structured_data:
            rec_sp = str(rec.get("scientific_name", rec.get("species", ""))).strip().lower()
            if rec_sp and (species_name.lower() in rec_sp or rec_sp in species_name.lower()):
                page_val = rec.get("page")
                # CITES Appendix
                if rec.get("cites_annex"):
                    prov = SourceProvenance(
                        source_id=doc.source_id,
                        filename=doc.filename,
                        page=page_val,
                        extracted_text_snippet=f"CITES: {rec['cites_annex']}",
                    )
                    all_facts.append(
                        Fact(
                            fact_id=self._next_fact_id(),
                            category="conservation",
                            predicate="cites_appendix",
                            value=rec["cites_annex"],
                            sources=[doc.source_id],
                            provenance=[prov],
                        )
                    )
                # National Gabon Protection
                if rec.get("gabon_protection"):
                    prov = SourceProvenance(
                        source_id=doc.source_id,
                        filename=doc.filename,
                        page=page_val,
                        extracted_text_snippet=f"Protection Gabon: {rec['gabon_protection']}",
                    )
                    all_facts.append(
                        Fact(
                            fact_id=self._next_fact_id(),
                            category="conservation",
                            predicate="national_protection",
                            value=rec["gabon_protection"],
                            sources=[doc.source_id],
                            provenance=[prov],
                        )
                    )
                # Trade forms / exploitation threats
                if rec.get("trade_forms") and "aucun" not in rec.get("trade_forms", "").lower():
                    prov = SourceProvenance(
                        source_id=doc.source_id,
                        filename=doc.filename,
                        page=page_val,
                        extracted_text_snippet=f"Forme dans le commerce: {rec['trade_forms']}",
                    )
                    all_facts.append(
                        Fact(
                            fact_id=self._next_fact_id(),
                            category="conservation",
                            predicate="threats",
                            value=f"Commerce/Exploitation: {rec['trade_forms']}",
                            sources=[doc.source_id],
                            provenance=[prov],
                        )
                    )
                # IUCN Status
                if rec.get("iucn_status"):
                    prov = SourceProvenance(
                        source_id=doc.source_id,
                        filename=doc.filename,
                        page=page_val,
                        extracted_text_snippet=f"UICN: {rec['iucn_status']}",
                    )
                    all_facts.append(
                        Fact(
                            fact_id=self._next_fact_id(),
                            category="conservation",
                            predicate="iucn_status",
                            value=rec["iucn_status"],
                            sources=[doc.source_id],
                            provenance=[prov],
                        )
                    )

        # 1. Extract from sections
        for sec in doc.sections:
            if species_name.lower() in sec.content.lower() or len(doc.sections) == 1:
                f, o = self.extract_from_text(
                    sec.content,
                    species_name=species_name,
                    source_id=doc.source_id,
                    section_title=sec.title,
                )
                all_facts.extend(f)
                all_obs.extend(o)

        # 2. Extract from tables
        for tab in doc.tables:
            o = self.extract_from_table(tab, species_name=species_name, source_id=doc.source_id)
            all_obs.extend(o)

        # 3. Fallback extraction from raw text if nothing captured
        if not all_facts and not all_obs and doc.raw_text:
            f, o = self.extract_from_text(
                doc.raw_text,
                species_name=species_name,
                source_id=doc.source_id,
                section_title="General",
            )
            all_facts.extend(f)
            all_obs.extend(o)

        return all_facts, all_obs
