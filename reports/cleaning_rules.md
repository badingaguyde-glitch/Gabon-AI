# Temizleme ve Ön İşleme Kuralları (Cleaning Rules)

Bu belge, Gabon LLM projesinde ham metinlere uygulanan temizleme, normalizasyon ve filtreleme kurallarını ve bu kuralların teknik gerekçelerini *Vize Rehberi* 7. Bölümüne uygun olarak açıklamaktadır.

---

## 1. Temizleme Kuralları Tablosu

| Kural Adı | Ne Yapar | Neden / Gerekçe |
| :--- | :--- | :--- |
| **Unicode NFKC Normalizasyonu** | Farklı kodlamalardaki karakter varyantlarını ve birleşik sembolleri tek biçime çeker | Farklı işletim sistemleri ve PDF motorlarının ürettiği kodlama uyumsuzluklarını giderir. |
| **Tekrarlayan Başlık / Alt Bilgi Tespiti** | Aynı belgede 5 sayfadan fazla tekrar eden üst ve alt bilgi satırlarını siler | Modelin dikkatini dağıtan ve bilgi taşımayan sayfa numarası ve kurum başlığı gürültüsünü temizler. |
| **Whitespace Normalizasyonu** | Ardışık boşlukları ve tabları teke indirir; 2'den fazla ardışık satır sonunu çift satır sonuna çeker | PDF sütun hizalamasından kaynaklanan bozuk satır bölünmelerini ve anlamsız boşlukları giderir. |
| **Kısa Yalnız Satır Eşiği** | 20 karakterden kısa ve noktalama işareti içermeyen tekil satırları siler | Menü kalıntıları, izole sayfa numaraları ve kırpılmış başlık parçalarını eler. |
| **Bozuk Kodlama (Mojibake) Düzeltmesi** | Transkodlama hatalarını (`DǸmographique` -> `Démographique`, `d?T` -> `d'`) düzeltir | Fransızca ve yerel dillerdeki metinlerin dil bilgisi doğruluğunu ve okunabilirliğini geri kazandırır. |
| **Sayı ve Sembollerin Korunması** | `Art. 12`, `%88`, `Loxodonta cyclotis`, `FCFA` gibi teknik ifadeleri ve sayıları korur | **Kritik Kural**: Agresif regex kuralları sayıları silerse kanun maddeleri, orman yüzölçümleri ve tarihler anlamını tamamen yitirir. |

---

## 2. Somut Öncesi / Sonrası Örneği (Before / After)

### Ham Çıkarılan Metin (ÖNCE):
```text
Sayfa 14
RÉPUBLIQUE GABONAISE | MINISTÈRE DES EAUX ET FORÊTS
DIRECTION GÉNÉRALE DES ÉCOSYSTÈMES AQUATIQUES
Sommaire | Textes | Contact

Art.     24.   -   Dans     les     parcs     nationaux,     toute     activité
d'exploitation     minière,     forestière     ou     agricole     est
strictement     interdite     conformément     à     la     loi     n°     03/2007.

www.eaux-forets.gouv.ga
14
```

### Temizlenmiş Metin (SONRA):
```text
Art. 24. - Dans les parcs nationaux, toute activité d'exploitation minière, forestière ou agricole est strictement interdite conformément à la loi n° 03/2007.
```

---

## 3. Doküman Çıkarma ve Filtreleme Kriterleri

Bir doküman aşağıdaki durumlarda nihai veri setine dahil edilmez ve çıkarma nedeni kaydedilir:
1. **Aşırı kısa doküman (`too_short`)**: Metin uzunluğunun 150 karakterin altında olması.
2. **Bozuk karakter oranı (`corrupt_characters`)**: Metindeki tanınmayan veya bozuk karakter oranının %10'u aşması.
3. **Alan dışı içerik (`out_of_domain`)**: Gabon, Kongo Havzası veya biyoçeşitlilik ile ilgisi olmayan metinler.
4. **İzin verilmeyen dil (`wrong_language`)**: Fransızca veya İngilizce dışındaki dillerde kalan belgeler.
