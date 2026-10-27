# Dataset card — Modèle de connaissances générales par pays

Généré le 2026-10-14T10:15:09 UTC.

Axe principal : **pays**. Axe secondaire : **catégorie** de question.

| Fichier | Usage | Volume |
|---|---|---|
| `sft_chat.jsonl` | Fine-tuning instructionnel (format messages) | 25469 exemples |
| `sft_alpaca.jsonl` | Fine-tuning format Alpaca | 25469 exemples |
| `splits/` | train / validation / test (90/5/5, déterministe) | — |
| `pretraining_corpus.jsonl` | Pré-entraînement continu | 2134 docs, 6,451,163 caractères |
| `rag_chunks.jsonl` | Embeddings / RAG | 8323 passages |
| `kg_triplets.jsonl` | Graphe de connaissances | 43642 triplets |

## Gabon

| Catégorie | Exemples SFT |
|---|---|
| Droit et justice (`droit`) | 8487 |
| Économie et finances (`economie`) | 6450 |
| Santé (`sante`) | 1866 |
| Société, travail et protection sociale (`social`) | 1628 |
| Démographie et population (`demographie`) | 1308 |
| Éducation (`education`) | 1080 |
| Environnement et climat (`environnement`) | 1056 |
| Administration et services publics (`administration`) | 692 |
| Biodiversité, faune et flore (`biodiversite`) | 582 |
| Connaissances générales (`general`) | 531 |
| Énergie, mines et hydrocarbures (`energie_mines`) | 394 |
| Infrastructures, transport et télécommunications (`infrastructures_transport`) | 322 |
| Agriculture, pêche et alimentation (`agriculture`) | 314 |
| Histoire, personnalités et politique (`histoire`) | 265 |
| Culture, langues et tourisme (`culture_tourisme`) | 206 |
| Sécurité et défense (`securite`) | 122 |
| Géographie et localisation (`geographie`) | 21 |

## France

| Catégorie | Exemples SFT |
|---|---|
| Histoire, personnalités et politique (`histoire`) | 77 |
| Culture, langues et tourisme (`culture_tourisme`) | 23 |
| Droit et justice (`droit`) | 21 |
| Géographie et localisation (`geographie`) | 1 |

## Cameroun

| Catégorie | Exemples SFT |
|---|---|
| Culture, langues et tourisme (`culture_tourisme`) | 16 |
| Histoire, personnalités et politique (`histoire`) | 4 |
| Biodiversité, faune et flore (`biodiversite`) | 3 |

## Types de questions

| Type | Exemples |
|---|---|
| `indicator_value` | 10911 |
| `legal_source_attribution` | 4606 |
| `legal_article` | 3855 |
| `indicator_trend` | 2122 |
| `indicator_latest` | 1252 |
| `indicator_definition` | 1252 |
| `document_passage` | 1018 |
| `species_profile` | 239 |
| `species_name` | 156 |
| `legal_preamble` | 13 |
| `legal_structure` | 13 |
| `dataset_description` | 11 |
| `dataset_variables` | 11 |
| `survey_metadata` | 10 |
