"""Training-data generator for a GENERAL-KNOWLEDGE model centred on a country.

Primary axis: country.  Secondary axis: category (droit, santé, économie, éducation, administration,
géographie, social, environnement, biodiversité, énergie, sécurité, ...).

Outputs (datasets/):
- sft_chat.jsonl              messages format (system/user/assistant) + metadata  -> SFT / instruction tuning
- sft_alpaca.jsonl            instruction / input / output                          -> Alpaca-style trainers
- splits/{train,validation,test}.jsonl  deterministic split of sft_chat
- pretraining_corpus.jsonl    clean long texts                                       -> continued pre-training
- rag_chunks.jsonl            self-contained passages with metadata                 -> embeddings / RAG
- kg_triplets.jsonl           (head, relation, tail) facts                           -> knowledge graph
- dataset_stats.json / dataset_card.md
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional

from src.general_knowledge.store import KnowledgeStore, slugify
from src.general_knowledge.taxonomy import category_label

# Natural French names for the most frequently asked indicators (others keep the WB English name).
INDICATOR_FR: Dict[str, str] = {
    "SP.POP.TOTL": "la population totale",
    "SP.POP.GROW": "le taux de croissance démographique annuel (%)",
    "SP.URB.TOTL.IN.ZS": "la part de la population urbaine (% de la population totale)",
    "SP.RUR.TOTL.ZS": "la part de la population rurale (% de la population totale)",
    "SP.POP.TOTL.FE.ZS": "la part des femmes dans la population (%)",
    "SP.POP.0014.TO.ZS": "la part des 0-14 ans dans la population (%)",
    "SP.POP.65UP.TO.ZS": "la part des 65 ans et plus dans la population (%)",
    "SP.DYN.LE00.IN": "l'espérance de vie à la naissance (années)",
    "SP.DYN.LE00.FE.IN": "l'espérance de vie à la naissance des femmes (années)",
    "SP.DYN.LE00.MA.IN": "l'espérance de vie à la naissance des hommes (années)",
    "SP.DYN.TFRT.IN": "l'indice synthétique de fécondité (naissances par femme)",
    "SP.DYN.CBRT.IN": "le taux brut de natalité (pour 1 000 habitants)",
    "SP.DYN.CDRT.IN": "le taux brut de mortalité (pour 1 000 habitants)",
    "SP.DYN.IMRT.IN": "le taux de mortalité infantile (pour 1 000 naissances vivantes)",
    "SH.DYN.MORT": "le taux de mortalité des moins de 5 ans (pour 1 000 naissances vivantes)",
    "SH.STA.MMRT": "le taux de mortalité maternelle (pour 100 000 naissances vivantes)",
    "SH.XPD.CHEX.GD.ZS": "les dépenses courantes de santé (% du PIB)",
    "SH.HIV.INCD.TL.P3": "l'incidence du VIH (pour 1 000 personnes non infectées)",
    "SH.MLR.INCD.P3": "l'incidence du paludisme (pour 1 000 personnes à risque)",
    "SH.IMM.MEAS": "la couverture vaccinale contre la rougeole (% des enfants de 12-23 mois)",
    "NY.GDP.MKTP.CD": "le PIB (en dollars US courants)",
    "NY.GDP.MKTP.KD.ZG": "le taux de croissance du PIB (% annuel)",
    "NY.GDP.PCAP.CD": "le PIB par habitant (en dollars US courants)",
    "NY.GNP.PCAP.CD": "le RNB par habitant, méthode Atlas (dollars US courants)",
    "FP.CPI.TOTL.ZG": "l'inflation, prix à la consommation (% annuel)",
    "NE.EXP.GNFS.ZS": "les exportations de biens et services (% du PIB)",
    "NE.IMP.GNFS.ZS": "les importations de biens et services (% du PIB)",
    "NV.AGR.TOTL.ZS": "la valeur ajoutée de l'agriculture, foresterie et pêche (% du PIB)",
    "NV.IND.TOTL.ZS": "la valeur ajoutée de l'industrie (% du PIB)",
    "NY.GDP.PETR.RT.ZS": "les rentes pétrolières (% du PIB)",
    "NY.GDP.FRST.RT.ZS": "les rentes forestières (% du PIB)",
    "BX.KLT.DINV.CD.WD": "les investissements directs étrangers, entrées nettes (dollars US courants)",
    "GC.DOD.TOTL.GD.ZS": "la dette de l'administration centrale (% du PIB)",
    "SL.UEM.TOTL.ZS": "le taux de chômage (% de la population active, estimation OIT)",
    "SL.UEM.1524.ZS": "le taux de chômage des jeunes de 15-24 ans (%)",
    "SL.TLF.TOTL.IN": "la population active totale",
    "SI.POV.GINI": "l'indice de Gini",
    "SI.POV.DDAY": "le taux de pauvreté à 2,15 $ par jour (% de la population)",
    "SE.PRM.ENRR": "le taux brut de scolarisation dans le primaire (%)",
    "SE.SEC.ENRR": "le taux brut de scolarisation dans le secondaire (%)",
    "SE.TER.ENRR": "le taux brut de scolarisation dans le supérieur (%)",
    "SE.ADT.LITR.ZS": "le taux d'alphabétisation des adultes (% des 15 ans et plus)",
    "SE.XPD.TOTL.GD.ZS": "les dépenses publiques d'éducation (% du PIB)",
    "EG.ELC.ACCS.ZS": "l'accès à l'électricité (% de la population)",
    "EG.ELC.ACCS.RU.ZS": "l'accès à l'électricité en milieu rural (% de la population rurale)",
    "EG.FEC.RNEW.ZS": "la part des énergies renouvelables dans la consommation finale d'énergie (%)",
    "AG.LND.FRST.ZS": "la superficie forestière (% du territoire)",
    "AG.LND.FRST.K2": "la superficie forestière (km²)",
    "AG.LND.TOTL.K2": "la superficie terrestre (km²)",
    "AG.SRF.TOTL.K2": "la superficie totale (km²)",
    "AG.LND.AGRI.ZS": "la superficie agricole (% du territoire)",
    "EN.POP.DNST": "la densité de population (habitants par km²)",
    "ER.LND.PTLD.ZS": "les aires protégées terrestres (% du territoire)",
    "ER.MRN.PTMR.ZS": "les aires marines protégées (% des eaux territoriales)",
    "IT.NET.USER.ZS": "la part de la population utilisant Internet (%)",
    "IT.CEL.SETS.P2": "les abonnements à la téléphonie mobile (pour 100 habitants)",
    "SH.H2O.BASW.ZS": "l'accès à un service d'eau potable de base (% de la population)",
    "SH.STA.BASS.ZS": "l'accès à un service d'assainissement de base (% de la population)",
    "MS.MIL.XPND.GD.ZS": "les dépenses militaires (% du PIB)",
    "VC.IHR.PSRC.P5": "le taux d'homicides volontaires (pour 100 000 habitants)",
    "ST.INT.ARVL": "le nombre d'arrivées de touristes internationaux",
}

PRIORITY_PREFIXES = tuple(INDICATOR_FR.keys())


def fmt_number(v: float, lang: str = "fr") -> str:
    a = abs(v)
    if lang == "fr":
        if a >= 1e9:
            return f"{v / 1e9:,.2f} milliards".replace(",", " ").replace(".", ",")
        if a >= 1e6:
            return f"{v / 1e6:,.2f} millions".replace(",", " ").replace(".", ",")
        if float(v).is_integer():
            return f"{int(v):,}".replace(",", " ")
        return f"{v:,.2f}".replace(",", " ").replace(".", ",")
    if a >= 1e9:
        return f"{v / 1e9:,.2f} billion"
    if a >= 1e6:
        return f"{v / 1e6:,.2f} million"
    return f"{int(v):,}" if float(v).is_integer() else f"{v:,.2f}"


def stable_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


class CountryTrainingDatasetGenerator:
    def __init__(self, base_dir: str | Path = ".", max_values_per_indicator: int = 10,
                 languages: Iterable[str] = ("fr", "en")):
        self.base_dir = Path(base_dir)
        self.out = self.base_dir / "datasets"
        self.out.mkdir(parents=True, exist_ok=True)
        self.store = KnowledgeStore(self.base_dir)
        self.max_values = max_values_per_indicator
        self.languages = set(languages)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def system_prompt(country: str, lang: str = "fr") -> str:
        if lang == "en":
            return (f"You are a general-knowledge assistant specialised in {country}. You answer questions on "
                    f"any topic about the country (law, health, economy, education, administration, geography, "
                    f"society, environment, biodiversity, energy, security, culture...) accurately, citing years "
                    f"and sources when available.")
        return (f"Tu es un assistant de connaissances générales spécialisé sur le pays : {country}. Tu réponds à "
                f"toute question concernant ce pays, quelle que soit la catégorie (droit, santé, économie, "
                f"éducation, administration, géographie, société, environnement, biodiversité, énergie, "
                f"sécurité, culture...), de façon exacte et en précisant les années et les sources lorsqu'elles "
                f"sont disponibles.")

    def _sample(self, country: str, category: str, subcategory: Optional[str], qtype: str, question: str,
                answer: str, source: Dict[str, Any], lang: str = "fr", context: str = "") -> Dict[str, Any]:
        return {
            "id": stable_id(country, category, qtype, question),
            "country": country, "category": category, "category_label": category_label(category, lang),
            "subcategory": subcategory, "question_type": qtype, "language": lang,
            "question": question.strip(), "answer": answer.strip(), "context": context, "source": source,
        }

    # ------------------------------------------------------------------ indicators
    def _indicator_samples(self, country: str, ind: Dict[str, Any]) -> List[Dict[str, Any]]:
        code = ind["indicator_code"]
        name_en = ind["indicator_name"]
        cat = ind["category"]
        name_fr = INDICATOR_FR.get(code)
        label_fr = name_fr or f"l'indicateur « {name_en} »"
        values = {int(y): v["value"] for y, v in ind["values"].items()}
        if not values:
            return []
        years = sorted(values)
        src = {"type": "indicator", "dataset": ind.get("source_dataset"), "indicator_code": code}
        out: List[Dict[str, Any]] = []

        chosen = {years[0], years[-1]} | set(years[-4:]) | {y for y in years if y % 5 == 0}
        chosen = sorted(chosen, reverse=True)[: self.max_values if code not in INDICATOR_FR else self.max_values * 3]

        for y in chosen:
            v = values[y]
            q = f"Quelle était la valeur de {label_fr} au {country} en {y} ?" if name_fr is None else \
                f"Quelle était {label_fr} au {country} en {y} ?"
            a = (f"En {y}, {label_fr} au {country} était de {fmt_number(v)}"
                 f"{'' if name_fr else ''}. (Indicateur : {name_en} ; source : {ind.get('source_dataset')}.)")
            out.append(self._sample(country, cat, code, "indicator_value", q, a, {**src, "year": y}))
            if "en" in self.languages and y == years[-1]:
                out.append(self._sample(
                    country, cat, code, "indicator_value",
                    f"What was the value of '{name_en}' in {country} in {y}?",
                    f"In {y}, '{name_en}' in {country} was {fmt_number(v, 'en')} (source: {ind.get('source_dataset')}).",
                    {**src, "year": y}, lang="en"))

        # latest value question (no year given)
        yl = years[-1]
        out.append(self._sample(
            country, cat, code, "indicator_latest",
            f"Quelle est la donnée la plus récente disponible pour {label_fr} au {country} ?",
            f"La donnée la plus récente concerne l'année {yl} : {fmt_number(values[yl])}. "
            f"(Indicateur : {name_en} ; source : {ind.get('source_dataset')}.)", {**src, "year": yl}))

        # trend
        if len(years) >= 3:
            y0, y1 = years[0], years[-1]
            v0, v1 = values[y0], values[y1]
            ymax = max(years, key=lambda y: values[y])
            ymin = min(years, key=lambda y: values[y])
            change = f" soit une variation de {((v1 - v0) / abs(v0) * 100):+.1f} %".replace(".", ",") if v0 else ""
            recent = ", ".join(f"{y} : {fmt_number(values[y])}" for y in years[-5:])
            a = (f"Au {country}, {label_fr} est passé(e) de {fmt_number(v0)} en {y0} à {fmt_number(v1)} en {y1}"
                 f"{change}. Le maximum observé est {fmt_number(values[ymax])} ({ymax}) et le minimum "
                 f"{fmt_number(values[ymin])} ({ymin}). Valeurs récentes — {recent}. "
                 f"(Source : {ind.get('source_dataset')}.)")
            out.append(self._sample(country, cat, code, "indicator_trend",
                                    f"Comment a évolué {label_fr} au {country} entre {y0} et {y1} ?", a, src))
            if "en" in self.languages:
                out.append(self._sample(
                    country, cat, code, "indicator_trend",
                    f"How has '{name_en}' evolved in {country} between {y0} and {y1}?",
                    f"In {country}, '{name_en}' went from {fmt_number(v0, 'en')} in {y0} to {fmt_number(v1, 'en')} "
                    f"in {y1}. Peak: {fmt_number(values[ymax], 'en')} ({ymax}); low: {fmt_number(values[ymin], 'en')} "
                    f"({ymin}). Source: {ind.get('source_dataset')}.", src, lang="en"))

        # definition
        d = self.store.definitions.get(code, {})
        if d.get("definition"):
            out.append(self._sample(
                country, cat, code, "indicator_definition",
                f"Que mesure l'indicateur « {name_en} » ({code}) ?",
                f"Définition (source : {d.get('source_organization') or 'Banque mondiale'}) : {d['definition']}",
                src))
        return out

    def _indicator_text(self, country: str, ind: Dict[str, Any]) -> str:
        values = {int(y): v["value"] for y, v in ind["values"].items()}
        series = "; ".join(f"{y} : {fmt_number(values[y])}" for y in sorted(values))
        name_fr = INDICATOR_FR.get(ind["indicator_code"])
        head = f"{country} — {ind['indicator_name']}"
        if name_fr:
            head += f" ({name_fr})"
        d = self.store.definitions.get(ind["indicator_code"], {}).get("definition", "")
        return (f"{head}. Catégorie : {category_label(ind['category'])}. Code : {ind['indicator_code']}. "
                f"Source : {ind.get('source_dataset')}.\n" + (f"Définition : {d}\n" if d else "") +
                f"Série annuelle : {series}.")

    # ------------------------------------------------------------------ documents
    def _legal_samples(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        country, title, sub = doc["country"], doc["title"], doc.get("subcategory")
        src_base = {"type": "document", "doc_id": doc["doc_id"], "files": doc.get("source_files", [])}
        out = []
        chunks = [c for c in doc["chunks"] if not c.get("duplicate_of")]
        contexts: List[str] = []
        for c in chunks:
            art, txt, ctx = c.get("article", ""), c["text"], c.get("context", "")
            if ctx and ctx not in contexts:
                contexts.append(ctx)
            src = {**src_base, "chunk_id": c["chunk_id"], "article": art}
            loc = f" ({ctx})" if ctx else ""
            if art.lower().startswith("article"):
                out.append(self._sample(country, "droit", sub, "legal_article",
                                        f"Que dispose l'{art.lower()} du texte « {title} » ({country}) ?",
                                        f"{art} — {title}{loc} :\n{txt}", src))
                excerpt = re.sub(r"\s+", " ", txt)[:260]
                if len(excerpt) > 80:
                    out.append(self._sample(country, "droit", sub, "legal_source_attribution",
                                            f"De quel texte juridique du {country} et de quel article provient la "
                                            f"disposition suivante : « {excerpt}… » ?",
                                            f"Cette disposition est extraite de l'{art.lower()} du texte « {title} »{loc}.",
                                            src))
            else:
                out.append(self._sample(country, "droit", sub, "legal_preamble",
                                        f"Que contiennent les dispositions introductives (préambule / visas) du texte "
                                        f"« {title} » ?", txt, src))
        n_art = sum(1 for c in chunks if c.get("article", "").lower().startswith("article"))
        if n_art:
            structure = "\n".join(f"- {c}" for c in contexts[:60]) or "- (pas de subdivision détectée)"
            out.append(self._sample(country, "droit", sub, "legal_structure",
                                    f"Comment est structuré le texte « {title} » ({country}) ?",
                                    f"Le texte « {title} » comporte {n_art} articles identifiés, organisés selon les "
                                    f"subdivisions suivantes :\n{structure}", src_base))
        return out

    def _survey_samples(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        out = []
        src_base = {"type": "document", "doc_id": doc["doc_id"], "files": doc.get("source_files", [])}
        cat = doc["category"]
        for c in doc["chunks"]:
            if c.get("duplicate_of"):
                continue
            sec = c.get("section") or "Informations générales"
            out.append(self._sample(doc["country"], cat, doc.get("subcategory"), "survey_metadata",
                                    f"Concernant « {doc['title']} » ({doc['country']}), que sait-on sur : "
                                    f"{sec.lower()} ?", c["text"], {**src_base, "chunk_id": c["chunk_id"]}))
        return out

    def _dataset_samples(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        out = []
        src = {"type": "dataset", "doc_id": doc["doc_id"], "files": doc.get("source_files", [])}
        country, cat = doc["country"], doc["category"]
        for c in doc["chunks"]:
            if c.get("duplicate_of"):
                continue
            out.append(self._sample(country, cat, doc.get("subcategory"), "dataset_description",
                                    f"Quelles données contient le jeu de données « {doc['title']} » ({country}) ?",
                                    c["text"], {**src, "chunk_id": c["chunk_id"]}))
        summ = doc.get("dataset_summary") or {}
        cols = summ.get("columns") or []
        if cols:
            out.append(self._sample(country, cat, doc.get("subcategory"), "dataset_variables",
                                    f"Quelles variables sont mesurées dans « {doc['title']} » ?",
                                    "Variables disponibles : " + ", ".join(cols[:60]) + ".", src))
        return out

    def _text_samples(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        out = []
        src_base = {"type": "document", "doc_id": doc["doc_id"], "files": doc.get("source_files", [])}
        for i, c in enumerate(doc["chunks"], 1):
            if c.get("duplicate_of"):
                continue
            sec = (c.get("section") or "").strip()
            if sec and sec.lower() not in ("tabular data", "general", "document"):
                q = f"Que dit le document « {doc['title']} » ({doc['country']}) au sujet de « {sec} » ?"
            else:
                q = (f"Que rapporte le document « {doc['title']} » sur le thème "
                     f"« {category_label(doc['category'])} » au {doc['country']} (extrait {i}) ?")
            out.append(self._sample(doc["country"], doc["category"], doc.get("subcategory"), "document_passage",
                                    q, c["text"], {**src_base, "chunk_id": c["chunk_id"]}))
        return out

    # ------------------------------------------------------------------ species (biodiversity category)
    def _species_samples(self) -> List[Dict[str, Any]]:
        path = self.base_dir / "all_species.json"
        if not path.exists():
            return []
        species = json.loads(path.read_text(encoding="utf-8")).get("species", [])
        out = []
        for sp in species:
            name = sp.get("scientific_name", "")
            tax = sp.get("taxonomy", {}) or {}
            cn = sp.get("common_names", {}) or {}
            obs = sp.get("observations", []) or []
            if not re.fullmatch(r"[A-Z][a-z]{2,} [a-z]{3,}( [a-z]{3,})?", name):
                continue
            if not (tax.get("family") or tax.get("class") or cn.get("fr") or cn.get("en") or obs):
                continue
            country = "Gabon"
            src = {"type": "species", "species_id": sp.get("species_id"), "sources": sp.get("sources", [])}
            lines = [f"*{name}*"]
            if cn.get("fr"):
                lines.append(f"Noms français : {', '.join(cn['fr'])}")
            if cn.get("en"):
                lines.append(f"Noms anglais : {', '.join(cn['en'])}")
            t = ", ".join(f"{k} : {v}" for k, v in tax.items() if v)
            if t:
                lines.append(f"Taxonomie : {t}")
            if sp.get("iucn_status"):
                lines.append(f"Statut UICN : {sp['iucn_status']}")
            for fcat, preds in (sp.get("facts") or {}).items():
                for pred, f in preds.items():
                    val = f.get("value")
                    if val:
                        lines.append(f"{fcat} ({pred}) : {', '.join(map(str, val)) if isinstance(val, list) else val}")
            locs = sorted({o.get("location") or o.get("park_name") for o in obs if (o.get("location") or o.get("park_name"))})
            if locs:
                lines.append(f"Observée au {country} : {', '.join(locs[:10])} ({len(obs)} observation(s))")
            out.append(self._sample(country, "biodiversite", sp.get("category"), "species_profile",
                                    f"Que sait-on de l'espèce {name} au {country} ?", "\n".join(lines), src))
            if cn.get("fr"):
                out.append(self._sample(country, "biodiversite", sp.get("category"), "species_name",
                                        f"Quel est le nom scientifique du {cn['fr'][0].lower()} ?",
                                        f"Le nom scientifique du {cn['fr'][0].lower()} est *{name}*.", src))
        return out

    # ------------------------------------------------------------------ main
    def generate(self) -> Dict[str, Any]:
        samples: List[Dict[str, Any]] = []
        rag: List[Dict[str, Any]] = []
        corpus: List[Dict[str, Any]] = []
        triplets: List[Dict[str, Any]] = []

        # Documents
        for doc in self.store.iter_documents():
            kind = doc["kind"]
            if kind == "legal_text":
                samples += self._legal_samples(doc)
            elif kind == "survey_metadata":
                samples += self._survey_samples(doc)
            elif kind == "dataset":
                samples += self._dataset_samples(doc)
            else:
                samples += self._text_samples(doc)

            uniq = [c for c in doc["chunks"] if not c.get("duplicate_of")]
            for c in uniq:
                header = f"[{doc['country']} | {category_label(doc['category'])}] {doc['title']}"
                if c.get("article"):
                    header += f" — {c['article']}" + (f" ({c['context']})" if c.get("context") else "")
                elif c.get("section"):
                    header += f" — {c['section']}"
                rag.append({"chunk_id": c["chunk_id"], "country": doc["country"], "category": doc["category"],
                            "subcategory": doc.get("subcategory"), "kind": kind, "title": doc["title"],
                            "text": f"{header}\n{c['text']}", "source_files": doc.get("source_files", [])})
            if uniq:
                full = "\n\n".join(
                    (f"{c['article']}. " if c.get("article") else (f"{c['section']}\n" if c.get("section") else "")) + c["text"]
                    for c in uniq)
                for k in range(0, len(full), 6000):
                    corpus.append({"country": doc["country"], "category": doc["category"], "doc_id": doc["doc_id"],
                                   "text": (f"{doc['title']} ({doc['country']})\n\n" if k == 0 else "") + full[k:k + 6000]})
            triplets.append({"head": doc["title"], "relation": "concerne_le_pays", "tail": doc["country"]})
            triplets.append({"head": doc["title"], "relation": "categorie", "tail": doc["category"]})
            if kind == "legal_text":
                for c in uniq:
                    if c.get("article", "").lower().startswith("article"):
                        triplets.append({"head": doc["title"], "relation": "contient_article", "tail": c["article"]})

        # Indicators
        for country_key, inds in self.store.all_indicators().items():
            for code, ind in inds.items():
                country = "Gabon" if country_key == "gabon" else country_key.replace("_", " ").title()
                samples += self._indicator_samples(country, ind)
                txt = self._indicator_text(country, ind)
                rag.append({"chunk_id": f"IND-{slugify(country)}-{code}", "country": country,
                            "category": ind["category"], "subcategory": code, "kind": "indicator",
                            "title": ind["indicator_name"], "text": txt, "source_files": [ind.get("source_dataset")]})
                corpus.append({"country": country, "category": ind["category"], "doc_id": code, "text": txt})
                for y, v in ind["values"].items():
                    triplets.append({"head": country, "relation": ind["indicator_name"], "tail": v["value"],
                                     "year": int(y), "category": ind["category"]})

        # Species (biodiversity category)
        samples += self._species_samples()

        # Deduplicate samples by id
        seen, uniq_samples = set(), []
        for s in samples:
            if s["id"] not in seen and len(s["answer"]) > 10:
                seen.add(s["id"])
                uniq_samples.append(s)
        samples = uniq_samples

        self._write_outputs(samples, rag, corpus, triplets)
        return self._write_stats(samples, rag, corpus, triplets)

    # ------------------------------------------------------------------ writers
    def _write_jsonl(self, path: Path, rows: Iterable[Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def _to_chat(self, s: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": s["id"],
            "messages": [
                {"role": "system", "content": self.system_prompt(s["country"], s["language"])},
                {"role": "user", "content": s["question"]},
                {"role": "assistant", "content": s["answer"]},
            ],
            "metadata": {k: s[k] for k in ("country", "category", "subcategory", "question_type", "language", "source")},
        }

    def _write_outputs(self, samples, rag, corpus, triplets) -> None:
        for old in ("instruction_tuning_chat.jsonl", "instruction_tuning_alpaca.jsonl", "rag_passages.jsonl",
                    "knowledge_graph_triplets.jsonl", "gabon_biodiversity_qa_benchmark.jsonl"):
            p = self.out / old
            if p.exists():
                p.unlink()
        chat = [self._to_chat(s) for s in samples]
        self._write_jsonl(self.out / "sft_chat.jsonl", chat)
        self._write_jsonl(self.out / "sft_alpaca.jsonl", (
            {"id": s["id"], "instruction": s["question"], "input": s["context"], "output": s["answer"],
             "country": s["country"], "category": s["category"], "subcategory": s["subcategory"],
             "question_type": s["question_type"], "language": s["language"]} for s in samples))
        # deterministic split: 90 / 5 / 5
        splits = defaultdict(list)
        for c in chat:
            b = int(c["id"], 16) % 100
            splits["train" if b < 90 else ("validation" if b < 95 else "test")].append(c)
        for name, rows in splits.items():
            self._write_jsonl(self.out / "splits" / f"{name}.jsonl", rows)
        self._write_jsonl(self.out / "rag_chunks.jsonl", rag)
        self._write_jsonl(self.out / "pretraining_corpus.jsonl", corpus)
        self._write_jsonl(self.out / "kg_triplets.jsonl", triplets)

    def _write_stats(self, samples, rag, corpus, triplets) -> Dict[str, Any]:
        by_country_cat: Dict[str, Counter] = defaultdict(Counter)
        for s in samples:
            by_country_cat[s["country"]][s["category"]] += 1
        stats = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sft_examples": len(samples),
            "rag_chunks": len(rag),
            "pretraining_documents": len(corpus),
            "pretraining_characters": sum(len(c["text"]) for c in corpus),
            "kg_triplets": len(triplets),
            "by_language": dict(Counter(s["language"] for s in samples)),
            "by_question_type": dict(Counter(s["question_type"] for s in samples).most_common()),
            "by_country_and_category": {c: dict(cnt.most_common()) for c, cnt in by_country_cat.items()},
        }
        (self.out / "dataset_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

        lines = ["# Dataset card — Modèle de connaissances générales par pays", "",
                 f"Généré le {stats['generated_at'][:19]} UTC.", "",
                 "Axe principal : **pays**. Axe secondaire : **catégorie** de question.", "",
                 "| Fichier | Usage | Volume |", "|---|---|---|",
                 f"| `sft_chat.jsonl` | Fine-tuning instructionnel (format messages) | {len(samples)} exemples |",
                 f"| `sft_alpaca.jsonl` | Fine-tuning format Alpaca | {len(samples)} exemples |",
                 "| `splits/` | train / validation / test (90/5/5, déterministe) | — |",
                 f"| `pretraining_corpus.jsonl` | Pré-entraînement continu | {len(corpus)} docs, {stats['pretraining_characters']:,} caractères |",
                 f"| `rag_chunks.jsonl` | Embeddings / RAG | {len(rag)} passages |",
                 f"| `kg_triplets.jsonl` | Graphe de connaissances | {len(triplets)} triplets |", ""]
        for country, cnt in stats["by_country_and_category"].items():
            lines += [f"## {country}", "", "| Catégorie | Exemples SFT |", "|---|---|"]
            lines += [f"| {category_label(cat)} (`{cat}`) | {n} |" for cat, n in cnt.items()]
            lines.append("")
        lines += ["## Types de questions", "", "| Type | Exemples |", "|---|---|"]
        lines += [f"| `{t}` | {n} |" for t, n in stats["by_question_type"].items()]
        (self.out / "dataset_card.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return stats
