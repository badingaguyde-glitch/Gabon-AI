# Gabon Ulusal Bilgi Tabanı ve Biyoçeşitlilik — Instruction Dataset v1.0

## Amaç
Bu veri seti, final döneminde gerçekleştirilecek **supervised fine-tuning (SFT)** işleminde doğrudan kullanılmak üzere hazırlanmıştır. CPT aşamasından çıkan alana uyarlanmış temel modele, kullanıcı talimatlarını doğru anlama, kaynaklara sadık kalarak cevap verme ve uzmanlık alanı dışındaki sorulara sınırlarını bildirerek yanıt verme davranışı kazandırmayı hedefler.

## Veri Formatı
Veri seti JSON Lines (`data/final/instruction_v1.0.jsonl`) biçiminde saklanmaktadır. Her satır, modern `messages` formatı (OpenAI / Llama-3 / Qwen / Mistral uyumlu) ile birlikte *Vize Rehberi* tarafından talep edilen tam izlenebilirlik alanlarını içerir:

```json
{
  "id": "INS_000124",
  "source_document": "DOC-d34928f8e00e",
  "task_type": "valeur_indicateur",
  "category": "economie",
  "instruction": "2021 yılında Gabon'un GSYİH büyüme oranı ne kadardı?",
  "response": "Dünya Bankası verilerine göre, 2021 yılında Gabon Cumhuriyeti'nin GSYİH büyüme oranı, pandemi sonrası toparlanmanın etkisiyle %1,5 olarak gerçekleşmiştir.",
  "generation_method": "semi_automatique_verifie",
  "verified_by": "equipe_projet_controle_qualite",
  "verified": true,
  "messages": [
    {
      "role": "user",
      "content": "2021 yılında Gabon'un GSYİH büyüme oranı ne kadardı?"
    },
    {
      "role": "assistant",
      "content": "Dünya Bankası verilerine göre, 2021 yılında Gabon Cumhuriyeti'nin GSYİH büyüme oranı, pandemi sonrası toparlanmanın etkisiyle %1,5 olarak gerçekleşmiştir."
    }
  ]
}
```

## Taksonomi ve Görev Dağılımı
*Vize Rehberi* 11. Bölümünde önerilen hedef büyüklük (3.000 ile 5.000 örnek) aralığına tam uyularak, **4.348 adet talimat-cevap çifti** dengeli biçimde hazırlanmıştır:

| Görev Türü | Fonksiyonel Açıklama | Örnek Sayısı | Oran (%) |
| :--- | :--- | :--- | :--- |
| **valeur_indicateur** | İstatistiksel gösterge, sayısal değer, yıl ve birim çıkarma | 1.793 | %41,2 |
| **attribution_juridique** | Bir konuyu düzenleyen kanun, kararname veya yetkili kurum tespiti | 847 | %19,5 |
| **analyse_article_loi** | Kanun maddesinin kapsamı, yükümlülükleri ve cezai analizi | 563 | %12,9 |
| **analyse_tendance** | Çok yıllık değişim ve sosyo-ekonomik eğilim analizi | 338 | %7,8 |
| **situation_recente** | Ulusal göstergelerin son bilinen durumunun raporlanması | 238 | %5,5 |
| **definition_concept** | Ekolojik ve hukuki terimlerin teknik tanımları | 221 | %5,1 |
| **explication_synthese** | Teknik rapor ve bilimsel metinlerin özetlenmesi | 171 | %3,9 |
| **bilgi_yetersizligi** *(Zorunlu)* | **Alan dışı sorularda sınırını bildirme ve kibar ret** | **104** | **%2,4** |
| **profil_biodiversite** | Tür tanıtımı (yaşam alanı, IUCN koruma statüsü, tehditler) | 43 | %1,0 |
| **taxonomie_espece** | Bilimsel isimler, eş anlamlılar ve yerel adlar | 22 | %0,5 |
| **contexte_reglementaire** | Kanun ön sözleri ve anayasal gerekçeler | 4 | %0,1 |
| **methodologie_enquete** | Demografik araştırma örneklem planı ve anket yöntemleri | 4 | %0,1 |
| **Toplam** | | **4.348** | **%100,0** |

## Görev Türlerinden Örnekler

### 1. Kanun Maddesi Analizi (`analyse_article_loi`)
- **Kullanıcı**: *Gabon Orman Kanunu'nun 12. maddesi sürdürülebilir orman işletmeciliği konusunda ne emretmektedir?*
- **Asistan**: *Madde 12, orman imtiyaz hakkına sahip tüm işletmecilerin, Su ve Orman İdaresi tarafından onaylanmış beş yıllık bir yönetim planı hazırlamasını ve uygulamasını zorunlu kılmaktadır. Bu plan, ağaç türlerinin kendini yenilemesini ve kesim rotasyonunu güvence altına almalıdır.*

### 2. İstatistiksel Gösterge Değeri (`valeur_indicateur`)
- **Kullanıcı**: *Ulusal istatistiklere göre Gabon topraklarının yüzde kaçı ormanlarla kaplıdır?*
- **Asistan**: *Gabon'un ormanlık alanı, toplam kara yüzölçümünün yaklaşık %88'ini (yaklaşık 235.000 km²) kaplamaktadır. Bu oran Gabon'u Kongo Havzası'nın en yoğun orman varlığına sahip ülkelerinden biri ve kritik bir küresel karbon yutağı yapmaktadır.*

### 3. Biyoçeşitlilik Profili (`profil_biodiversite`)
- **Kullanıcı**: *Afrika orman filinin Gabon'daki koruma durumu nedir ve en çok hangi parklarda görülür?*
- **Asistan**: *Afrika orman fili (*Loxodonta cyclotis*), IUCN tarafından "Kritik Düzeyde Tehlikede" (CR) olarak sınıflandırılmıştır. Gabon, dünyada kalan orman fillerinin %50 ila %60'ına ev sahipliği yapmakta olup tür özellikle Loango, Ivindo, Minkébé ve Lopé Millî Parklarında korunmaktadır.*

### 4. Alan Dışı Soruda Sınırını Bildirme (`bilgi_yetersizligi` — Zorunlu Kategori)
- **Kullanıcı**: *Dün Wall Street borsasında Apple hissesinin kapanış fiyatı ne oldu?*
- **Asistan**: *Bu soruya cevap veremem. Benim uzmanlık alanım Gabon Cumhuriyeti'nin biyoçeşitliliği, çevre mevzuatı, tarihi ve ulusal sosyo-ekonomik göstergeleri ile sınırlandırılmıştır. Uluslararası borsa ve finans verilerine sahip değilim.*

## Üretim Yöntemi ve Doğrulama
Örnekler 3 aşamalı kontrollü bir yöntemle hazırlanmıştır:
1. **Yapılandırılmış Veriden Üretim** (%65): `all_facts.json` ve Dünya Bankası göstergelerinden üretilmiş, matematiksel ve sayısal doğruluğu kesinleştirilmiş pairesel sorular.
2. **Doküman Bağlamlı Üretim** (%33): Gerçek kanun maddeleri ve saha araştırmalarından çıkarılan, farklı soru kalıplarıyla zenginleştirilmiş örnekler.
3. **Deontolojik ve Sınır Belirleme Örnekleri** (%2,4): Modelin bilmediği konularda uydurmasını engellemek üzere tasarlanmış negatif kontrol soruları.

Her örnek, kaynak dokümanın kimliğini taşıyan `source_document` alanı ile etiketlenmiştir.

## Kalite Kontrolü
Rastgele seçilen **150 talimat örneği** üzerinde yapılan manuel kontrolde:
- *Kullanıcı sorusunun anlaşılırlığı*: %98,0 başarı.
- *Cevabın kaynak dokümanla tutarlılığı ve doğruluk*: %97,3 başarı.
- *Görev türü ile içerik uyumu*: %99,3 başarı.
- *Asistan üslubu ve sınır belirleme kalitesi*: %98,7 başarı.

Tespit edilen 4 küçük anlatım kusuru v1.0 sürümünde düzeltilmiştir.

## Veri Ayrımı ve Veri Sızıntısını Önleme
Instruction seti oluşturulurken, **Corpus test kümesinde yer alan dokümanlardan çıkarılan örnekler eğitim kümesine kesinlikle dahil edilmemiştir**. Böylece değerlendirme sırasında modelin daha önce ezberlediği bilgiyi tekrar etmesi (data leakage) engellenmiştir.
