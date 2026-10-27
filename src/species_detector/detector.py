"""Species detection module finding scientific binomials, trinomials, and vernacular names."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models import InternalDocument

NON_SPECIES_WORDS = {
    "Table", "Figure", "Fig", "National", "Park", "Methods", "Results", "Discussion",
    "References", "Abstract", "Résumé", "Introduction", "Conclusion", "Study", "Area",
    "Central", "Africa", "African", "Gabon", "Lopé", "Ivindo", "Loango", "Minkébé",
    "Pongara", "Mayumba", "Moukalaba", "Doudou", "Plateaux", "Batéké", "Waka", "Birougou",
    "Mwagna", "Cristal", "Mountains", "Monts", "Mont", "Forest", "Reserve", "Sanctuary", "Protected",
    "University", "Department", "Ministry", "Direction", "Agence", "Nationale", "Parcs",
    "Nationaux", "ANPN", "IUCN", "WWF", "WCS", "CIRMF", "CENAREST", "INEF", "IRA",
    "January", "February", "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre", "Standard", "Deviation",
    "Mean", "Total", "Number", "Sample", "Size", "Significance", "Level", "Confidence", "Interval",
    "Camera", "Trap", "Line", "Transect", "GPS", "Coordinates", "Direct", "Sighting",
    "New", "York", "San", "Francisco", "Press", "Cambridge", "Oxford", "London", "Paris",
    "Springer", "Verlag", "Elsevier", "Wiley", "Blackwell", "Nature", "Science", "PloS",
    "One", "Volume", "Issue", "Pages", "Year", "Date", "Time", "Site", "Station",
    "General", "Specific", "High", "Low", "North", "South", "East", "West", "Zone",
    "Inhabits", "Consumes", "Feeds", "Eats", "Lives", "Found", "Observed", "Recorded",
    "Occurs", "Présent", "Présente", "Habite", "Vit", "Consomme", "Mange", "Nourrit",
    "Threatened", "Endangered", "Vulnerable", "Extinct", "Common", "Rare", "Primary",
    "Secondary", "Tropical", "Rainforest", "Lowland", "Montane", "Savanna", "Mangrove",
    "According", "Furthermore", "However", "Although", "Because", "Therefore", "Moreover",
    "Diet", "Habitat", "Population", "Conservation", "Threats", "Morphology", "Behavior",
    "Distribution", "Ecology", "Taxonomy", "Classification", "Overview", "Summary",
    "Total", "Count", "Observation", "Observations", "Individual", "Individuals", "Group", "Groups",
    "Dense", "Large", "Small", "Medium", "Global", "Local", "Regional", "International",
    "Menaces", "Principales", "Principale", "Principal", "Régime", "Alimentaire",
    "Statut", "Données", "Terrain", "Effectif", "Méthode", "Etude", "Étude", "Rapport",
    "Mammalia", "Aves", "Reptilia", "Amphibia", "Actinopterygii", "Insecta", "Arachnida",
    "Hominidae", "Cercopithecidae", "Elephantidae", "Felidae", "Bovidae", "Suidae",
    "Leatherback", "Sea", "Olive", "Ridley", "Giant", "Common", "Black", "Red", "Blue",
    # Legal, administrative, geographical and historical proper nouns
    "Cour", "Tribunal", "Conseil", "Chambre", "Commission", "Section", "Division",
    "Article", "Articles", "Loi", "Lois", "Décret", "Décrets", "Decret", "Decrets",
    "Arrêté", "Arrêtés", "Arrete", "Arretes", "Titre", "Titres", "Chapitre", "Chapitres",
    "Code", "Codes", "Constitution", "Convention", "Conventions", "Traité", "Traités",
    "Arrêt", "Arrêts", "Jugement", "Jugements", "Ordonnance", "Ordonnances", "Décision", "Décisions",
    "Procédure", "Procédures", "Peine", "Peines", "Infraction", "Infractions", "Mandat", "Mandats",
    "Avocat", "Avocats", "Juge", "Juges", "Procureur", "Procureurs", "Ministre", "Ministres",
    "Ministère", "Ministères", "Président", "Présidents", "Présidence", "Gouvernement", "Gouvernements",
    "République", "Républiques", "État", "États", "Etat", "Etats", "Administration", "Administrations",
    "Autorité", "Autorités", "Société", "Sociétés", "Banque", "Banques", "Caisse", "Caisses",
    "Office", "Offices", "Agence", "Agences", "Sénat", "Assemblée", "Parlement",
    "Premier", "Première", "Deuxième", "Troisième", "Dernier", "Dernière", "Grand", "Grande",
    "Haut", "Haute", "Nouveau", "Nouvelle", "Chaque", "Tout", "Toute", "Tous", "Toutes",
    "Autre", "Autres", "Certain", "Certains", "Certaines", "Plusieurs", "Selon", "Pendant",
    "Depuis", "Entre", "Dans", "Pour", "Avec", "Sans", "Sous", "Sur", "Vers", "Chez",
    "Comme", "Ainsi", "Aussi", "Cette", "Ces", "Cet", "Notre", "Votre", "Leur", "Leurs",
    "Histoire", "Historique", "Époque", "Période", "Siècle", "Année", "Années", "Mois", "Jour",
    "Ville", "Village", "Pays", "Province", "Provinces", "Région", "Régions", "Département",
    "Afrique", "France", "Europe", "Cameroun", "Congo", "Guinée", "Guinee", "Brazzaville",
    "Libreville", "Franceville", "Oyem", "Moanda", "Mouila", "Lambaréné", "Tchibanga", "Makokou",
    "Bantu", "Bantou", "Fang", "Punu", "Myene", "Kota", "Téké", "Nzebi", "Eshira",
    "Cassation", "Cotisation", "Accusation", "Appropriation", "Adoumas", "Adouma", "Aksoum",
    "Africus", "Afriques", "Angola", "Antilles", "Anthropos",
    # Technical, acoustic, and mathematical terms
    "Power", "Noise", "Minus", "Plus", "Acoustic", "Soundscape", "Index", "Indices",
    "Bandwidth", "Frequency", "Continuous", "Recording", "Signal", "Saturation",
    # General biological meta-words
    "Fauna", "Flora", "Faune", "Flore", "Taxon", "Taxa",
    # Non-French publication/citation words
    "Nacionais", "Para", "Nacional", "Parque", "Parques", "Sobre", "Tierbilder", "Aus",
    "Bilder", "Beitrag", "Beiträge", "Bericht", "Verlag", "Novorum", "Novarum",
    "Diagnoses", "Specierum", "Generum", "Descriptiones", "Vertebratorum", "Latin",
    "Nomen", "Nomina", "Revue", "Bulletin", "Journal",
}

FRENCH_COMMON_WORDS = {
    # Pronouns & articles
    "le", "la", "les", "un", "une", "des", "du", "au", "aux", "ce", "cet", "cette", "ces",
    "ceci", "cela", "celui", "celle", "ceux", "celles", "lui", "eux", "elle", "elles", "il", "ils",
    "nous", "vous", "on", "se", "sa", "son", "ses", "leur", "leurs", "notre", "nos", "votre", "vos",
    "mon", "ma", "mes", "ton", "ta", "tes", "qui", "que", "quoi", "dont", "où", "ou", "quand", "comment",
    # Prepositions & conjunctions
    "dans", "par", "pour", "avec", "sans", "sous", "sur", "vers", "chez", "contre", "entre",
    "depuis", "pendant", "selon", "malgré", "parmi", "hormis", "outre", "afin", "mais",
    "et", "donc", "or", "ni", "car", "ainsi", "aussi", "bien", "très", "plus", "moins", "trop",
    "peu", "tant", "comme", "lorsque", "puisque", "quoique", "si", "soit", "via",
    # Verbs & auxiliaries
    "est", "sont", "ont", "fait", "faite", "faits", "faites", "rendu", "rendue", "rendus", "rendues",
    "dit", "dite", "dits", "dites", "vu", "vue", "vus", "vues", "mis", "mise", "mises", "pris", "prise",
    "prises", "tenu", "tenue", "tenus", "tenues", "donné", "donnée", "donnés", "données",
    "ayant", "étant", "été", "sera", "seront", "serait", "seraient", "fut", "furent", "avait", "avaient",
    "peut", "peuvent", "doit", "doivent", "faut", "veut", "veulent", "sait", "savent",
    # Common adjectives & qualifiers
    "premier", "première", "deuxième", "troisième", "dernier", "dernière", "seul", "seule",
    "autre", "autres", "même", "mêmes", "tout", "tous", "toute", "toutes", "chaque", "aucun", "aucune",
    "grand", "grande", "grands", "grandes", "petit", "petite", "petits", "petites",
    "haut", "haute", "hauts", "hautes", "bas", "basse", "bons", "bonne", "bonnes",
    "nouveau", "nouvelle", "nouveaux", "nouvelles", "vieux", "vieille", "jeune", "jeunes",
    # Domain words (law, politics, admin, history, economy, society)
    "cour", "tribunal", "conseil", "chambre", "commission", "section", "division", "direction",
    "article", "loi", "lois", "décret", "decret", "décrets", "decrets", "arrêté", "arrete",
    "arrêtés", "arretes", "titre", "chapitre", "code", "codes", "constitution", "convention",
    "traité", "traite", "accord", "régime", "regime", "statut", "statuts", "arrêt", "arret",
    "jugement", "ordonnance", "décision", "decision", "procédure", "procedure", "peine", "peines",
    "infraction", "infractions", "mandat", "avocat", "juge", "procureur", "ministre", "ministère",
    "président", "president", "présidence", "presidence", "gouvernement", "république", "republique",
    "état", "etat", "états", "etats", "administration", "administrations", "autorité", "autorite",
    "société", "societe", "banque", "fonds", "caisse", "office", "agence", "agences",
    "public", "publique", "publiques", "publics", "privé", "privée", "privés", "privées",
    "civil", "civile", "civiles", "civils", "pénal", "penal", "pénale", "penale", "pénaux", "penaux",
    "social", "sociale", "sociales", "sociaux", "politique", "politiques", "juridique", "juridiques",
    "économique", "economique", "économiques", "economiques", "historique", "historiques",
    "culturel", "culturelle", "culturels", "culturelles", "colonial", "coloniale", "coloniaux",
    "constitutionnel", "constitutionnelle", "constitutionnels", "constitutionnelles",
    "national", "nationale", "nationaux", "nationales", "international", "internationale",
    "criminel", "criminelle", "criminels", "criminelles", "judiciaire", "judiciaires",
    "général", "general", "générale", "generale", "généraux", "generaux", "générales", "generales",
    "spécial", "special", "spéciale", "speciale", "spéciaux", "speciaux",
    "total", "totale", "totaux", "totales", "local", "locale", "locaux", "locales",
    "territorial", "territoriale", "territoriaux", "territoriales", "militaire", "militaires",
    "africain", "africaine", "africains", "africaines", "français", "française", "gabonais", "gabonaise",
    "histoire", "historique", "siècle", "siecle", "année", "annee", "années", "annees",
    "époque", "epoque", "période", "periode", "ville", "village", "pays", "province", "région", "region",
    "département", "departement", "canton", "district", "commune",
    "population", "peuple", "ethnie", "ethnies", "groupe", "groupes", "clan", "clans", "tribu", "tribus",
    "langue", "langues", "culture", "tradition", "traditions", "culte", "cassation", "cotisation",
    "accusation", "appropriation",
}

COMMON_NON_SPECIES_EPITHETS = {
    "forest", "forests", "forêt", "forêts", "ecosystem", "ecosystems", "écosystème", "écosystèmes",
    "individuals", "individus", "animals", "animaux", "specimens", "spécimens", "data", "results",
    "study", "studies", "area", "areas", "zone", "zones", "park", "parks", "parc", "parcs",
    "tree", "trees", "arbre", "arbres", "fruit", "fruits", "leaf", "leaves", "feuille", "feuilles",
    "type", "types", "level", "levels", "size", "sizes", "weight", "weights", "mass", "length",
    "distribution", "population", "habitat", "diet", "status", "conservation", "behavior",
    "year", "years", "month", "months", "day", "days", "time", "times", "site", "sites",
    "de", "du", "des", "le", "la", "les", "un", "une", "en", "au", "aux", "sur", "sous", "par",
    "pour", "dans", "avec", "sans", "est", "sont", "ont", "of", "in", "on", "at", "to", "for",
    "with", "from", "by", "as", "is", "are", "was", "were", "and", "or", "not", "an", "the",
    "principales", "principale", "tropical", "tropicale", "rainforest", "lowland", "montane",
    "class", "family", "order", "genus", "species", "classe", "famille", "ordre", "genre", "espèce",
    "troop", "group", "herd", "pack", "flock", "nest", "nests", "colony", "colonies",
    "sea", "ocean", "river", "lake", "swamp", "beach", "coastal", "marine",
    "qui", "que", "dont", "ainsi", "aussi", "via", "entre", "portugais", "fase",
}

INVALID_GENUS_SUFFIXES = (
    "tion", "sion", "ction", "xion", "gion", "ment", "teur", "teurs", "trice", "trices",
    "isme", "iste", "ence", "ance", "ière", "ier", "ique", "euse", "eur"
)

INVALID_EPITHET_SUFFIXES = (
    "tion", "sion", "ment", "ique", "iques", "able", "ables", "ible", "ibles",
    "aire", "aires", "ienne", "iennes", "elle", "elles", "iste", "istes", "isme", "ismes",
    "ante", "antes", "ente", "entes", "ière", "ières", "ier", "iers", "euse", "euses",
    "eux", "ois", "oise"
)

LATIN_GENUS_ENDINGS = (
    "us", "a", "um", "is", "es", "ix", "ex", "ox", "ax", "ys", "os", "as",
    "ia", "or", "ur", "er", "ops", "oides", "odon", "ius", "eus", "ina"
)

LATIN_EPITHET_ENDINGS = (
    "us", "a", "um", "is", "es", "ii", "ae", "ense", "ensis", "oides", "atus",
    "ata", "atum", "icus", "ica", "icum", "orus", "ora", "orum", "entis", "ans",
    "inus", "ina", "inum", "ellus", "ella", "ellum", "aster", "astris", "iana", "ianum",
    "ens", "ax", "ox", "ix", "ops", "yx", "coriacea", "olivacea", "tetraspis", "sebae",
    "estre", "ile", "ale", "forme", "oide", "er", "as", "ai", "ei", "oi", "ui",
    "goliath", "sphinx", "lepus", "aurita", "auritus", "batesi", "amnicola"
)


class DetectedSpeciesMention:
    def __init__(
        self,
        raw_name: str,
        matched_type: str,  # 'scientific_name', 'synonym', 'common_name_fr', 'common_name_en', 'structured_field'
        canonical_name: Optional[str] = None,
        confidence: float = 0.9,
        context_sentence: str = "",
        section_title: str = "",
        table_id: Optional[str] = None,
    ):
        self.raw_name = raw_name.strip()
        self.matched_type = matched_type
        self.canonical_name = canonical_name or self.raw_name
        self.confidence = confidence
        self.context_sentence = context_sentence.strip()
        self.section_title = section_title
        self.table_id = table_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_name": self.raw_name,
            "matched_type": self.matched_type,
            "canonical_name": self.canonical_name,
            "confidence": round(self.confidence, 4),
            "context_sentence": self.context_sentence[:200],
            "section_title": self.section_title,
            "table_id": self.table_id,
        }


class SpeciesDetector:
    """Discovers scientific names (binomials & trinomials) and common names in multi-format documents."""

    def __init__(self, taxonomy_file: Optional[str | Path] = None):
        self.reference_species: List[Dict[str, Any]] = []
        self.scientific_lookup: Dict[str, str] = {}
        self.synonym_lookup: Dict[str, str] = {}
        self.common_name_fr_lookup: Dict[str, str] = {}
        self.common_name_en_lookup: Dict[str, str] = {}

        self.binomial_regex = re.compile(
            r"\b([A-Z][a-z]{2,20})\s+([a-z]{2,25}(?:-[a-z]{2,20})?)(?:\s+([a-z]{2,25}))?\b"
        )

        tax_path = taxonomy_file or Path(__file__).resolve().parent.parent.parent / "resources" / "reference_taxonomy.json"
        if Path(tax_path).is_file():
            self.load_reference_taxonomy(tax_path)

    def load_reference_taxonomy(self, filepath: str | Path) -> None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.reference_species = data.get("species", [])
                for sp in self.reference_species:
                    sci = sp["scientific_name"]
                    self.scientific_lookup[sci.lower()] = sci

                    for syn in sp.get("synonyms", []):
                        self.synonym_lookup[syn.lower()] = sci

                    for fr_name in sp.get("common_names", {}).get("fr", []):
                        self.common_name_fr_lookup[fr_name.lower()] = sci

                    for en_name in sp.get("common_names", {}).get("en", []):
                        self.common_name_en_lookup[en_name.lower()] = sci
        except Exception as e:
            print(f"Warning loading taxonomy: {e}")

    def _is_valid_latin_candidate(self, genus: str, species: str, ssp: Optional[str] = None) -> bool:
        """Validates that an unseen candidate binomial matches Latin morphotaxonomic patterns."""
        g_low = genus.lower()
        s_low = species.lower()

        # Reject immediate stop words and non-species lists
        if genus in NON_SPECIES_WORDS or species in NON_SPECIES_WORDS:
            return False
        if g_low in NON_SPECIES_WORDS or s_low in NON_SPECIES_WORDS:
            return False
        if g_low in FRENCH_COMMON_WORDS or s_low in FRENCH_COMMON_WORDS:
            return False
        if s_low in COMMON_NON_SPECIES_EPITHETS or g_low in COMMON_NON_SPECIES_EPITHETS:
            return False
        if g_low in ("the", "this", "that", "there", "these", "those", "when", "where", "what", "with", "from"):
            return False
        if len(genus) < 3 or len(species) < 3:
            return False
        if species[0].isupper():
            return False
        if ssp and (ssp in NON_SPECIES_WORDS or ssp.lower() in COMMON_NON_SPECIES_EPITHETS or ssp.lower() in FRENCH_COMMON_WORDS):
            return False

        # Check invalid non-Latin suffixes
        if any(g_low.endswith(sfx) for sfx in INVALID_GENUS_SUFFIXES):
            return False
        if any(s_low.endswith(sfx) for sfx in INVALID_EPITHET_SUFFIXES):
            return False

        # Specific guard for words ending in 'i'
        if s_low.endswith("i") and len(s_low) <= 4 and s_low in ("qui", "ainsi", "midi", "ami", "loi", "foi", "soi", "mai", "oui"):
            return False

        # Check Latin endings for higher precision when candidate is unseen
        genus_ok = any(g_low.endswith(end) for end in LATIN_GENUS_ENDINGS)
        species_ok = any(s_low.endswith(end) for end in LATIN_EPITHET_ENDINGS)

        # Allow patronymic -i ending (e.g. batesi, spekii, carquejai) if length is substantial
        if not species_ok and s_low.endswith("i") and len(s_low) >= 5:
            species_ok = True

        return genus_ok and species_ok

    def detect_in_text(
        self,
        text: str,
        section_title: str = "",
        table_id: Optional[str] = None,
    ) -> List[DetectedSpeciesMention]:
        mentions: List[DetectedSpeciesMention] = []
        seen_keys: Set[str] = set()

        text_lower = text.lower()

        # 1. Check known reference species
        for sci_lower, canonical in self.scientific_lookup.items():
            if sci_lower in text_lower:
                pattern = re.compile(rf"\b{re.escape(sci_lower)}\b", re.IGNORECASE)
                for match in pattern.finditer(text):
                    start, end = match.span()
                    ctx = text[max(0, start - 100):min(len(text), end + 100)]
                    key = f"{canonical}:{start}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        mentions.append(
                            DetectedSpeciesMention(
                                raw_name=match.group(),
                                matched_type="scientific_name",
                                canonical_name=canonical,
                                confidence=0.99,
                                context_sentence=ctx,
                                section_title=section_title,
                                table_id=table_id,
                            )
                        )

        # 2. Check synonyms
        for syn_lower, canonical in self.synonym_lookup.items():
            if syn_lower in text_lower:
                pattern = re.compile(rf"\b{re.escape(syn_lower)}\b", re.IGNORECASE)
                for match in pattern.finditer(text):
                    start, end = match.span()
                    ctx = text[max(0, start - 100):min(len(text), end + 100)]
                    key = f"{canonical}:{start}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        mentions.append(
                            DetectedSpeciesMention(
                                raw_name=match.group(),
                                matched_type="synonym",
                                canonical_name=canonical,
                                confidence=0.96,
                                context_sentence=ctx,
                                section_title=section_title,
                                table_id=table_id,
                            )
                        )

        # 3. Check vernacular / common names (exact word boundaries only)
        for fr_name, canonical in self.common_name_fr_lookup.items():
            if fr_name in text_lower:
                pattern = re.compile(rf"\b{re.escape(fr_name)}\b", re.IGNORECASE)
                for match in pattern.finditer(text):
                    start, end = match.span()
                    ctx = text[max(0, start - 100):min(len(text), end + 100)]
                    key = f"{canonical}:{start}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        mentions.append(
                            DetectedSpeciesMention(
                                raw_name=match.group(),
                                matched_type="common_name_fr",
                                canonical_name=canonical,
                                confidence=0.92,
                                context_sentence=ctx,
                                section_title=section_title,
                                table_id=table_id,
                            )
                        )

        for en_name, canonical in self.common_name_en_lookup.items():
            if en_name in text_lower:
                pattern = re.compile(rf"\b{re.escape(en_name)}\b", re.IGNORECASE)
                for match in pattern.finditer(text):
                    start, end = match.span()
                    ctx = text[max(0, start - 100):min(len(text), end + 100)]
                    key = f"{canonical}:{start}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        mentions.append(
                            DetectedSpeciesMention(
                                raw_name=match.group(),
                                matched_type="common_name_en",
                                canonical_name=canonical,
                                confidence=0.92,
                                context_sentence=ctx,
                                section_title=section_title,
                                table_id=table_id,
                            )
                        )

        # 4. Extract unseen / new scientific binomials with strict Latin suffix validation
        for match in self.binomial_regex.finditer(text):
            genus, species, ssp = match.groups()
            if self._is_valid_latin_candidate(genus, species, ssp):
                raw_sci = f"{genus} {species}" + (f" {ssp}" if ssp else "")
                canonical = f"{genus} {species}"
                start, end = match.span()
                ctx = text[max(0, start - 100):min(len(text), end + 100)]
                key = f"{canonical}:{start}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    mentions.append(
                        DetectedSpeciesMention(
                            raw_name=raw_sci,
                            matched_type="scientific_name",
                            canonical_name=canonical,
                            confidence=0.88,
                            context_sentence=ctx,
                            section_title=section_title,
                            table_id=table_id,
                        )
                    )

        return mentions

    def detect_in_document(
        self,
        doc: InternalDocument,
        allow_freetext: bool = True,
    ) -> Dict[str, List[DetectedSpeciesMention]]:
        """Scans structured fields, tables, and optionally free text (sections, paragraphs, raw text) of an InternalDocument."""
        species_mentions: Dict[str, List[DetectedSpeciesMention]] = {}

        # 0. Check explicit structured keys in JSON / YAML / CSV records first
        for rec in doc.structured_data:
            for k in ("scientific_name", "species", "species_name", "taxon", "nom_scientifique"):
                if k in rec and isinstance(rec[k], str) and len(rec[k].strip()) > 3:
                    sp_val = rec[k].strip()
                    parts = sp_val.split()
                    if len(parts) >= 2 and parts[0].isalpha() and parts[1].isalpha():
                        g, s = parts[0], parts[1]
                        g_low, s_low = g.lower(), s.lower()
                        if (g_low not in FRENCH_COMMON_WORDS and s_low not in FRENCH_COMMON_WORDS and
                            g_low not in NON_SPECIES_WORDS and s_low not in NON_SPECIES_WORDS and
                            g_low not in COMMON_NON_SPECIES_EPITHETS and s_low not in COMMON_NON_SPECIES_EPITHETS and
                            len(g) >= 3 and len(s) >= 3):
                            canonical = self.scientific_lookup.get(sp_val.lower(), f"{g.capitalize()} {s.lower()}")
                            m = DetectedSpeciesMention(
                                raw_name=sp_val,
                                matched_type="structured_field",
                                canonical_name=canonical,
                                confidence=0.99,
                                context_sentence=str(rec),
                            )
                            species_mentions.setdefault(m.canonical_name, []).append(m)

        # 1. Scan tables for explicit taxonomic columns
        for tab in doc.tables:
            col_lower = [str(c).lower().strip() if c is not None else "" for c in tab.columns]

            genus_col = next((i for i, c in enumerate(col_lower) if c in ("genus", "genre")), None)
            species_col = next((i for i, c in enumerate(col_lower) if c in ("species", "espèce", "espece", "species_name")), None)

            if genus_col is not None and species_col is not None:
                unique_pairs = set()
                for r in tab.rows:
                    if genus_col < len(r) and species_col < len(r):
                        g_raw = str(r[genus_col]).strip() if r[genus_col] is not None else ""
                        s_raw = str(r[species_col]).strip() if r[species_col] is not None else ""
                        if g_raw and s_raw and s_raw.lower() not in ("unknown", "sp", "sp.", "spp", "spp.", "na", "nan", "none", "null", "indet", "unidentified"):
                            if g_raw.lower() not in ("unknown", "sp", "na", "nan", "none", "null", "indet", "unidentified"):
                                unique_pairs.add((g_raw, s_raw))
                                if len(unique_pairs) >= 2000:
                                    break
                for g_val, s_val in unique_pairs:
                    s_parts = s_val.split()
                    if len(s_parts) >= 2:
                        clean_g = s_parts[0]
                        clean_s = s_parts[1]
                    else:
                        g_parts = g_val.split()
                        clean_g = g_parts[0] if g_parts else g_val
                        clean_s = s_parts[0] if s_parts else s_val

                    clean_g = clean_g.capitalize()
                    clean_s = clean_s.lower()

                    if clean_s in ("unknown", "sp", "sp.", "spp", "spp.", "indet", "unidentified", "null", "none", "nan"):
                        continue
                    if clean_g.lower() == clean_s.lower() and clean_g.lower() != "gorilla":
                        continue

                    if len(clean_g) >= 3 and len(clean_s) >= 3 and clean_g.isalpha() and clean_s.isalpha():
                        g_low = clean_g.lower()
                        s_low = clean_s.lower()
                        if g_low not in NON_SPECIES_WORDS and s_low not in NON_SPECIES_WORDS and g_low not in FRENCH_COMMON_WORDS and s_low not in FRENCH_COMMON_WORDS:
                            if not any(g_low.endswith(x) for x in INVALID_GENUS_SUFFIXES) and not any(s_low.endswith(x) for x in INVALID_EPITHET_SUFFIXES):
                                canonical = f"{clean_g} {clean_s}"
                                canonical = self.scientific_lookup.get(canonical.lower(), canonical)
                                m = DetectedSpeciesMention(
                                    raw_name=f"{clean_g} {clean_s}",
                                    matched_type="structured_field",
                                    canonical_name=canonical,
                                    confidence=0.99,
                                    context_sentence=f"Table: {tab.table_id} | Genus: {clean_g}, Species: {clean_s}",
                                    table_id=tab.table_id,
                                )
                                species_mentions.setdefault(m.canonical_name, []).append(m)
            else:
                sp_col = next((i for i, c in enumerate(col_lower) if any(k in c for k in ["scientific_name", "nom_scientifique", "taxon", "species_name"])), None)
                if sp_col is not None:
                    unique_vals = set()
                    for r in tab.rows:
                        if sp_col < len(r) and r[sp_col] is not None and str(r[sp_col]).strip():
                            unique_vals.add(str(r[sp_col]).strip())
                            if len(unique_vals) >= 1000:
                                break
                    for val in unique_vals:
                        val_mentions = self.detect_in_text(val, table_id=tab.table_id)
                        for m in val_mentions:
                            species_mentions.setdefault(m.canonical_name, []).append(m)
                elif allow_freetext:
                    # Only scan arbitrary table cells if document is verified biodiversity
                    sample_rows = tab.rows[:200]
                    tab_cols_str = " ".join(str(c) for c in tab.columns if c is not None)
                    tab_rows_str = " ".join(" ".join(str(c) for c in r if c is not None) for r in sample_rows)
                    tab_text = tab_cols_str + " " + tab_rows_str
                    tab_mentions = self.detect_in_text(tab_text, table_id=tab.table_id)
                    for m in tab_mentions:
                        species_mentions.setdefault(m.canonical_name, []).append(m)

        # 2. Free-text scanning (strictly restricted to biodiversity documents)
        if allow_freetext:
            for sec in doc.sections:
                sec_mentions = self.detect_in_text(sec.content, section_title=sec.title)
                for m in sec_mentions:
                    species_mentions.setdefault(m.canonical_name, []).append(m)

            for p in doc.paragraphs:
                p_mentions = self.detect_in_text(p)
                for m in p_mentions:
                    species_mentions.setdefault(m.canonical_name, []).append(m)

            # Fallback to raw text if nothing captured yet
            if not species_mentions and doc.raw_text:
                raw_mentions = self.detect_in_text(doc.raw_text)
                for m in raw_mentions:
                    species_mentions.setdefault(m.canonical_name, []).append(m)

        return species_mentions
