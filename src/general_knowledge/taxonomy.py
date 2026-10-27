"""General-knowledge country model: category taxonomy and keyword maps.

The primary axis of the knowledge base is the COUNTRY. Each piece of knowledge is
then attached to one CATEGORY (and an optional subcategory). The taxonomy is open:
unknown categories can be created dynamically by the classifier.
"""

from __future__ import annotations

from typing import Dict, List

# category_id -> metadata (French label, English label, keywords FR/EN)
CATEGORIES: Dict[str, Dict] = {
    "droit": {
        "label_fr": "Droit et justice",
        "label_en": "Law and justice",
        "keywords": [
            "loi n", "code pénal", "code penal", "code civil", "code du travail", "constitution",
            "décret", "decret", "arrêté", "ordonnance", "article 1", "journal officiel",
            "tribunal", "juridiction", "procédure pénale", "infraction", "promulgue",
            "assemblée nationale", "sénat", "law", "court", "penal", "statute",
        ],
    },
    "gouvernance_politique": {
        "label_fr": "Gouvernance, politique et institutions",
        "label_en": "Governance, politics and institutions",
        "keywords": [
            "président de la république", "gouvernement", "premier ministre", "élection", "election",
            "parlement", "institutions", "souveraineté", "referendum", "référendum", "partis politiques",
            "governance", "corruption", "rule of law", "voice and accountability",
        ],
    },
    "administration": {
        "label_fr": "Administration et services publics",
        "label_en": "Public administration",
        "keywords": [
            "administration", "comptabilité publique", "fonction publique", "finances publiques",
            "budget de l'état", "trésor", "collectivités locales", "préfecture", "province",
            "département", "commune", "état civil", "passeport", "carte de séjour", "visa",
            "public sector", "civil service", "tax", "impôt",
        ],
    },
    "sante": {
        "label_fr": "Santé",
        "label_en": "Health",
        "keywords": [
            "santé", "sante", "health", "mortalité", "mortality", "paludisme", "malaria", "vih", "hiv",
            "vaccination", "immunization", "hôpital", "hospital", "nutrition", "maternelle", "maternal",
            "fécondité", "fertility", "espérance de vie", "life expectancy", "tuberculose", "tuberculosis",
            "dhs", "enquête démographique et de santé",
        ],
    },
    "demographie": {
        "label_fr": "Démographie et population",
        "label_en": "Demography and population",
        "keywords": [
            "population", "démographie", "demography", "recensement", "census", "naissances", "births",
            "migration", "urbanisation", "urban population", "rural population", "ménages", "households",
            "étrangers", "admission et de séjour",
        ],
    },
    "economie": {
        "label_fr": "Économie et finances",
        "label_en": "Economy and finance",
        "keywords": [
            "pib", "gdp", "gni", "inflation", "économie", "economy", "commerce", "trade", "exportations",
            "exports", "importations", "imports", "dette", "debt", "investissement", "investment",
            "fcfa", "us$", "banque", "bank", "croissance", "growth", "current account",
        ],
    },
    "education": {
        "label_fr": "Éducation",
        "label_en": "Education",
        "keywords": [
            "éducation", "education", "école", "school", "scolarisation", "enrollment", "enrolment",
            "alphabétisation", "literacy", "université", "university", "enseignement", "teachers",
            "primary completion", "tertiary",
        ],
    },
    "social": {
        "label_fr": "Société, travail et protection sociale",
        "label_en": "Society, labour and social protection",
        "keywords": [
            "protection sociale", "social protection", "sécurité sociale", "travail", "labor", "labour",
            "emploi", "employment", "chômage", "unemployment", "pauvreté", "poverty", "inégalités",
            "inequality", "gini", "enfant", "child", "femmes", "women", "gender", "genre", "famille",
            "retraite", "pension", "cnss", "cnamgs",
        ],
    },
    "environnement": {
        "label_fr": "Environnement et climat",
        "label_en": "Environment and climate",
        "keywords": [
            "environnement", "environment", "climat", "climate", "co2", "émissions", "emissions",
            "forêt", "forest", "déforestation", "pollution", "température", "temperature",
            "précipitations", "rainfall", "aires protégées", "protected areas", "exploitation forestière",
            "logging", "parcs nationaux",
        ],
    },
    "biodiversite": {
        "label_fr": "Biodiversité, faune et flore",
        "label_en": "Biodiversity, fauna and flora",
        "keywords": [
            "biodiversité", "biodiversity", "espèce", "species", "faune", "fauna", "flore", "flora",
            "amphibiens", "amphibians", "mammifères", "mammals", "oiseaux", "birds", "camera trap",
            "piège photographique", "genus", "taxon", "iucn", "uicn",
        ],
    },
    "energie_mines": {
        "label_fr": "Énergie, mines et hydrocarbures",
        "label_en": "Energy, mining and hydrocarbons",
        "keywords": [
            "hydrocarbures", "pétrole", "petroleum", "oil", "gaz", "gas", "énergie", "energy",
            "électricité", "electricity", "minier", "mining", "manganèse", "manganese", "renewable",
            "fossil fuel",
        ],
    },
    "infrastructures_transport": {
        "label_fr": "Infrastructures, transport et télécommunications",
        "label_en": "Infrastructure, transport and telecom",
        "keywords": [
            "aviation civile", "aéroport", "airport", "transport", "routes", "roads", "chemin de fer",
            "railway", "port", "télécommunications", "internet", "mobile cellular", "air transport",
            "infrastructure",
        ],
    },
    "agriculture": {
        "label_fr": "Agriculture, pêche et alimentation",
        "label_en": "Agriculture, fishing and food",
        "keywords": [
            "agriculture", "agricultural", "cultures", "crop", "élevage", "livestock", "pêche",
            "fisheries", "fishing", "alimentaire", "food", "cereal", "arable land",
        ],
    },
    "securite": {
        "label_fr": "Sécurité et défense",
        "label_en": "Security and defence",
        "keywords": [
            "sécurité", "security", "défense", "defense", "military", "armée", "police",
            "homicide", "conflict", "battle-related", "criminalité", "crime",
        ],
    },
    "geographie": {
        "label_fr": "Géographie et localisation",
        "label_en": "Geography and location",
        "keywords": [
            "géographie", "geography", "latitude", "longitude", "altitude", "elevation", "superficie",
            "land area", "surface area", "province", "libreville", "port-gentil", "franceville",
            "ogooué", "estuaire", "frontière", "border", "coordonnées", "coordinates",
        ],
    },
    "culture_tourisme": {
        "label_fr": "Culture, langues et tourisme",
        "label_en": "Culture, languages and tourism",
        "keywords": [
            "culture", "langue", "language", "tourisme", "tourism", "patrimoine", "heritage",
            "religion", "ethnie", "fang", "punu", "musique", "art",
        ],
    },
    "histoire": {
        "label_fr": "Histoire, personnalités et politique",
        "label_en": "History, public figures and politics",
        "keywords": [
            "histoire", "history", "président", "présidence", "coup d'état", "indépendance",
            "colonisation", "colonial", "époque", "siècle", "dynastie", "traité", "république",
            "léon mba", "omar bongo", "ali bongo", "oligui nguema", "aef", "afrique équatoriale",
            "fondation", "royaume", "biographie", "personnalité",
        ],
    },
    "general": {
        "label_fr": "Connaissances générales",
        "label_en": "General knowledge",
        "keywords": [],
    },
}

# Folder / filename hints (lower-case substring -> category). Checked before content keywords.
PATH_HINTS: List[tuple] = [
    ("histoire", "histoire"),
    ("history", "histoire"),
    ("constitution", "droit"),
    ("code-penal", "droit"),
    ("code_penal", "droit"),
    ("procedure-penale", "droit"),
    ("code_civil", "droit"),
    ("code-civil", "droit"),
    ("code-travail", "social"),
    ("protections-sociale", "social"),
    ("protection-sociale", "social"),
    ("code-de-lenfant", "social"),
    ("code-de-l'enfant", "social"),
    ("code-de-l'environnement", "environnement"),
    ("code-des-hydrocarbures", "energie_mines"),
    ("code-minier", "energie_mines"),
    ("aviation-civile", "infrastructures_transport"),
    ("comptabilit", "administration"),
    ("séjour des étrangers", "demographie"),
    ("démographique et de santé", "sante"),
    ("demographique et de sante", "sante"),
    ("enqu", "sante"),
    ("climate", "environnement"),
    ("climat", "environnement"),
    ("forêt", "environnement"),
    ("foret", "environnement"),
    ("forest", "environnement"),
    ("foresti", "environnement"),
    ("amphibi", "biodiversite"),
    ("mammif", "biodiversite"),
    ("soundscape", "biodiversite"),
    ("biodivers", "biodiversite"),
    ("droit", "droit"),
    ("lois", "droit"),
    ("codes", "droit"),
    ("sant", "sante"),
    ("econom", "economie"),
    ("educat", "education"),
    ("administ", "administration"),
]

# Legal subcategories (droit), detected from filename/title.
LEGAL_SUBCATEGORY_HINTS: List[tuple] = [
    ("constitution", "constitution"),
    ("procedure-penale", "procedure_penale"),
    ("procédure pénale", "procedure_penale"),
    ("code-penal", "code_penal"),
    ("code pénal", "code_penal"),
    ("code_civil", "code_civil"),
    ("code civil", "code_civil"),
    ("travail", "code_du_travail"),
    ("protections-sociale", "protection_sociale"),
    ("enfant", "code_de_l_enfant"),
    ("environnement", "code_de_l_environnement"),
    ("hydrocarbures", "code_des_hydrocarbures"),
    ("minier", "code_minier"),
    ("aviation", "code_de_l_aviation_civile"),
    ("comptabilit", "comptabilite_publique"),
    ("étrangers", "droit_des_etrangers"),
    ("etrangers", "droit_des_etrangers"),
    ("586", "droit_des_etrangers"),
]

# World Bank WDI indicator code prefix -> category.
WB_PREFIX_CATEGORY: Dict[str, str] = {
    "SP.POP": "demographie", "SP.URB": "demographie", "SP.RUR": "demographie", "SM.": "demographie",
    "SP.DYN.LE": "sante", "SP.DYN.IMRT": "sante", "SP.DYN.CDRT": "sante", "SP.DYN.CBRT": "demographie",
    "SP.DYN.TFRT": "demographie", "SP.ADO": "sante", "SP.REG": "administration", "SP.DYN": "demographie",
    "SH.": "sante", "SN.": "sante",
    "SE.": "education",
    "SL.": "social", "SI.": "social", "per_": "social", "SG.": "social",
    "NY.": "economie", "NE.": "economie", "NV.": "economie", "FP.": "economie", "FR.": "economie",
    "FM.": "economie", "FS.": "economie", "FB.": "economie", "FD.": "economie", "FX.": "economie",
    "BX.": "economie", "BM.": "economie", "BN.": "economie", "TX.": "economie", "TM.": "economie",
    "TG.": "economie", "DT.": "economie", "PA.": "economie", "PX.": "economie", "CM.": "economie",
    "BG.": "economie", "DC.": "economie", "FI.": "economie",
    "GC.": "administration", "IC.": "administration", "GB.": "economie",
    "EG.": "energie_mines", "EP.": "energie_mines",
    "EN.ATM": "environnement", "EN.CLC": "environnement", "EN.POP": "environnement",
    "EN.": "environnement", "ER.": "environnement", "CC.": "environnement",
    "AG.LND.FRST": "environnement", "AG.": "agriculture",
    "IS.": "infrastructures_transport", "IT.": "infrastructures_transport", "IE.": "infrastructures_transport",
    "VC.": "securite", "MS.": "securite",
    "ST.": "culture_tourisme",
    "IQ.": "administration",
}


def category_label(category: str, lang: str = "fr") -> str:
    meta = CATEGORIES.get(category)
    if not meta:
        return category.replace("_", " ").capitalize()
    return meta["label_fr"] if lang == "fr" else meta["label_en"]


def wb_indicator_category(indicator_code: str) -> str:
    """Longest-prefix match of a World Bank indicator code to a category."""
    best = ""
    best_cat = "general"
    for prefix, cat in WB_PREFIX_CATEGORY.items():
        if indicator_code.startswith(prefix) and len(prefix) > len(best):
            best, best_cat = prefix, cat
    return best_cat
