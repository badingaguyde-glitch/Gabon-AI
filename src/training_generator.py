"""Module generating multi-format training and fine-tuning datasets for AI / LLM models specialized in Gabon biodiversity and environmental law."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple

from src.models import SpeciesRecord


class TrainingDatasetGenerator:
    """Generates standardized AI model training datasets from the structured Gabon knowledge base."""

    def __init__(self, base_dir: str | Path = "."):
        self.base_dir = Path(base_dir)
        self.datasets_dir = self.base_dir / "datasets"
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_datasets(self) -> Dict[str, Path]:
        """Generates instruction-tuning (Chat & Alpaca), RAG chunks, Knowledge Graph triplets, and QA evaluation benchmarks."""
        output_paths: Dict[str, Path] = {}

        # 1. Load structured data
        all_species_file = self.base_dir / "all_species.json"
        all_laws_file = self.base_dir / "all_laws.json"

        species_list: List[Dict[str, Any]] = []
        laws_list: List[Dict[str, Any]] = []

        if all_species_file.exists():
            with open(all_species_file, "r", encoding="utf-8") as f:
                species_list = json.load(f).get("species", [])

        if all_laws_file.exists():
            with open(all_laws_file, "r", encoding="utf-8") as f:
                laws_list = json.load(f).get("laws", [])

        print(f"\n[DATASET GENERATOR] Preparing training datasets from {len(species_list)} species and {len(laws_list)} legal documents...")

        # 2. Build QA Pairs
        qa_pairs = self._build_qa_pairs(species_list, laws_list)

        # 3. Generate datasets/instruction_tuning_chat.jsonl (OpenAI / Llama-3 / Mistral format)
        chat_file = self.datasets_dir / "instruction_tuning_chat.jsonl"
        with open(chat_file, "w", encoding="utf-8") as f:
            for item in qa_pairs:
                chat_entry = {
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Vous êtes un assistant expert en écologie, biodiversité et droit de l'environnement "
                                "en République Gabonaise. Vos réponses sont rigoureuses, scientifiques et sourcées."
                            )
                        },
                        {"role": "user", "content": item["question"]},
                        {"role": "assistant", "content": item["answer"]}
                    ],
                    "metadata": item.get("metadata", {})
                }
                f.write(json.dumps(chat_entry, ensure_ascii=False) + "\n")
        output_paths["chat_format"] = chat_file

        # 4. Generate datasets/instruction_tuning_alpaca.jsonl (Alpaca / Instruction-Input-Output format)
        alpaca_file = self.datasets_dir / "instruction_tuning_alpaca.jsonl"
        with open(alpaca_file, "w", encoding="utf-8") as f:
            for item in qa_pairs:
                alpaca_entry = {
                    "instruction": item["question"],
                    "input": item.get("context", ""),
                    "output": item["answer"],
                    "category": item.get("category", "general")
                }
                f.write(json.dumps(alpaca_entry, ensure_ascii=False) + "\n")
        output_paths["alpaca_format"] = alpaca_file

        # 5. Generate datasets/rag_passages.jsonl (Dense chunks for RAG & embeddings)
        rag_passages_file = self.datasets_dir / "rag_passages.jsonl"
        self._generate_rag_passages(species_list, laws_list, rag_passages_file)
        output_paths["rag_passages"] = rag_passages_file

        # 6. Generate datasets/knowledge_graph_triplets.jsonl
        triplets_file = self.datasets_dir / "knowledge_graph_triplets.jsonl"
        self._generate_triplets(species_list, laws_list, triplets_file)
        output_paths["triplets"] = triplets_file

        # 7. Generate datasets/gabon_biodiversity_qa_benchmark.jsonl (Evaluation benchmark)
        eval_file = self.datasets_dir / "gabon_biodiversity_qa_benchmark.jsonl"
        with open(eval_file, "w", encoding="utf-8") as f:
            sample_eval = qa_pairs[:min(len(qa_pairs), 150)]
            for q in sample_eval:
                f.write(json.dumps(q, ensure_ascii=False) + "\n")
        output_paths["qa_benchmark"] = eval_file

        print(f"[DATASET GENERATOR] Generated {len(qa_pairs)} instruction examples and rich RAG/KG corpora in {self.datasets_dir}")
        return output_paths

    def _build_qa_pairs(
        self,
        species_list: List[Dict[str, Any]],
        laws_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        qa_pairs: List[Dict[str, Any]] = []

        # A. Species-based QA pairs
        for sp in species_list:
            sci_name = sp.get("scientific_name", "")
            cat = sp.get("category", "")
            fr_names = ", ".join(sp.get("common_names", {}).get("fr", []))
            en_names = ", ".join(sp.get("common_names", {}).get("en", []))
            tax = sp.get("taxonomy", {})
            tax_str = f"Classe: {tax.get('class', 'N/A')}, Ordre: {tax.get('order', 'N/A')}, Famille: {tax.get('family', 'N/A')}"
            iucn = sp.get("iucn_status") or "Non évalué"

            # 1. General Profile Question
            q1 = f"Présentez la fiche d'identité taxonomique et écologique de l'espèce {sci_name} au Gabon."
            a1 = (
                f"**Espèce** : *{sci_name}*\n"
                f"- **Noms vernaculaires français** : {fr_names or 'Non renseigné'}\n"
                f"- **Noms vernaculaires anglais** : {en_names or 'Non renseigné'}\n"
                f"- **Classification taxonomique** : {tax_str}\n"
                f"- **Catégorie biologique** : {cat.capitalize()}\n"
                f"- **Statut de conservation (UICN)** : {iucn}\n"
            )
            # Append facts if any
            facts = sp.get("facts", {})
            if "diet" in facts:
                d_val = facts["diet"].get("type", {}).get("value", "")
                if d_val:
                    a1 += f"- **Régime alimentaire** : {', '.join(d_val) if isinstance(d_val, list) else d_val}\n"
            if "habitat" in facts:
                h_val = facts["habitat"].get("type", {}).get("value", "")
                if h_val:
                    a1 += f"- **Habitat au Gabon** : {h_val}\n"

            obs_count = len(sp.get("observations", []))
            if obs_count > 0:
                a1 += f"- **Observations de terrain enregistrées** : {obs_count} observation(s) dans les parcs et concessions du Gabon.\n"

            qa_pairs.append({
                "question": q1,
                "answer": a1,
                "category": "species_profile",
                "species": sci_name,
                "metadata": {"species_id": sp.get("species_id"), "iucn_status": iucn}
            })

            # 2. IUCN Status QA
            if sp.get("iucn_status"):
                qa_pairs.append({
                    "question": f"Quel est le statut de conservation UICN de *{sci_name}* et où la trouve-t-on au Gabon ?",
                    "answer": f"L'espèce *{sci_name}* est classée avec le statut **{iucn}** sur la liste rouge de l'UICN. Elle est présente dans les écosystèmes forestiers et parcs nationaux du Gabon.",
                    "category": "conservation_status",
                    "species": sci_name,
                    "metadata": {"species_id": sp.get("species_id")}
                })

            # 3. Field observations QA
            obs_list = sp.get("observations", [])
            if obs_list:
                first_obs = obs_list[0]
                loc = first_obs.get("location") or first_obs.get("park_name") or "Gabon"
                yr = first_obs.get("year")
                cnt = first_obs.get("count")
                q_obs = f"Quelles sont les données d'observation de terrain disponibles pour *{sci_name}* au Gabon ?"
                a_obs = f"Pour *{sci_name}*, des inventaires scientifiques ont relevé des occurrences à **{loc}**"
                if yr:
                    a_obs += f" au cours de l'année {yr}"
                if cnt:
                    a_obs += f" avec un effectif recensé de {cnt} individu(s)"
                a_obs += f". Au total, {len(obs_list)} enregistrement(s) sont documentés."
                qa_pairs.append({
                    "question": q_obs,
                    "answer": a_obs,
                    "category": "field_observations",
                    "species": sci_name,
                    "metadata": {"species_id": sp.get("species_id")}
                })

        # B. Legal Framework & Environmental Law QA pairs
        for law in laws_list:
            law_num = law.get("law_number") or law.get("doc_id")
            title = law.get("title", "Législation gabonaise")
            sanctions = law.get("general_sanctions", [])
            articles = law.get("articles", [])

            # General law overview
            q_law = f"Quelle est la portée et l'objet de {law_num} : {title} au Gabon ?"
            a_law = (
                f"**Document** : {law_num}\n"
                f"**Intitulé** : {title}\n"
                f"**Dispositions** : Ce texte juridique comporte {len(articles)} articles régissant les normes environnementales, "
                f"la protection de la faune, la gestion durable des concessions forestières ou la gouvernance des parcs nationaux en République Gabonaise."
            )
            qa_pairs.append({
                "question": q_law,
                "answer": a_law,
                "category": "environmental_law",
                "metadata": {"doc_id": law.get("doc_id")}
            })

            # Penalties QA
            if sanctions:
                q_sanc = f"Quelles sont les sanctions et peines prévues par la législation gabonaise ({law_num}) en cas d'infraction ?"
                sanc_text = "\n".join(f"- {s}" for s in sanctions[:5])
                a_sanc = (
                    f"En vertu de {law_num} ({title}), les infractions relatives à la protection de la faune, "
                    f"au braconnage ou aux atteintes à l'environnement exposent aux sanctions suivantes :\n{sanc_text}"
                )
                qa_pairs.append({
                    "question": q_sanc,
                    "answer": a_sanc,
                    "category": "legal_sanctions",
                    "metadata": {"doc_id": law.get("doc_id")}
                })

            # Specific articles QA
            for art in articles[:10]:
                art_num = art.get("article_number")
                art_content = art.get("content", "").strip()
                if len(art_content) > 30:
                    qa_pairs.append({
                        "question": f"Que stipule l'{art_num} de {law_num} en droit gabonais ?",
                        "answer": f"L'{art_num} de {law_num} ({title}) dispose :\n\n> {art_content[:500]}",
                        "category": "legal_articles",
                        "metadata": {"doc_id": law.get("doc_id"), "article": art_num}
                    })

        return qa_pairs

    def _generate_rag_passages(
        self,
        species_list: List[Dict[str, Any]],
        laws_list: List[Dict[str, Any]],
        target_path: Path
    ) -> None:
        with open(target_path, "w", encoding="utf-8") as f:
            # Species passages
            for sp in species_list:
                sid = sp.get("species_id")
                sci = sp.get("scientific_name")
                common_fr = ", ".join(sp.get("common_names", {}).get("fr", []))
                common_en = ", ".join(sp.get("common_names", {}).get("en", []))
                tax = sp.get("taxonomy", {})
                tax_str = f"Classe: {tax.get('class', 'N/A')}, Ordre: {tax.get('order', 'N/A')}, Famille: {tax.get('family', 'N/A')}"
                iucn = sp.get("iucn_status", "Non évalué")

                facts = sp.get("facts", {})
                diet_str = facts.get("diet", {}).get("type", {}).get("value", "")
                habitat_str = facts.get("habitat", {}).get("type", {}).get("value", "")

                obs_summary = []
                for obs in sp.get("observations", [])[:10]:
                    loc = obs.get("location") or obs.get("park_name") or "Gabon"
                    yr = obs.get("year", "N/A")
                    cnt = obs.get("count", "N/A")
                    obs_summary.append(f"Observation à {loc} en {yr} (effectif: {cnt})")

                passage_text = (
                    f"Espèce : {sci}\n"
                    f"Noms usuels : {common_fr or 'N/A'} (FR) | {common_en or 'N/A'} (EN)\n"
                    f"Taxonomie : {tax_str}\n"
                    f"Statut UICN : {iucn}\n"
                    f"Régime : {diet_str or 'Non documenté'}\n"
                    f"Habitat au Gabon : {habitat_str or 'Forêts et parcs nationaux du Gabon'}\n"
                    f"Données d'observation :\n" + ("\n".join(f"- {o}" for o in obs_summary) if obs_summary else "Aucune observation de terrain.")
                )

                chunk = {
                    "chunk_id": f"CHUNK-{sid}",
                    "type": "species_entity",
                    "title": f"Profil Biodiversité - {sci}",
                    "content": passage_text,
                    "metadata": {
                        "species_id": sid,
                        "scientific_name": sci,
                        "category": sp.get("category"),
                        "iucn_status": iucn,
                        "sources": sp.get("sources", [])
                    }
                }
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

            # Legal passages
            for law in laws_list:
                did = law.get("doc_id")
                law_num = law.get("law_number") or did
                title = law.get("title", "")
                articles = law.get("articles", [])

                for idx, art in enumerate(articles, 1):
                    art_num = art.get("article_number", f"Art. {idx}")
                    content = art.get("content", "").strip()
                    if content:
                        chunk = {
                            "chunk_id": f"CHUNK-{did}-A{idx:03d}",
                            "type": "legal_article",
                            "title": f"{law_num} - {art_num}",
                            "content": f"Document : {law_num} ({title})\n{art_num} :\n{content}",
                            "metadata": {
                                "doc_id": did,
                                "law_number": law_num,
                                "article": art_num,
                                "topic": art.get("topic", "general"),
                                "source_id": law.get("source_id")
                            }
                        }
                        f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    def _generate_triplets(
        self,
        species_list: List[Dict[str, Any]],
        laws_list: List[Dict[str, Any]],
        target_path: Path
    ) -> None:
        with open(target_path, "w", encoding="utf-8") as f:
            for sp in species_list:
                sci = sp.get("scientific_name", "")
                cat = sp.get("category", "")
                tax = sp.get("taxonomy", {})
                iucn = sp.get("iucn_status")

                if cat:
                    f.write(json.dumps({"head": sci, "relation": "belongs_to_category", "tail": cat}, ensure_ascii=False) + "\n")
                if tax.get("class"):
                    f.write(json.dumps({"head": sci, "relation": "has_class", "tail": tax["class"]}, ensure_ascii=False) + "\n")
                if tax.get("order"):
                    f.write(json.dumps({"head": sci, "relation": "has_order", "tail": tax["order"]}, ensure_ascii=False) + "\n")
                if tax.get("family"):
                    f.write(json.dumps({"head": sci, "relation": "has_family", "tail": tax["family"]}, ensure_ascii=False) + "\n")
                if iucn:
                    f.write(json.dumps({"head": sci, "relation": "has_iucn_status", "tail": iucn}, ensure_ascii=False) + "\n")

                facts = sp.get("facts", {})
                if "habitat" in facts:
                    h_val = facts["habitat"].get("type", {}).get("value")
                    if h_val:
                        f.write(json.dumps({"head": sci, "relation": "inhabits", "tail": h_val}, ensure_ascii=False) + "\n")

                for obs in sp.get("observations", []):
                    loc = obs.get("location") or obs.get("park_name")
                    if loc:
                        f.write(json.dumps({"head": sci, "relation": "observed_in", "tail": loc}, ensure_ascii=False) + "\n")
