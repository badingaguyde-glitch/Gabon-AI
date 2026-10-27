# Bitirme Projesi (Vize Teslimi) — Alana Özel LLM İçin Veri Seti Hazırlama
## Gabon Ulusal Bilgi Tabanı, Biyoçeşitlilik ve Çevre Hukuku Dil Modeli (Domain Corpus & Instruction Dataset v1.0)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: CC-BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Dataset Status: Vize Ready](https://img.shields.io/badge/Dataset_Status-Vize_v1.0_Ready-green.svg)](data/final/)
[![Code Style: Black / Flake8](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

Bu depo, Bilgisayar Mühendisliği Bölümü **Bitirme Projesi Vize Dönemi** kapsamında gerçekleştirilen tüm mühendislik çalışmalarını ve veri setlerini içermektedir.

**Vize Rehberi** (*Alana Özel Bir Dil Modeli İçin Veri Seti Hazırlama*) ilkelerine tam uyumlu olarak, bu aşamada bir model eğitimi yapılmamış; bunun yerine alana özel bir dil modelinin eğitiminde doğrudan kullanılabilecek, kaynağı doğrulanmış, temizlenmiş, tekrarsız ve belgelenmiş iki temel veri seti hazırlanmıştır:
1. **Domain Corpus v1.0** : Modelin alana uyarlanmasında ve continued pretraining (**CPT / DAPT — Domain-Adaptive Pretraining**) aşamasında kullanılacak temiz metin koleksiyonu.
2. **Instruction Dataset v1.0** : Modelin talimat takip etme ve soru-cevap davranışı kazanması için supervised fine-tuning (**SFT**) aşamasında kullanılacak tamamlanmış talimat-cevap veri seti.

---

## 📌 1. Problemin ve Alanın Tanımı

### Problem
Genel amaçlı büyük dil modelleri (ChatGPT, Llama, Qwen vb.), Afrotropikal ekosistemler, ekvatoral yağmur ormanlarının biyoçeşitliliği, endemik türlerin koruma statüleri ve Gabon Cumhuriyeti'nin ulusal çevre ve ormancılık mevzuatı söz konusu olduğunda yetersiz kalmakta ve ciddi bilgi uydurma (hallucination) sorunları yaşamaktadır.

### Hedef
Gabon Cumhuriyeti'nin biyoçeşitliliği, koruma hukuku ve temel sosyo-ekonomik göstergeleri konusunda doğru, güncel ve kaynakları doğrulanabilir yanıtlar üretebilen alana özel bir dil modeli geliştirmek için yüksek kaliteli bir veri altyapısı kurmak.

### Kapsam İçi
- **Biyoçeşitlilik ve Korunan Türler**: Gabon'un simge türleri (*Gorilla gorilla*, *Loxodonta cyclotis*, *Pan troglodytes*, mandriller, deniz memelileri, sürüngenler), orman kanopisi, biyoakustik izleme verileri ve IUCN kırmızı liste statüleri.
- **Çevre Hukuku ve Mevzuat**: Gabon Orman Kanunu, Çevre Kanunu, Balıkçılık Kanunu, Ulusal Parklar Ajansı (ANPN) kuruluş kararnameleri, Anayasa ve onaylanmış uluslararası çevre sözleşmeleri.
- **Ulusal Göstergeler ve Demografi**: Dünya Bankası Gabon tarihsel serileri (1960–2024), Demografi ve Sağlık Araştırması (EDSG-III 2019–2021) ve halk sağlığı istatistikleri.
- **Tarih ve Egemenlik**: Gabon'un siyasi kronolojisi, tarihsel antlaşmalar ve cumhuriyet kurumları.

### Kapsam Dışı
- Kongo Havzası ile ilgisi olmayan yabancı ülkelerin iç siyaseti.
- Genel amaçlı yazılım geliştirme, genel algoritmalar ve kodlama soruları.
- Onaylanmamış bireysel tıbbi tavsiyeler veya klinik reçeteler.

### Hedef Kullanıcı Profili
Ekoloji araştırmacıları, millî park görevlileri (ANPN personeli), çevre hukuku uzmanları, öğrenciler ve Gabon'un doğal/hukuki mirası hakkında güvenilir, kaynaklı ve teknik jargona boğulmamış yanıtlar arayan araştırmacılar.

---

## 📂 2. Proje Klasör Yapısı

Depo yapısı, *Vize Rehberi* 5. Bölümünde belirtilen standart hiyerarşik düzene göre yapılandırılmıştır:

```text
Bitirme-Projesi/
├── data/
│   ├── raw/                      # Orijinal ham veri dosyaları (PDF, CSV, TXT, HTML)
│   ├── extracted/                # Dokümanlardan çıkarılmış ham metinler
│   ├── cleaned/                  # Temizlenmiş ve normalleştirilmiş metinler
│   ├── final/                    # Eğitime hazır nihai veri setleri
│   │   ├── train.jsonl           # Domain Corpus v1.0 %90 eğitim kümesi (1.920 doküman)
│   │   ├── validation.jsonl      # Domain Corpus v1.0 %5 doğrulama kümesi (106 doküman)
│   │   ├── test.jsonl            # Domain Corpus v1.0 %5 test kümesi (108 doküman)
│   │   └── instruction_v1.0.jsonl# Instruction Dataset v1.0 tamamı (4.348 örnek)
│   └── sources.csv               # 8 kurumsal kaynağın detaylı envanteri
├── scripts/                      # Adım adım çalıştırılabilir modüler pipeline kodları
│   ├── 01_download.py            # Kaynak doğrulama ve SHA-256 kayıt kontrolü
│   ├── 02_extract.py             # Çok formatlı metin çıkarma (PyMuPDF)
│   ├── 03_clean.py               # Unicode NFKC, üst/alt bilgi ve gürültü temizleme
│   ├── 04_filter.py              # Kalite, uzunluk ve bozuk karakter filtreleme
│   ├── 05_deduplicate.py         # SHA-256 ve MinHash/Jaccard (0.85) ile tekrar ayıklama
│   ├── 06_split.py               # Doküman düzeyinde train/val/test ayrımı (leakage önleme)
│   ├── 07_token_count.py         # Token sayımı ve istatistikleri (Qwen 2.5 tokenizer profili)
│   └── 08_statistics.py          # Konsolide veri seti raporlarının üretimi
├── notebooks/
│   └── exploration_and_metrics.ipynb # Veri analizi ve metrik inceleme notebook'u
├── reports/                      # Kalite kontrol ve teknik raporlar
│   ├── cleaning_rules.md         # Temizleme kuralları ve öncesi/sonrası örnekleri
│   ├── quality_report.md         # Manuel örnek incelemesi ve çıkarma nedenleri
│   ├── statistics_report.md      # Aşamalar boyunca veri erimesi ve token dağılımı
│   └── permissions/              # Telif, etik ve açık veri kullanım izinleri
│       └── README.md
├── metadata/                     # Bütünlük, varlık ve denetim kayıtları
│   ├── source_registry.json      # Tüm kaynakların SHA-256 kayıt kütüğü
│   ├── entity_registry.json      # Kararlı tür kimlikleri kayıt kütüğü
│   ├── change_log.jsonl          # Artımlı değişikliklerin denetim günlüğü
│   └── conflicts.json            # Çözümlenen bilimsel veri uyuşmazlıkları
├── config.yaml                   # Parametre, eşik ve yolların merkezi yapılandırması
├── requirements.txt              # Sürüm sabitlenmiş Python kütüphaneleri
├── experiments.md                # Teknik kararların tarihli deney günlüğü
├── DATASET_CARD.md               # Domain Corpus v1.0 resmi veri kartı
├── INSTRUCTION_CARD.md           # Instruction Dataset v1.0 resmi veri kartı
└── README.md                     # Bu özet doküman
```

---

## 📊 3. Veri Seti Özeti (Vize Raporu Sayısal Tablosu)

*Vize Rehberi* 12. Bölümünde istenen biçimde veri setimizin nicel özeti:

| Özellik | Değer |
| :--- | :--- |
| **Veri kaynağı sayısı** | 8 kurumsal sağlayıcı (105 birincil kaynak dosya) |
| **Ham doküman / bölüm sayısı** | 2.318 doküman |
| **Extraction başarılı** | 2.243 doküman (%96,8) |
| **Extraction başarısız (OCR akışına ayrılan)** | 75 doküman (%3,2) |
| **Filtering ve temizleme sonrası** | 2.219 doküman |
| **Exact duplicate (SHA-256)** | 38 doküman |
| **Near duplicate (Jaccard $\ge 0.85$)** | 47 doküman |
| **Final doküman sayısı (Domain Corpus v1.0)** | **2.134 doküman** |
| **Toplam kelime sayısı** | **1.009.778 kelime** |
| **Toplam karakter sayısı** | **12.907.476 karakter** |
| **Toplam token sayısı (Qwen 2.5 Tokenizer)** | **3.395.898 token** |
| **Fransızca içerik oranı** | **%94,7** |
| **İngilizce içerik oranı (Uluslararası terminoloji)** | **%5,3** |
| **Manuel kontrol örneği (Corpus)** | 200 doküman |
| **Manuel kalite başarısı (Corpus)** | **%97,5** |
| **Instruction örneği (Instruction Dataset v1.0)** | **4.348 örnek** |
| **Manuel kontrol örneği (Instruction)** | 150 örnek |
| **Manuel kalite başarısı (Instruction)** | **%98,0** |

---

## 🎯 4. Instruction Dataset v1.0 — Görev Türleri ve Dağılımı

*Vize Rehberi* 11. Bölümü uyarınca, instruction seti yalnızca basit bilgi sorularından oluşmamakta; problem alanımıza uygun dengeli bir taksonomi içermektedir:

```text
├── valeur_indicateur        : 1.793 (%41,2)  -> Kesin istatistiksel metrik, yıl ve birim sorguları
├── attribution_juridique    :   847 (%19,5)  -> İlgili kanun maddesi, kararname ve yetkili makam tespiti
├── analyse_article_loi      :   563 (%12,9)  -> Kanun maddesinin kapsamı ve hukuki analizi
├── analyse_tendance         :   338 ( %7,8)  -> Zaman içindeki değişim ve çok yıllı eğilim analizleri
├── situation_recente        :   238 ( %5,5)  -> Ulusal göstergelerin güncel durumu
├── definition_concept       :   221 ( %5,1)  -> Ekolojik ve hukuki kavramların tanımlanması
├── explication_synthese     :   171 ( %3,9)  -> Teknik rapor ve kanun metinlerinin özetlenmesi
├── bilgi_yetersizligi       :   104 ( %2,4)  -> Alan dışı konularda sınırını bildirme ve kibar ret (Zorunlu)
└── profil_biodiversite      :    73 ( %1,7)  -> Taksonomi, yaşam alanı, tehditler ve koruma profili
```

> [!IMPORTANT]
> **Bilgi Yetersizliği ve Alan Sınırını Bildirme Davranışı (`bilgi_yetersizligi`)**:
> Rehberde özellikle vurgulanan bu davranış için sete 104 adet örnek eklenmiştir. Model, alan dışı konularda (örneğin yabancı borsa, insan tıbbı reçetesi vb.) bilgi uydurmak yerine: *"Bu soruya cevap veremem. Ben Gabon Cumhuriyeti'nin biyoçeşitliliği, çevre mevzuatı ve ulusal verileri üzerine uzmanlaştım..."* şeklinde sınırlarını bildirmektedir.

---

## 🛡️ 5. Veri Ayrımı ve Veri Sızıntısını (Data Leakage) Önleme

Veri kümeleri oluşturulurken rehberdeki en kritik kurala riayet edilmiştir:
- Ayrım işlemi **kesinlikle doküman düzeyinde** yapılmıştır (`RANDOM_SEED = 42`).
- Dokümanlar eğitim (%90), doğrulama (%5) ve test (%5) kümelerine bölünmeden önce parçalara (chunk) ayrılmamıştır.
- Test kümesindeki bir dokümandan türetilmiş herhangi bir instruction sorusu, eğitim kümesine kesinlikle dahil edilmemiştir. Böylece final değerlendirmesinde ölçüm sonuçlarının geçerliliği güvence altına alınmıştır.

---

## 🚀 6. Hızlı Başlangıç ve Yeniden Üretilebilirlik (Reproducibility)

Tüm veri hazırlama zincirini sıfırdan çalıştırmak için:

### 1. Kütüphaneleri kurun
```bash
git clone https://github.com/kullanici-adi/Bitirme-Projesi.git
cd Bitirme-Projesi
pip install -r requirements.txt
```

### 2. Modüler betikleri sırasıyla çalıştırın
```bash
# Kaynak bütünlüğü ve SHA-256 kontrolü
python scripts/01_download.py

# PDF ve CSV belgelerinden metin çıkarma
python scripts/02_extract.py

# Unicode NFKC ve gürültü temizliği
python scripts/03_clean.py

# Kalite ve eşik filtrelemesi
python scripts/04_filter.py

# Çift aşamalı tekrar ayıklama (SHA-256 + MinHash Jaccard 0.85)
python scripts/05_deduplicate.py

# Doküman düzeyinde train/validation/test ayrımı
python scripts/06_split.py

# Token dağılımı ve istatistik hesaplama
python scripts/07_token_count.py

# Konsolide istatistik ve özet tabloları
python scripts/08_statistics.py
```

### 3. Varlık çözümleme ve artımlı bilgi tabanı motoru
```bash
python pipeline.py --input-dir data --output-dir .
```

---

## 🔮 7. Vizeden Sonra Ne Olacak? (Final Dönemi Yol Haritası)

1. **Continued Pretraining (CPT / DAPT)**: Açık kaynaklı temel bir base model (örn. `Qwen2.5-7B-Base`), `data/final/train.jsonl` üzerindeki 3,4 milyon token ile alana uyarlanacak.
2. **Supervised Fine-Tuning (SFT)**: CPT aşamasından çıkan modele `data/final/instruction_v1.0.jsonl` kullanılarak LoRA / QLoRA ile soru-cevap davranışı kazandırılacak.
3. **Bilimsel Karşılaştırma**: Üç sistem yan yana test edilecek:
   - Hazır genel amaçlı model.
   - Sadece CPT yapılmış model.
   - CPT + SFT yapılmış alana özel model.
4. **Uygulama Katmanları**: RAG (vektör arama), ChromaDB vektör veri tabanı, FastAPI REST servisleri ve web arayüzü entegrasyonu tamamlanacak.

---

## 👥 Proje Ekibi
- **Bilgisayar Mühendisliği Bölümü Bitirme Projesi**
- **Detaylı Bilgi ve Raporlar**: [`DATASET_CARD.md`](DATASET_CARD.md), [`INSTRUCTION_CARD.md`](INSTRUCTION_CARD.md) ve [`experiments.md`](experiments.md) dosyalarını inceleyebilirsiniz.
