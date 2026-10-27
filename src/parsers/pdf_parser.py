"""Scientific PDF parser with PyMuPDF (fitz) and pypdf fallback, extracting text, pages, metadata, and tables."""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Optional

from src.models import InternalDocument, DocumentSection, TableData
from src.parsers.base_parser import BaseParser, detect_text_language


class PdfParser(BaseParser):
    name = "pdf_parser"
    supported_formats = ["pdf"]

    def _parse_with_fitz(self, file_path: Path, source_id: str) -> InternalDocument:
        import fitz  # PyMuPDF

        doc_obj = fitz.open(file_path)

        # Check if PDF is the CITES Guide (Gabon_species.pdf)
        first_pages_text = "".join(doc_obj[p].get_text("text") for p in range(min(4, len(doc_obj)))).lower()
        if "cites" in file_path.name.lower() or "gabon_species" in file_path.name.lower() or "convention cites" in first_pages_text:
            return self._parse_cites_guide(doc_obj, file_path, source_id)

        doc = self.create_empty_doc(file_path, source_id, "pdf", encoding="utf-8")

        pdf_meta = doc_obj.metadata or {}
        doc.document_metadata.update({
            "title": pdf_meta.get("title"),
            "author": pdf_meta.get("author"),
            "subject": pdf_meta.get("subject"),
            "keywords": pdf_meta.get("keywords"),
            "page_count": len(doc_obj),
        })

        full_text_pages = []
        sections: List[DocumentSection] = []
        tables: List[TableData] = []
        table_idx = 1

        for page_idx, page in enumerate(doc_obj, start=1):
            page_text = page.get_text("text")
            full_text_pages.append(f"--- [Page {page_idx}] ---\n{page_text}")

            # Try extracting tables if page text suggests tabular data
            if len(doc_obj) <= 30 or any(kw in page_text.lower() for kw in ("table", "tableau", "%", "n=")):
                try:
                    tabs = page.find_tables()
                    for tab in tabs:
                        headers = tab.header.names if tab.header and tab.header.names else []
                        rows = tab.extract()
                        # Clean rows
                        clean_rows = []
                        for row in rows:
                            clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                            if any(c for c in clean_row):
                                clean_rows.append(clean_row)
                        if clean_rows:
                            if not headers and clean_rows:
                                headers = [f"col_{i+1}" for i in range(len(clean_rows[0]))]
                            tables.append(
                                TableData(
                                    table_id=f"TABLE-{table_idx:03d}",
                                    columns=headers,
                                    rows=clean_rows,
                                    source_id=source_id,
                                    page=page_idx,
                                )
                            )
                            table_idx += 1
                except Exception:
                    pass

        doc.raw_text = "\n\n".join(full_text_pages)
        doc.tables = tables

        # Split text into paragraphs
        doc.paragraphs = [
            p.strip() for p in re.split(r"\n\s*\n", doc.raw_text) if p.strip() and not p.strip().startswith("--- [Page")
        ]

        # Structure into sections (e.g. by looking for common scientific headers)
        sections = self._extract_scientific_sections(doc.raw_text)
        doc.sections = sections

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        doc_obj.close()
        return doc

    def _parse_with_pypdf(self, file_path: Path, source_id: str) -> InternalDocument:
        import pypdf

        reader = pypdf.PdfReader(str(file_path))
        doc = self.create_empty_doc(file_path, source_id, "pdf", encoding="utf-8")

        pdf_meta = reader.metadata or {}
        doc.document_metadata.update({
            "title": str(pdf_meta.get("/Title", "")),
            "author": str(pdf_meta.get("/Author", "")),
            "page_count": len(reader.pages),
        })

        full_text_pages = []
        for page_idx, page in enumerate(reader.pages, start=1):
            try:
                t = page.extract_text() or ""
                full_text_pages.append(f"--- [Page {page_idx}] ---\n{t}")
            except Exception as e:
                doc.parsing_warnings.append(f"Failed extracting text on page {page_idx}: {e}")

        doc.raw_text = "\n\n".join(full_text_pages)
        doc.paragraphs = [
            p.strip() for p in re.split(r"\n\s*\n", doc.raw_text) if p.strip() and not p.strip().startswith("--- [Page")
        ]
        doc.sections = self._extract_scientific_sections(doc.raw_text)

        lang, conf = detect_text_language(doc.raw_text)
        doc.language = lang
        doc.language_confidence = conf

        return doc

    def _extract_scientific_sections(self, text: str) -> List[DocumentSection]:
        sections: List[DocumentSection] = []
        pattern = re.compile(
            r"^(?:[0-9]+\.?\s*)?(ABSTRACT|RÉSUMÉ|INTRODUCTION|METHODS?|MÉTHODES|RESULTS?|RÉSULTATS|DISCUSSION|CONCLUSION|HABITAT|DIET|POPULATION|CONSERVATION|REFERENCES?|BIBLIOGRAPHY)\b",
            re.IGNORECASE | re.MULTILINE
        )

        matches = list(pattern.finditer(text))
        if not matches:
            return [DocumentSection(title="Body", level=1, content=text)]

        for i, match in enumerate(matches):
            title = match.group(1).capitalize()
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start_pos:end_pos].strip()
            sections.append(DocumentSection(title=title, level=1, content=content))

        return sections

    def _parse_cites_guide(self, doc_obj, file_path: Path, source_id: str) -> InternalDocument:
        doc = self.create_empty_doc(file_path, source_id, "pdf", encoding="utf-8")
        doc.document_metadata.update({
            "title": "Guide d'identification des espèces de faune gabonaise inscrites à la convention CITES (2012)",
            "author": "Alice Stroud, DGFAP, Ministère des Eaux et Forêts",
            "subject": "Faune et réglementation CITES au Gabon",
            "page_count": len(doc_obj),
            "is_cites_guide": True,
        })

        PAGE_CLASSES = {
            15: ("Mammalia", "mammals"),
            16: ("Mammalia", "mammals"),
            17: ("Mammalia", "mammals"),
            18: ("Mammalia", "mammals"),
            19: ("Mammalia", "mammals"),
            20: ("Mammalia", "mammals"),
            21: ("Mammalia", "mammals"),
            22: ("Mammalia", "mammals"),
            23: ("Mammalia", "mammals"),
            24: ("Mammalia", "mammals"),
            25: ("Aves", "birds"),
            26: ("Aves", "birds"),
            27: ("Aves", "birds"),
            28: ("Aves", "birds"),
            29: ("Reptilia", "reptiles"),
            30: ("Reptilia", "reptiles"),
            31: ("Reptilia", "reptiles"),
            32: ("Reptilia", "reptiles"),
            33: ("Amphibia", "amphibians"),
            34: ("Elasmobranchii", "fish"),
            35: ("Anthozoa", "corals"),
            36: ("Arachnida", "arachnids"),
            37: ("Liliopsida", "plants"),
            38: ("Liliopsida", "plants"),
        }

        STOP_GENERA = {
            "garden", "botanic", "national", "museum", "source", "photo", "image",
            "picture", "figure", "table", "espèce", "classe", "annexe", "forme",
            "animaux", "aucun", "gabon", "france", "oiseaux", "corps", "page",
            "western", "golden", "allen", "african", "congo", "grey", "black"
        }

        STOP_EPITHETS = {
            "of", "in", "on", "the", "at", "by", "to", "for", "with", "from",
            "and", "de", "du", "des", "le", "la", "les", "au", "aux", "par",
            "sur", "sous", "dans", "sans", "avec", "est", "sont", "ont"
        }

        full_text_pages = []
        sections: List[DocumentSection] = []
        structured_data: List[Dict[str, Any]] = []

        # 1. Front matter (pages 1-4)
        for pno in range(min(4, len(doc_obj))):
            t = doc_obj[pno].get_text("text").strip()
            full_text_pages.append(f"--- [Page {pno + 1}] ---\n{t}")

        # 2. Extract Regulatory Sections (Pages 5 to 14)
        sec1_text = "\n\n".join(
            re.sub(r"[\uf000-\uf0ff]", "-", doc_obj[p].get_text("text").strip())
            for p in range(4, min(7, len(doc_obj)))
        )
        sections.append(DocumentSection(
            title="Introduction à la CITES et fonctionnement des Annexes I, II et III",
            level=1,
            content=sec1_text,
            page_start=5,
            page_end=7,
        ))

        if len(doc_obj) >= 8:
            sec2_text = re.sub(r"[\uf000-\uf0ff]", "-", doc_obj[7].get_text("text").strip())
            sections.append(DocumentSection(
                title="Informations Sommaires sur la Liste Rouge Mondiale des Espèces Menacées de l'UICN",
                level=1,
                content=sec2_text,
                page_start=8,
                page_end=8,
            ))

        if len(doc_obj) >= 9:
            sec3_text = re.sub(r"[\uf000-\uf0ff]", "-", doc_obj[8].get_text("text").strip())
            sections.append(DocumentSection(
                title="Résumé de la Réglementation Applicable et Autorités CITES au Gabon",
                level=1,
                content=sec3_text,
                page_start=9,
                page_end=9,
            ))

        if len(doc_obj) >= 12:
            sec4_text = "\n\n".join(
                re.sub(r"[\uf000-\uf0ff]", "-", doc_obj[p].get_text("text").strip())
                for p in range(9, min(12, len(doc_obj)))
            )
            sections.append(DocumentSection(
                title="Dispositions conventionnelles CITES (Articles III et IV) : Exportation, Importation et Permis",
                level=1,
                content=sec4_text,
                page_start=10,
                page_end=12,
            ))

        if len(doc_obj) >= 14:
            sec5_text = re.sub(r"[\uf000-\uf0ff]", "-", doc_obj[13].get_text("text").strip())
            sections.append(DocumentSection(
                title="Étapes du Contrôle et Procédures de Vérification des Permis CITES au Gabon",
                level=1,
                content=sec5_text,
                page_start=14,
                page_end=14,
            ))

        for pno in range(4, min(14, len(doc_obj))):
            t = doc_obj[pno].get_text("text").strip()
            full_text_pages.append(f"--- [Page {pno + 1}] ---\n{t}")

        # 3. Extract Species Cards Grid (Pages 15 to 38)
        col_bounds = [(0, 205), (205, 390), (390, 575), (575, 792)]
        for pno in range(14, min(38, len(doc_obj))):
            page_num = pno + 1
            page = doc_obj[pno]
            words = page.get_text("words")
            banner_cls, banner_cat = PAGE_CLASSES.get(page_num, (None, None))
            page_text_lines = []

            for r_idx, (y_min, y_max) in enumerate([(35, 295), (295, 565)]):
                for c_idx, (x_min, x_max) in enumerate(col_bounds):
                    card_words = []
                    for w in words:
                        x0, y0, x1, y1, word_str, bno, lno, wno = w
                        cx = (x0 + x1) / 2
                        cy = (y0 + y1) / 2
                        if x_min <= cx < x_max and y_min <= cy < y_max:
                            card_words.append((y0, x0, word_str))

                    if not card_words:
                        continue

                    lines_dict = {}
                    for y, x, w_str in card_words:
                        line_key = round(y / 4) * 4
                        lines_dict.setdefault(line_key, []).append(w_str)

                    sorted_line_keys = sorted(lines_dict.keys())
                    full_card_text = "\n".join([" ".join(lines_dict[k]) for k in sorted_line_keys])
                    full_card_text = re.sub(r"[\uf000-\uf0ff]", "-", full_card_text)

                    if not any(k in full_card_text.lower() for k in ["cites", "nom :", "forme dans le commerce", "uicn"]):
                        continue

                    # Attributes
                    gabon_protection = None
                    if "intégralement" in full_card_text.lower() and "protégée" in full_card_text.lower():
                        gabon_protection = "Intégralement protégée au Gabon"
                    elif "partiellement" in full_card_text.lower() and "protégée" in full_card_text.lower():
                        gabon_protection = "Partiellement protégée au Gabon"

                    cites_annex = None
                    m_cites = re.search(r"CITES\s+Annexe\s+([I|V|X]+)", full_card_text, re.IGNORECASE)
                    if m_cites:
                        cites_annex = f"Annexe {m_cites.group(1).upper()}"

                    iucn_status = None
                    m_iucn = re.search(r"UICN\s*:\s*([^\n\r]+)", full_card_text, re.IGNORECASE)
                    if m_iucn:
                        raw_st = m_iucn.group(1).strip()
                        st_low = raw_st.lower()
                        if "critique" in st_low:
                            iucn_status = "CR"
                        elif "en danger" in st_low:
                            iucn_status = "EN"
                        elif "vulnérable" in st_low or "vulnerable" in st_low:
                            iucn_status = "VU"
                        elif "quasi" in st_low:
                            iucn_status = "NT"
                        elif "préoccupation mineure" in st_low or "preoccupation" in st_low:
                            iucn_status = "LC"
                        elif "données insuffisantes" in st_low or "insuffisante" in st_low:
                            iucn_status = "DD"
                        elif "non évalué" in st_low or "non evalue" in st_low:
                            iucn_status = "NE"
                        else:
                            iucn_status = raw_st

                    common_name_fr = None
                    common_name_en = None
                    m_fr = re.search(r"Nom\s*:\s*([^(\n\r]+?)(?:\s*\(FR\)|\s*\(AN\)|\n|$)", full_card_text, re.IGNORECASE)
                    if m_fr:
                        common_name_fr = m_fr.group(1).strip()

                    m_en = re.search(r"([A-Za-z0-9'\s\-]+)\s*\(AN\)", full_card_text, re.IGNORECASE)
                    if m_en:
                        common_name_en = m_en.group(1).strip()
                        common_name_en = re.sub(r"^Nom\s*:\s*", "", common_name_en, flags=re.IGNORECASE).strip()

                    trade_forms = None
                    m_trade = re.search(r"Forme dans le commerce\s*:\s*([^\n\r]+(?:\n[^\n\r]+)?)", full_card_text, re.IGNORECASE)
                    if m_trade:
                        trade_forms = re.sub(r"\s+", " ", m_trade.group(1)).strip()

                    synonyms = []
                    for syn_m in re.finditer(r"\[([A-Z][a-z]+(?:\s+[a-z]+)+)\]", full_card_text):
                        synonyms.append(syn_m.group(1).strip())

                    cleaned_card = re.sub(r"\[[^\]]+\]", "", full_card_text)

                    sci_name = None
                    lines = [l.strip() for l in cleaned_card.split("\n") if l.strip()]
                    for l in lines:
                        if l.startswith("©") or "protégée" in l.lower() or "cites" in l.lower() or "uicn" in l.lower():
                            continue
                        if "copyright" in l.lower() or "botanic garden" in l.lower() or "wikimedia" in l.lower():
                            continue
                        if l.lower().startswith("nom :") or "(fr)" in l.lower() or "(an)" in l.lower() or "forme" in l.lower():
                            continue
                        m_sci = re.search(r"\b([A-Z][a-z]{2,20}\s+[a-z]{2,25}(?:-[a-z]{2,20})?)\b", l)
                        if m_sci:
                            cand = m_sci.group(1).strip()
                            cand_parts = cand.split()
                            g_low = cand_parts[0].lower()
                            s_low = cand_parts[1].lower()
                            if g_low not in STOP_GENERA and s_low not in STOP_EPITHETS:
                                sci_name = cand
                                break

                    if sci_name:
                        card_rec = {
                            "scientific_name": sci_name,
                            "synonyms": synonyms,
                            "common_name_fr": common_name_fr,
                            "common_name_en": common_name_en,
                            "cites_annex": cites_annex,
                            "iucn_status": iucn_status,
                            "gabon_protection": gabon_protection,
                            "trade_forms": trade_forms,
                            "class": banner_cls,
                            "category": banner_cat,
                            "page": page_num,
                        }
                        structured_data.append(card_rec)

                        species_desc = [
                            f"Espèce: {sci_name}",
                            f"Classe: {banner_cls} ({banner_cat})",
                        ]
                        if common_name_fr:
                            species_desc.append(f"Nom français: {common_name_fr}")
                        if common_name_en:
                            species_desc.append(f"Nom anglais: {common_name_en}")
                        if synonyms:
                            species_desc.append(f"Synonymes: {', '.join(synonyms)}")
                        if cites_annex:
                            species_desc.append(f"Statut CITES: {cites_annex}")
                        if iucn_status:
                            species_desc.append(f"Statut UICN: {iucn_status}")
                        if gabon_protection:
                            species_desc.append(f"Protection nationale: {gabon_protection}")
                        if trade_forms:
                            species_desc.append(f"Forme dans le commerce: {trade_forms}")

                        card_body = "\n".join(species_desc)
                        page_text_lines.append(card_body)
                        sections.append(DocumentSection(
                            title=f"Espèce CITES: {sci_name} ({common_name_fr or banner_cat})",
                            level=2,
                            content=card_body,
                            page_start=page_num,
                            page_end=page_num,
                        ))

            full_text_pages.append(f"--- [Page {page_num}] ---\n" + "\n\n".join(page_text_lines))

        doc.structured_data = structured_data
        doc.sections = sections
        doc.raw_text = "\n\n".join(full_text_pages)
        doc.paragraphs = [
            p.strip() for p in re.split(r"\n\s*\n", doc.raw_text) if p.strip() and not p.strip().startswith("--- [Page")
        ]
        doc.language = "fr"
        doc.language_confidence = 0.99
        doc_obj.close()
        return doc

    def parse(
        self,
        file_path: str | Path,
        source_id: str,
        detected_format: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> InternalDocument:
        p = Path(file_path)

        # Try PyMuPDF / fitz first
        try:
            return self._parse_with_fitz(p, source_id)
        except ImportError:
            pass
        except Exception as e:
            # Fitz failed, fallback
            pass

        # Try pypdf fallback
        try:
            return self._parse_with_pypdf(p, source_id)
        except Exception as e:
            doc = self.create_empty_doc(p, source_id, "pdf")
            doc.parsing_warnings.append(f"PDF extraction error: {e}")
            return doc
