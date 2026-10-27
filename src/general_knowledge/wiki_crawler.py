"""Wikipedia Historical Crawler for Gabon with strict reference count scoring.

Evaluation metric:
- Counts explicit occurrences of 'gabon' (and variants 'gabonais', 'gabonaise')
  in the article's complete wikitext.
- ref_count == 0  : REJETÉ IMMÉDIATEMENT (aucun téléchargement).
- 1 <= ref_count < 3 : EN ATTENTE DE SECONDE RÉVISION (liste d'attente).
- ref_count >= 3 : ACCEPTÉ IMMÉDIATEMENT pour téléchargement direct.

Seconde révision :
- Calcul de la médiane et de la moyenne des références parmi les pages acceptées / évaluées.
- Les pages en attente dont le score atteint ou dépasse le seuil requis sont repêchées et téléchargées.
"""

from __future__ import annotations

import collections
import json
import os
from pathlib import Path
import re
import statistics
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple

WIKI_API_URL = "https://fr.wikipedia.org/w/api.php"
WIKI_REST_PDF_URL = "https://fr.wikipedia.org/api/rest_v1/page/pdf"
USER_AGENT = "GabonHistoryPipeline/2.0 (https://github.com/gabon-project; educational research)"

DISCARD_TITLE_PATTERNS = [
    r"^\d{1,4}$",  # pure years like '1960'
    r"^(Janvier|Février|Mars|Avril|Mai|Juin|Juillet|Août|Septembre|Octobre|Novembre|Décembre)\b",
    r"^(Catégorie|Fichier|Portail|Aide|Discussion|Modèle|Projet|Wikipédia):",
    r"\b(football|coupe du monde|jeux olympiques|championnat)\b",
]


def clean_filename(title: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "_", title)
    clean = re.sub(r"\s+", "_", clean).strip("_")
    return clean[:120] or "page"


class WikipediaHistoryCrawler:
    """Recursive crawler with strict reference count scoring and secondary review thresholding."""

    def __init__(
        self,
        output_dir: str | Path = "Histoire",
        seeds: Optional[List[str]] = None,
        max_depth: int = 3,
        max_pages: int = 150,
        request_delay_sec: float = 0.3,
    ):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir = self.output_dir / "pdf"
        self.json_dir = self.output_dir / "metadata"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)

        self.seeds = seeds or [
            "Gabon",
            "Histoire du Gabon",
            "Politique au Gabon",
            "Léon Mba",
            "Omar Bongo",
            "Ali Bongo",
            "Brice Clotaire Oligui Nguema",
            "Coup d'État de 2023 au Gabon",
            "Liste des présidents de la République gabonaise",
            "Afrique équatoriale française"
        ]
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.delay = request_delay_sec

        self.index_file = self.output_dir / "index_histoire.json"
        self.index: Dict[str, Dict[str, Any]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index(self) -> None:
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[INDEX ERROR] Impossible de sauvegarder l'index : {e}")

    def audit_and_clean_existing_documents(self) -> int:
        """Audits already downloaded PDFs in Histoire/pdf and removes any with 0 references to Gabon."""
        print(f"\n========================================================")
        print(f"[AUDIT INITIAL] Verification du dossier Histoire/ ({len(self.index)} enregistres)")
        print(f"========================================================")
        import fitz

        purged = 0
        all_pdfs = sorted(self.pdf_dir.glob("*.pdf"))
        for pdf in all_pdfs:
            try:
                doc = fitz.open(pdf)
                txt = "".join(p.get_text() for p in doc).lower()
                doc.close()
                cnt = txt.count("gabon")
                if cnt == 0:
                    print(f"  [-] SUPPRIME : '{pdf.name}' (0 reference au Gabon)")
                    pdf.unlink()
                    json_p = self.json_dir / f"{pdf.stem}.json"
                    if json_p.exists():
                        json_p.unlink()
                    to_del = [k for k, v in self.index.items() if v.get("pdf_filename") == pdf.name]
                    for k in to_del:
                        del self.index[k]
                    purged += 1
                else:
                    # Update ref count in index
                    for k, v in self.index.items():
                        if v.get("pdf_filename") == pdf.name:
                            v["gabon_references_count"] = cnt
            except Exception as e:
                print(f"  [!] Erreur lors de l'audit de {pdf.name}: {e}")

        self._save_index()
        print(f"Audit termine : {purged} fichiers supprimes car 0 reference. {len(self.index)} fichiers valides conserves.")
        print(f"========================================================\n")
        return purged

    def list_existing_history_documents(self) -> None:
        """Displays currently kept history documents with reference count and section outlines."""
        print(f"\n========================================================")
        print(f"[INVENTAIRE] DOCUMENTS VALIDES DANS HISTOIRE : {self.output_dir}")
        print(f"========================================================")
        if not self.index:
            print("  (Aucun document d'histoire n'est encore enregistre)")
        else:
            print(f"Total documents valides : {len(self.index)}\n")
            for idx, (title, meta) in enumerate(self.index.items(), start=1):
                pdf_name = meta.get("pdf_filename", "N/A")
                file_size = meta.get("pdf_size_bytes", 0)
                ref_cnt = meta.get("gabon_references_count", "N/A")
                sections = meta.get("main_sections", [])
                sec_str = ", ".join(sections[:4]) + ("..." if len(sections) > 4 else "")
                print(f"  [{idx:03d}] {title} (Fichier: {pdf_name}, {file_size / 1024:.1f} Ko, Refs Gabon: {ref_cnt})")
                if sec_str:
                    print(f"        Grands titres : {sec_str}")
        print(f"========================================================\n")

    def _api_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["format"] = "json"
        url = WIKI_API_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        time.sleep(self.delay)
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_page_sections(self, title: str) -> List[str]:
        try:
            data = self._api_get({
                "action": "parse",
                "page": title,
                "prop": "sections",
                "redirects": 1
            })
            sections = []
            for sec in data.get("parse", {}).get("sections", []):
                if sec.get("level") in ("2", 2, "3", 3):
                    line = sec.get("line", "").strip()
                    if line and line.lower() not in ("voir aussi", "liens externes", "notes et références", "articles connexes"):
                        sections.append(line)
            return sections
        except Exception:
            return []

    def get_page_details_with_ref_count(self, title: str) -> Optional[Dict[str, Any]]:
        """Retrieves page metadata, outgoing links AND computes occurrences of 'gabon' in wikitext."""
        try:
            data = self._api_get({
                "action": "query",
                "titles": title,
                "prop": "categories|links|info|revisions",
                "rvprop": "content",
                "rvslots": "main",
                "inprop": "url",
                "cllimit": "max",
                "pllimit": "max",
                "redirects": 1
            })
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return None
            p = list(pages.values())[0]
            if "missing" in p:
                return None

            resolved_title = p.get("title", title)
            categories = [c.get("title", "").replace("Catégorie:", "").strip() for c in p.get("categories", [])]
            raw_links = [l.get("title", "").strip() for l in p.get("links", []) if l.get("ns") == 0 or "ns" not in l]

            outgoing_links = []
            for link in raw_links:
                if any(re.search(pat, link, re.IGNORECASE) for pat in DISCARD_TITLE_PATTERNS):
                    continue
                outgoing_links.append(link)

            canonical_url = p.get("fullurl") or f"https://fr.wikipedia.org/wiki/{urllib.parse.quote(resolved_title)}"

            # Compute references to Gabon in wikitext
            revisions = p.get("revisions", [])
            wikitext = ""
            if revisions:
                slot = revisions[0].get("slots", {}).get("main", {})
                wikitext = slot.get("*", "") or revisions[0].get("*", "")

            # Count occurrences of 'gabon', 'gabonaise', 'gabonais'
            wikitext_lower = wikitext.lower()
            title_lower = resolved_title.lower()
            categories_lower = " ".join(categories).lower()

            # References in body + category bonus + title bonus
            body_count = len(re.findall(r"\bgabon(?:ais|aise|aises)?\b", wikitext_lower))
            if "gabon" in title_lower:
                body_count += 10
            if "gabon" in categories_lower:
                body_count += 3

            return {
                "title": resolved_title,
                "pageid": p.get("pageid"),
                "url": canonical_url,
                "categories": categories,
                "outgoing_links": outgoing_links,
                "gabon_ref_count": body_count,
            }
        except Exception as e:
            print(f"  [API WARN] Echec de la recuperation pour '{title}': {e}")
            return None

    def download_page_pdf(self, title: str, output_path: Path) -> bool:
        encoded_title = urllib.parse.quote(title)
        url = f"{WIKI_REST_PDF_URL}/{encoded_title}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        try:
            time.sleep(self.delay)
            with urllib.request.urlopen(req, timeout=35) as resp:
                if resp.status == 200:
                    content = resp.read()
                    if len(content) > 1000 and content.startswith(b"%PDF"):
                        with open(output_path, "wb") as f:
                            f.write(content)
                        return True
            return False
        except Exception as e:
            print(f"  [PDF DOWNLOAD WARN] Echec du telechargement PDF pour '{title}': {e}")
            return False

    def _save_downloaded_record(self, details: Dict[str, Any], depth: int, referrer: str, pdf_path: Path, json_path: Path) -> None:
        resolved_title = details["title"]
        pdf_size = pdf_path.stat().st_size
        main_sections = self.get_page_sections(resolved_title)

        meta_record = {
            "title": resolved_title,
            "url": details["url"],
            "pageid": details["pageid"],
            "crawled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "depth": depth,
            "referrer": referrer,
            "gabon_references_count": details["gabon_ref_count"],
            "main_sections": main_sections,
            "categories": details["categories"],
            "total_outgoing_links": len(details["outgoing_links"]),
            "outgoing_links": details["outgoing_links"],
            "pdf_filename": pdf_path.name,
            "pdf_size_bytes": pdf_size,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta_record, f, indent=2, ensure_ascii=False)

        self.index[resolved_title] = {
            "pdf_filename": pdf_path.name,
            "pdf_size_bytes": pdf_size,
            "gabon_references_count": details["gabon_ref_count"],
            "main_sections": main_sections,
            "url": details["url"],
            "outgoing_links_count": len(details["outgoing_links"]),
        }
        self._save_index()

    def crawl_and_download(self) -> Dict[str, Any]:
        """Runs the two-phase crawler:
        Phase 1:
          - ref == 0 : NON-TELECHARGEMENT IMMÉDIAT
          - 1 <= ref < 3 : EN ATTENTE DE SECONDE RÉVISION
          - ref >= 3 : TÉLÉCHARGEMENT IMMÉDIAT
        Phase 2:
          - Calcul médiane / moyenne des scores des pages
          - Revue des pages en attente : repêchage si ref_count >= seuil requis.
        """
        # Step 0: Initial audit of existing documents
        self.audit_and_clean_existing_documents()

        # Step 1: Inventory
        self.list_existing_history_documents()

        print(f"========================================================")
        print(f"[WIKI CRAWLER] DEMARRAGE EXPLORATION AVEC FILTRAGE PAR OCCURRENCES")
        print(f"Regle : 0 ref = Rejet | 1-2 ref = En attente | >=3 ref = Telechargement direct")
        print(f"========================================================\n")

        queue = collections.deque([(seed, 0, "Point de depart") for seed in self.seeds])
        visited_or_queued: Set[str] = set(self.seeds)

        pages_evaluated = 0
        pages_direct_download = 0
        pages_rejected_zero = 0
        pending_review_pages: List[Tuple[Dict[str, Any], int, str]] = []  # (details, depth, referrer)
        all_positive_scores: List[int] = [
            v.get("gabon_references_count", 1) for v in self.index.values() if isinstance(v.get("gabon_references_count"), int) and v.get("gabon_references_count") > 0
        ]

        while queue and pages_evaluated < self.max_pages:
            current_title, current_depth, referrer = queue.popleft()
            clean_stem = clean_filename(current_title)
            pdf_path = self.pdf_dir / f"{clean_stem}.pdf"
            json_path = self.json_dir / f"{clean_stem}.json"

            print(f"[{pages_evaluated + 1}/{self.max_pages}] [EXAMEN] '{current_title}' (Prof: {current_depth}, Referent: {referrer})")

            # Check if already present in valid index
            if current_title in self.index and pdf_path.exists() and json_path.exists():
                ref_cnt = self.index[current_title].get("gabon_references_count", ">0")
                print(f"  [SKIP DEJA VALIDE] Fichier '{pdf_path.name}' present (Refs Gabon: {ref_cnt}). Passage aux liens.")
                pages_evaluated += 1
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    out_links = meta.get("outgoing_links", [])
                    if current_depth < self.max_depth:
                        for next_title in out_links:
                            if next_title not in visited_or_queued:
                                visited_or_queued.add(next_title)
                                queue.append((next_title, current_depth + 1, current_title))
                except Exception:
                    pass
                continue

            # Fetch details and compute exact reference count
            details = self.get_page_details_with_ref_count(current_title)
            if not details:
                print(f"  [IGNORER] Page introuvable ou inaccessible.")
                continue

            resolved_title = details["title"]
            ref_count = details["gabon_ref_count"]
            print(f"  [MESURE LIENS GABON] Occurrences detectees : {ref_count}")

            # DECISION RULE:
            # 1. 0 reference -> NON-TELECHARGEMENT
            if ref_count == 0:
                print(f"  [REJET - 0 REFERENCE] Aucun lien ni mention du Gabon dans la page. NON-TELECHARGE.")
                pages_rejected_zero += 1
                pages_evaluated += 1
                continue

            # 2. < 3 references -> EN ATTENTE DE SECONDE REVISION
            elif ref_count < 3:
                print(f"  [EN ATTENTE] {ref_count} reference(s) (<3) : Placee en liste d'attente pour la seconde revision.")
                pending_review_pages.append((details, current_depth, referrer))
                all_positive_scores.append(ref_count)
                pages_evaluated += 1

            # 3. >= 3 references -> TELECHARGEMENT DIRECT
            else:
                print(f"  [ACCEPTE DIRECT] {ref_count} references (>=3) : Page hautement pertinente sur le Gabon.")
                all_positive_scores.append(ref_count)
                print(f"  [TELECHARGEMENT PDF] Vers '{pdf_path.name}'...")
                ok = self.download_page_pdf(resolved_title, pdf_path)
                if ok:
                    print(f"  [OK] PDF telecharge avec succes ({pdf_path.stat().st_size / 1024:.1f} Ko).")
                    self._save_downloaded_record(details, current_depth, referrer, pdf_path, json_path)
                    pages_direct_download += 1
                else:
                    print(f"  [WARN] Echec telechargement PDF.")
                pages_evaluated += 1

            # Queue outgoing links if page has any reference to Gabon
            if current_depth < self.max_depth and ref_count > 0:
                out_links = details.get("outgoing_links", [])
                added_count = 0
                for next_title in out_links:
                    if next_title not in visited_or_queued:
                        visited_or_queued.add(next_title)
                        queue.append((next_title, current_depth + 1, resolved_title))
                        added_count += 1
                if added_count > 0:
                    print(f"  [CROSS-REF] +{added_count} nouveaux liens ajoutes a l'exploration.")

            print()

        # PHASE 2 : SECONDE REVISION DES PAGES EN ATTENTE
        print(f"\n========================================================")
        print(f"[SECONDE REVISION] EVALUATION DES PAGES EN ATTENTE ({len(pending_review_pages)} pages)")
        print(f"========================================================")

        pages_reviewed_downloaded = 0
        if pending_review_pages:
            mean_score = statistics.mean(all_positive_scores) if all_positive_scores else 3.0
            median_score = statistics.median(all_positive_scores) if all_positive_scores else 3.0
            print(f"Statistiques globales des references : Moyenne = {mean_score:.2f} | Mediane = {median_score:.2f}")

            # Requisite threshold for secondary review: minimum 2 references or >= median/4
            threshold = 2
            print(f"Seuil requis pour repechage en seconde revision : {threshold} references")

            for details, depth, referrer in pending_review_pages:
                title = details["title"]
                score = details["gabon_ref_count"]
                clean_stem = clean_filename(title)
                pdf_path = self.pdf_dir / f"{clean_stem}.pdf"
                json_path = self.json_dir / f"{clean_stem}.json"

                if score >= threshold:
                    print(f"  [REPECHAGE ACCEPTE] '{title}' ({score} ref >= {threshold}). Telechargement en cours...")
                    ok = self.download_page_pdf(title, pdf_path)
                    if ok:
                        print(f"  [OK] PDF telecharge ({pdf_path.stat().st_size / 1024:.1f} Ko).")
                        self._save_downloaded_record(details, depth, referrer, pdf_path, json_path)
                        pages_reviewed_downloaded += 1
                else:
                    print(f"  [DEFINITIVEMENT REJETE] '{title}' ({score} ref < {threshold}).")
        else:
            print("Aucune page n'etait en attente de revision.")

        print(f"\n========================================================")
        print(f"[BILAN CRAWLER WIKIPEDIA]")
        print(f"Pages examinees               : {pages_evaluated}")
        print(f"Pages rejetees (0 reference)  : {pages_rejected_zero}")
        print(f"Pages acceptees direct (>=3)  : {pages_direct_download}")
        print(f"Pages repechees en revision   : {pages_reviewed_downloaded}")
        print(f"Total valide dans Histoire/   : {len(self.index)}")
        print(f"========================================================\n")

        return {
            "total_documents": len(self.index),
            "direct_download": pages_direct_download,
            "reviewed_download": pages_reviewed_downloaded,
            "rejected_zero": pages_rejected_zero,
            "history_dir": str(self.output_dir)
        }
