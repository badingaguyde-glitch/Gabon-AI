# Çalışma ve Deney Günlüğü (Experiments Log)

Bu belge, bitirme projesinin ilk 7 haftası boyunca gerçekleştirilen teknik denemeleri, karşılaştırmalı analizleri, karşılaşılan problemleri ve alınan mühendislik kararlarını tarih sırasıyla kayda geçirmektedir.

---

## 28.09.2026 — Problem ve Alan Sınırlarının Belirlenmesi
- **Amaç**: Modelin uzmanlaşacağı alanı belirlemek ve veri setinin aşırı dağınık bir yığına dönüşmesini önlemek.
- **Denenen**: Tüm Orta Afrika ülkelerini (Kamerun, Kongo, Gabon, Orta Afrika Cumhuriyeti) tek bir modelde birleştirmek.
- **Sonuç**: Ülkeler arası ormancılık kanunlarının, bakanlık yapılarının ve kurum isimlerinin çok farklı olması nedeniyle çözülemeyen varlık çelişkileri ve veri kirliliği oluştu.
- **Karar**: Kapsam yalnızca **Gabon Cumhuriyeti** olarak sınırlandırıldı. Üç tamamlayıcı sütun belirlendi: Biyoçeşitlilik (fauna/flora/parklar), Çevre Hukuku (Kanunlar ve kararnameler) ve Ulusal Sosyo-Ekonomik Göstergeler.

---

## 04.10.2026 — PDF Metin Çıkarma Araçlarının Karşılaştırılması (`PyMuPDF` ve `pdfplumber`)
- **Bağlam**: 85 adet resmi PDF dokümanı (kanunlar, koruma raporları, saha sayımları).
- **Deney**:
  - `PyMuPDF (fitz)`: 50 PDF belgesinde denendi. Toplam süre: ~34 saniye. Düz metin akışını başarıyla korudu, metadata alanlarını eksiksiz çıkardı.
  - `pdfplumber`: Aynı 50 PDF belgesinde denendi. Toplam süre: ~4 dakika 12 saniye. Tablo kenarlıklarını tespit etmekte başarılı ancak 100 sayfayı aşan belgelerde bellek tüketimi yüksek ve yavaş.
- **Problem**: 7 belgenin metin katmanı içermeyen taranmış görüntü (scan) olduğu fark edildi (`extraction_error`).
- **Karar**: Hız ve istikrar nedeniyle ana çıkarma motoru olarak **PyMuPDF** seçildi. Taranmış 7 belge ise ayrı bir OCR (*Tesseract* `fra`) akışına yönlendirildi.

---

## 09.10.2026 — Tekrar Eden Verileri Ayıklama: Hash ve MinHash Eşik Analizi
- **Bağlam**: Çeşitli bakanlık sitelerinden indirilen metinlerde aynı kanun ve istatistik tablolarının farklı dosya adlarıyla tekrar ettiği görüldü.
- **Deney**:
  - *1. Aşama*: SHA-256 ile tam eşleşme kontrolü yapıldı. **38 exact duplicate** tespit edilerek elendi.
  - *2. Aşama*: 128 permütasyonlu MinHash ve Jaccard benzerliği üzerinde farklı eşik değerleri 40 çift üzerinde elle incelendi:
    - Eşik 0.70: Farklı türlerin koruma maddelerini benzer şablon nedeniyle yanlışlıkla duplicate saydı (aşırı agresif).
    - Eşik 0.95: Sadece sonundaki imza tarihi farklı olan aynı kanun kopyalarını yakalayamadı (yetersiz).
    - Eşik 0.85: Farklı içerikleri korurken neredeyse aynı olan metinleri kusursuz ayıkladı.
- **Karar**: İki aşamalı filtreleme kabul edildi: Önce SHA-256, ardından $0.85$ eşikli MinHash + Jaccard ile **47 near duplicate** elendi.

---

## 14.10.2026 — Tür Koruma Statülerindeki Çelişkilerin Çözümü
- **Bağlam**: Farklı yıllara ait yayınlarda aynı tür için çelişkili IUCN statüleri tespit edildi (örneğin *Gorilla gorilla* 1996'da *Endangered*, 2016'da *Critically Endangered* olarak geçmişti).
- **Deney**: Eski veriyi doğrudan ezmek vs. çatışmayı kaydederek kronolojik öncelik vermek.
- **Karar**: Veri kaybını önlemek için `metadata/conflicts.json` dosyası oluşturuldu. En güncel tarihli bilimsel kaynağın statüsü geçerli kabul edilirken, geçmiş değişiklikler `change_log.jsonl` kütüğüne işlendi.

---

## 18.10.2026 — Bozuk Kodlama (Mojibake) Tespiti ve Temizleme
- **Bağlam**: Windows ortamındaki metin çıktılarında bazı Fransızca karakterlerin bozulduğu görüldü (`DǸmographique`, `d?Tenviron`, `ǽgǸes`).
- **Neden**: Windows konsol varsayılan kodlaması (CP1252/CP850) ile kaynak UTF-8 dosyalarının çakışması.
- **Çözüm**:
  - Çıkarma ve kaydetme işlemlerinin tamamında `encoding='utf-8'` zorunlu kılındı.
  - Unicode `NFKC` normalizasyonu standartlaştırıldı.
  - Bozuk karakter oranı %10'un üzerinde olan sayfaların doğrudan elenmesi kuralı getirildi.

---

## 22.10.2026 — Tokenizer Seçimi ve Token Hacmi Hesabı
- **Bağlam**: Final döneminde CPT yapılacak açık kaynak model ailesine göre token sayısını belirlemek.
- **Karar**: Çok dilli başarısı ve açık kaynak ağırlıkları nedeniyle **Qwen 2.5** (152k sözlük boyutu) referans tokenizer olarak seçildi. Domain Corpus v1.0 üzerinde toplam **3.395.898 token** hesaplandı.

---

## 25.10.2026 — Instruction Taksonomisi ve Alan Sınırı Örnekleri
- **Bağlam**: *Vize Rehberi* 11. Bölüm gerekliliklerinin karşılanması.
- **Tespit**: İlk instruction havuzunda basit gösterge sorularının oranı çok yüksekti ve modelin alan dışı sorularda sınırını bildirebileceği negatif örnekler yoktu.
- **Aksiyon**:
  - Örnekler dengelenerek 4.348 adede indirildi (rehberdeki 3.000–5.000 hedefi).
  - 104 adet alan dışı ret örneği (`bilgi_yetersizligi`) eklendi (uluslararası borsa, insan tıbbı, spor vb. konularda modelin sınırını belirtmesi sağlandı).
  - Doküman düzeyinde test kümesi izolasyonu tamamlanarak veri sızıntısı riski ortadan kaldırıldı.
