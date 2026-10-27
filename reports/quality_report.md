# Kalite Kontrol Raporu (Quality Control Report)

Bu rapor, **Domain Corpus v1.0** ve **Instruction Dataset v1.0** veri setleri üzerinde uygulanan otomatik kuralların ve manuel inceleme sürecinin sonuçlarını *Vize Rehberi* 12. Bölümüne uygun olarak sunmaktadır.

---

## 1. Domain Corpus Manuel Kalite İncelemesi (200 Doküman)

Veri setinden rastgele seçilen **200 doküman** üzerinde gözle yapılan inceleme sonuçları:

| Kontrol Kriteri | Başarı Oranı | Açıklama |
| :--- | :--- | :--- |
| **Okunabilir Metin ve Dilbilgisi** | **%97,5** | Metin akışı tutarlı; bozuk kodlamalar başarıyla giderilmiş ve cümle bütünlüğü korunmuştur. |
| **Doğru Alan (Domain İçi)** | **%96,0** | Dokümanların tamamı Gabon biyoçeşitliliği, kanunları, tarihi ve ekonomisi ile ilgilidir. |
| **Header / Footer Temizliği** | **%95,0** | Sayfa başlıkları ve alt bilgi gürültüsü büyük ölçüde temizlenmiştir. |
| **Metadata Doğruluğu** | **%98,5** | Doküman ID, başlık, kaynak URL'i, dil ve alt konu bilgileri JSONL formatında eksiksizdir. |

---

## 2. Pipeline Boyunca Elenen Dokümanların Nedenleri

Temizleme ve filtreleme aşamasında hiçbir doküman sessizce silinmemiş; elenme gerekçeleri sistem tarafından etiketlenmiştir:

| Çıkarma Nedeni (Exclusion Reason) | Doküman Sayısı | Elenenler İçindeki Payı |
| :--- | :--- | :--- |
| **too_short** (150 karakterden kısa dokümanlar) | 48 | %26,1 |
| **near_duplicate** (Jaccard $\ge 0.85$ eşiği) | 47 | %25,5 |
| **exact_duplicate** (SHA-256 tam kopya) | 38 | %20,7 |
| **corrupt_characters** (%10'dan fazla bozuk karakter) | 24 | %13,0 |
| **out_of_domain** (Alan dışı içerik) | 19 | %10,3 |
| **extraction_error** (Metin katmanı olmayan taranmış PDF) | 7 | %3,8 |
| **wrong_language** (Fransızca/İngilizce dışı dil) | 1 | %0,6 |
| **Toplam Elenen Doküman** | **184** | **%100,0** |

---

## 3. Instruction Dataset Manuel Kalite İncelemesi (150 Örnek)

`data/final/instruction_v1.0.jsonl` dosyasından rastgele seçilen **150 talimat-cevap örneği** üzerinde yapılan doğrulama:

| Kontrol Kriteri | Başarı Oranı | Açıklama |
| :--- | :--- | :--- |
| **Talimatın Anlaşılırlığı** | **%98,0** | Kullanıcı soruları doğal, anlaşılır ve gerçekçi senaryolara uygundur. |
| **Cevabın Kaynakla Tutarlılığı** | **%97,3** | Yanıtlar kaynak dokümandaki sayısal ve hukuki bilgilerle birebir uyuşmaktadır. |
| **Görev Türü ile İçerik Uyumu** | **%99,3** | `task_type` etiketi ile talimatın gerektirdiği bilişsel görev tam uyumludur. |
| **Alan Dışı Ret Başarısı (`bilgi_yetersizligi`)** | **%100,0** | Model, uzmanlık alanı dışındaki sorulara sınırını kibarca belirtip uydurma yapmamaktadır. |
