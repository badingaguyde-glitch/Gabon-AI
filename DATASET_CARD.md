# Gabon Ulusal Bilgi Tabanı ve Biyoçeşitlilik — Domain Corpus v1.0

## Amaç
Bu veri seti, Gabon Cumhuriyeti'nin biyoçeşitliliği, korunan alanları, çevre hukuku ve temel sosyo-ekonomik verileri konusunda soru cevaplayabilen alana özel bir dil modelinin **continued pretraining (CPT / DAPT — Domain-Adaptive Pretraining)** aşamasında kullanılmak üzere hazırlanmıştır. Genel amaçlı bir web metin koleksiyonu değildir ve öyle kullanılması amaçlanmamıştır.

## Kapsam
- **Kapsam içi**:
  - Afrotropikal biyoçeşitlilik ve Gabon'un koruma altındaki simge türleri (*Gorilla gorilla*, *Loxodonta cyclotis*, *Pan troglodytes*, mandriller, deniz memelileri, sürüngenler ve endemik flora).
  - Gabon hukuki ve mevzuat altyapısı: Gabon Orman Kanunu, Çevre Kanunu, Balıkçılık Kanunu, Ulusal Parklar Ajansı (ANPN) kararnameleri, Anayasa ve onaylanmış uluslararası çevre antlaşmaları.
  - Makro-ekonomik göstergeler, halk sağlığı araştırmaları (EDSG-III) ve ulusal demografi verileri.
  - Gabon Cumhuriyeti'nin siyasi kronolojisi, egemenlik tarihi ve devlet kurumları.
- **Kapsam dışı**:
  - Orta Afrika ve Kongo Havzası ile doğrudan ilgisi bulunmayan yabancı ülkelerin iç politikaları.
  - Genel amaçlı yazılım geliştirme, genel algoritmalar ve programlama içerikleri.
  - Doğrulanmamış bireysel klinik tıbbi reçeteler ve cerrahi öneriler.

## Veri Kaynakları

| Kaynak | Tür | Dil | Doküman | Lisans / Kullanım Durumu |
| :--- | :--- | :--- | :--- | :--- |
| Çevre ve Orman Mevzuatı (Gabon Hükümeti) | PDF | tr/fr | 42 | Kamuya açık / Resmi Gazete (Journal Officiel) |
| Dünya Bankası Göstergeleri (Gabon Serisi 1960–2024) | CSV | en/fr | 3 | CC-BY 4.0 |
| İstatistik Genel Müdürlüğü (DGS - EDSG-III) | TXT/PDF | fr | 1 | Açık devlet erişimi |
| IUCN Kırmızı Liste Gabon Koruma Statüleri | PDF/JSON | en/fr | 28 | Bilimsel araştırma ve koruma |
| Büyük Memeli Sayımları ve FSC 2023 | CSV | fr | 1 | CC-BY 4.0 |
| BioCon Gabon Soundscapes (Biyoakustik İzleme) | CSV | en | 1 | CC-BY 4.0 (Zenodo) |
| Ulusal Tarih ve Devlet Arşivleri | HTML/MD | fr | 25 | CC BY-SA 4.0 |
| Anayasa ve Temel Hukuk Metinleri | PDF | fr | 4 | Resmi Gazete |
| **Toplam (ham)** | **Çoklu** | **fr/en** | **105 kaynak dosya** | |

*İngilizce kaynaklar hakkında not*: İngilizce dokümanlar (Dünya Bankası göstergeleri, IUCN koruma verileri ve biyoakustik kayıtlar) toplam corpus'un %5,3'ünü oluşturmaktadır. Bu dokümanlar, uluslararası standart göstergelerin ve Latince/İngilizce taksonomik terminolojinin korunması amacıyla özellikle veri setinde tutulmuştur.

## Veri Toplama
Dokümanlar 28 Eylül – 14 Ekim 2026 tarihleri arasında `scripts/01_download.py` betiği ile toplanmıştır. Web kaynaklarında `robots.txt` kurallarına titizlikle uyulmuş ve istekler arasına 2 saniyelik bekleme süresi konulmuştur. İndirilen tüm ham dosyalar `data/` altında orijinal hâliyle saklanmaktadır. Kaynakların SHA-256 doğrulama özetleri `metadata/source_registry.json` kütüğünde kayıtlıdır.

## İşleme Adımları
1. **Extraction (Metin Çıkarma)**: Metin katmanı bulunan PDF'ler için `PyMuPDF`, taranmış 7 arşiv belgesi için Tesseract OCR, tablolar için CSV ayrıştırıcılar ve web sayfaları için `Trafilatura` kullanıldı.
2. **Cleaning (Temizleme)**: Tekrarlayan sayfa başlık ve alt bilgileri (> 5 tekrar), Unicode NFKC normalizasyonu, bozuk karakter (mojibake) düzeltmeleri ve 20 karakterden kısa anlamsız yalnız satırların temizlenmesi uygulandı. Kurallar `reports/cleaning_rules.md` dosyasında belgelenmiştir.
3. **Filtering (Filtreleme)**: 150 karakterden kısa dokümanlar, bozuk karakter oranı %10'u aşan sayfalar ve alan dışı metinler ayıklandı.
4. **Deduplication (Tekrar Ayıklama)**: 
   - *Exact duplicate*: SHA-256 kriptografik hash ile 38 tam kopya silindi.
   - *Near duplicate*: MinHash + Jaccard benzerliği (eşik $\ge 0.85$, 128 permütasyon) ile 47 yakın kopya elendi.

## Format
JSON Lines (`.jsonl`). Her satır bir dokümandır ve şu metadata alanlarını içerir:
```json
{
  "document_id": "DOC_000123",
  "title": "Code forestier gabonais - Titre II de la gestion durable",
  "source": "ministere_environnement_gabon",
  "url": "https://environnement.gouv.ga",
  "language": "fr",
  "document_type": "texte_juridique_ou_statistique",
  "publication_year": 2024,
  "subtopic": "droit",
  "country": "Gabon",
  "char_count": 8412,
  "token_count": 2213,
  "text": "..."
}
```

## İstatistikler

| Ölçüt | Değer |
| :--- | :--- |
| **Final doküman sayısı** | **2.134** |
| **Toplam karakter sayısı** | **12.907.476** |
| **Toplam kelime sayısı** | **1.009.778** |
| **Toplam token sayısı (Qwen 2.5 tokenizer)** | **3.395.898** |
| Ortalama doküman uzunluğu | 1.591 token |
| Medyan doküman uzunluğu | 845 token |
| 95. yüzdelik (P95) | 4.210 token |
| Dil dağılımı (Fransızca / İngilizce) | %94,7 / %5,3 |

### Alt Konu Dağılımı (Subtopics)
- **Ekonomi ve Kamu Maliyesi**: 455 doküman (%21,3)
- **Hukuk ve Çevre Mevzuatı**: 399 doküman (%18,7)
- **Tarih ve Cumhuriyet Kurumları**: 312 doküman (%14,6)
- **Sosyal İşler ve İstihdam**: 221 doküman (%10,4)
- **Halk Sağlığı (EDSG Verileri)**: 151 doküman (%7,1)
- **Eğitim**: 112 doküman (%5,2)
- **Demografi ve Nüfus**: 85 doküman (%4,0)
- **Çevre, İklim ve Orman**: 83 doküman (%3,9)
- **Kamu Yönetimi**: 82 doküman (%3,8)
- **Genel Bilgiler**: 55 doküman (%2,6)
- **Kültür ve Turizm**: 44 doküman (%2,1)
- **Biyoçeşitlilik ve Korunan Türler**: 36 doküman (%1,7)
- **Altyapı ve Ulaşım**: 30 doküman (%1,4)
- **Enerji ve Madencilik**: 27 doküman (%1,3)
- **Tarım ve Balıkçılık**: 23 doküman (%1,1)
- **Coğrafya**: 10 doküman (%0,5)
- **Güvenlik**: 9 doküman (%0,4)

## Veri Ayrımı (Data Leakage Önleme)
Veri ayrımı **kesinlikle doküman düzeyinde** yapılmış olup `RANDOM_SEED = 42` parametresiyle `scripts/06_split.py` tarafından gerçekleştirilmiştir:
- **Train (Eğitim kümesi)**: 1.920 doküman (%90,0) -> `data/final/train.jsonl`
- **Validation (Doğrulama kümesi)**: 106 doküman (%5,0) -> `data/final/validation.jsonl`
- **Test (Test kümesi)**: 108 doküman (%5,0) -> `data/final/test.jsonl`

> [!IMPORTANT]
> Dokümanlar bölünmeden önce parçalara (chunk) ayrılmamıştır. Aynı dokümanın bir parçası eğitime, başka bir parçası teste kesinlikle düşemez; veri sızıntısı (*data leakage*) tamamen engellenmiştir.

## Lisans ve Etik
Veri setindeki tüm kaynaklar kamuya açık devlet yayınlarından, açık lisanslı uluslararası veri tabanlarından (Dünya Bankası, Zenodo, Mendeley) veya Creative Commons lisanslı arşivlerden derlenmiştir.
Kişisel veri (PII) içermemektedir; anket ve sağlık verileri tamamen anonimleştirilmiş ve bölgesel küme düzeyinde toplanmıştır.

## Bilinen Problemler
1. **Sektörel dağılım dengesizliği**: Hukuk, ekonomi ve tarih konuları, taranmış resmi metinlerin çokluğu nedeniyle sağlık ve tarıma kıyasla daha geniş yer kaplamaktadır.
2. **Tablo yapısı**: Dünya Bankası raporlarındaki çok sütunlu tablolar çıkarılırken iki boyutlu hücre hiyerarşisi doğrusal metne dönüşmüştür.
3. **Mevzuat değişiklikleri**: 2010 öncesi mülga kanunlar tarihsel bağlamıyla etiketlenmiş olup güncel mevzuatla karıştırılmaması için metadata alanında yılı belirtilmiştir.

## Sürüm Geçmişi
- **v0.1 (07.10.2026)**: Çok formatlı ilk veri çıkarma ve ham kayıtlar.
- **v0.5 (14.10.2026)**: Artımlı birleştirme, bilimsel olguların tespiti ve tür kayıtları.
- **v1.0 (25.10.2026)**: Unicode NFKC temizliği, MinHash tekrar ayıklama, token sayımı ve vize teslimi.
