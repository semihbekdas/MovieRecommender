# 📝 Content-Based Filtering - Yol Haritası

## 🎯 Bu Doküman Ne İçin?

Bu doküman, Content-Based Filtering (İçerik Tabanlı Filtreleme) modelini anlamak ve uygulamak için hazırlanmış kapsamlı bir rehberdir.

---

## 📚 BÖLÜM 1: KAVRAMSAL ANLAYIŞ

### 1.1 Content-Based Filtering Nedir?

Content-Based Filtering, **filmlerin kendine özgü özelliklerine** (içeriğine) bakarak öneri yapan bir yöntemdir. Diğer kullanıcıların ne izlediğini veya ne puanladığını **hiç bilmese bile** çalışabilir.

**Temel Mantık:**
> "Aksiyon filmi seviyorsan, sana başka aksiyon filmleri öneririm."

Bu yöntem şu soruyu sorar:
- "Bu filmin **içeriği** (türü, açıklaması, yönetmeni, oyuncuları) neye benziyor?"
- "Kullanıcının sevdiği filmlerin içeriğine benzer başka filmler hangileri?"

---

### 1.2 Diğer Yöntemlerden Farkları

#### Association Rules (ARL) vs Content-Based

| Özellik | Association Rules | Content-Based |
|---------|-------------------|---------------|
| **Veri kaynağı** | Rating matrisi (userId, movieId, rating) | Film metadata (genres, overview, cast) |
| **Mantık** | "A'yı seven B'yi de sever" (birliktelik) | "A'ya benzeyen filmler hangileri?" (içerik benzerliği) |
| **Kullanıcı bilgisi** | Tüm kullanıcıların davranışına bakar | Sadece senin geçmişine bakar |
| **Cold start** | Yeni film için kural üretemez | Yeni filmin metadata'sı varsa hemen öneri yapabilir |

#### Item-based CF vs Content-Based

| Özellik | Item-based CF | Content-Based |
|---------|---------------|---------------|
| **Benzerlik hesabı** | Rating pattern'lerine göre | İçerik özelliklerine göre |
| **Veri kaynağı** | userId-movieId-rating | genres, overview, keywords, cast |
| **Örnek** | "Bu filmi beğenenler şunu da beğendi" | "Bu film aksiyon, o da aksiyon" |
| **Cold start** | Yeni film için rating yoksa çalışmaz | Metadata varsa hemen çalışır |

#### Özet: Üç Yöntemin Karşılaştırması

```
ARL:         [User Behaviors] → Birliktelik Kuralları → Öneri
Item-CF:     [User Ratings]   → Rating Benzerliği    → Öneri  
Content:     [Film Features]  → İçerik Benzerliği    → Öneri
```

---

### 1.3 Content-Based Nasıl Çalışır?

#### Adım 1: Film Özelliklerini Topla

Her film için "içerik profili" oluşturulur:

```
Film: Inception
├── Genres: Action, Sci-Fi, Thriller
├── Overview: "A thief who steals corporate secrets through dream-sharing technology..."
├── Keywords: dream, subconscious, heist (opsiyonel)
└── Cast/Crew: Leonardo DiCaprio, Christopher Nolan (opsiyonel)
```

#### Adım 2: Metin Birleştirme

Bu özellikler tek bir metin haline getirilir:

```
content = "Action Sci-Fi Thriller A thief who steals corporate secrets through dream-sharing technology..."
```

#### Adım 3: TF-IDF Vektörleştirme

**TF-IDF Nedir?**
- **TF (Term Frequency):** Bir kelimenin o belgede kaç kez geçtiği
- **IDF (Inverse Document Frequency):** Kelimenin tüm belgelerde ne kadar nadir olduğu
- **TF-IDF = TF × IDF:** Hem sık geçen hem de ayırt edici kelimelere yüksek skor

**Örnek:**
- "the" kelimesi her filmde geçer → düşük IDF → düşük TF-IDF
- "dream" kelimesi sadece Inception gibi filmlerde geçer → yüksek IDF → yüksek TF-IDF

**Sonuç:** Her film bir sayı vektörüne dönüşür:

```
Inception:    [0.12, 0.45, 0.00, 0.89, 0.23, ...]  (5000 boyutlu vektör)
Interstellar: [0.08, 0.42, 0.15, 0.91, 0.18, ...]
Titanic:      [0.01, 0.05, 0.78, 0.02, 0.65, ...]
```

#### Adım 4: Cosine Similarity (Kosinüs Benzerliği)

**Cosine Similarity Nedir?**

İki vektör arasındaki açının kosinüsünü hesaplar:
- **1.0:** Tamamen aynı yönde (çok benzer)
- **0.0:** Dik açı (hiç benzemez)
- **-1.0:** Tam zıt yönde (çok zıt)

**Formül:**
```
similarity(A, B) = (A · B) / (||A|| × ||B||)
```

**Görsel Anlayış:**
```
           Inception
              ↗
             /  θ = 15° → similarity = 0.97 (çok benzer)
            /
Interstellar ←————————————— Titanic
                θ = 75° → similarity = 0.26 (az benzer)
```

#### Adım 5: En Benzer Filmleri Bul

Kullanıcı "Inception" seçtiğinde:
1. Inception'ın TF-IDF vektörünü al
2. Diğer tüm filmlerle cosine similarity hesapla
3. En yüksek similarity skoruna sahip filmleri sırala
4. İlk N tanesini öner

---

### 1.4 Avantajlar ve Dezavantajlar

#### ✅ Avantajlar

1. **Cold Start Çözümü:** Yeni eklenen bir film için metadata varsa hemen öneri yapabilir
2. **Şeffaflık:** "Bu film sana şundan dolayı önerildi: Aksiyon + Sci-Fi" açıklanabilir
3. **Bağımsızlık:** Diğer kullanıcıların davranışına ihtiyaç duymaz
4. **Niş İçerik:** Az izlenen ama içeriği benzer filmleri bulabilir

#### ❌ Dezavantajlar

1. **Filter Bubble (Filtre Balonu):** Hep aynı türde filmler önerir, çeşitlilik azalır
2. **Metadata Kalitesi:** Kötü/eksik açıklamalar kötü önerilere yol açar
3. **Yüzeysel Benzerlik:** İki film aynı türde olsa bile kalite farkı yakalanmaz
4. **Serendipity Eksikliği:** "Sürpriz" öneriler üretmez, tahmin edilebilir

---

## 📊 BÖLÜM 2: VERİ KAYNAKLARI

### 2.1 Ana Veri Dosyası

Content-Based için kullanılacak dosya: **`movies_metadata.csv`**

| Kolon | Açıklama | Kullanım |
|-------|----------|----------|
| `id` | TMDB ID | Film eşleştirme |
| `title` | Film adı | Gösterim |
| `genres` | Tür listesi (JSON) | **Ana içerik özelliği** |
| `overview` | Film açıklaması | **Metin benzerliği** |
| `vote_average` | Ortalama puan | Opsiyonel filtreleme |
| `vote_count` | Oy sayısı | Opsiyonel popülerlik |

### 2.2 Genres Formatı

`genres` kolonu JSON string formatında:

```json
[{"id": 28, "name": "Action"}, {"id": 878, "name": "Science Fiction"}]
```

Bu parse edilip listeye çevrilecek:
```python
["Action", "Science Fiction"]
```

### 2.3 Opsiyonel Veri Kaynakları (İleride Eklenebilir)

| Dosya | İçerik | Faydası |
|-------|--------|---------|
| `keywords.csv` | Film anahtar kelimeleri | Daha spesifik benzerlik |
| `credits.csv` | Oyuncu ve yönetmen bilgisi | "Nolan filmleri" gibi öneriler |

---

## 🔧 BÖLÜM 3: TEKNİK KAVRAMLAR

### 3.1 TF-IDF Detaylı Açıklama

```
TF-IDF = Term Frequency × Inverse Document Frequency
```

**Term Frequency (TF):**
```
TF(t, d) = (t teriminin d belgesindeki sayısı) / (d belgesindeki toplam terim sayısı)
```

**Inverse Document Frequency (IDF):**
```
IDF(t) = log(Toplam belge sayısı / t terimini içeren belge sayısı)
```

**Örnek Hesaplama:**

```
Corpus: 3 film
- Film 1: "action adventure action"
- Film 2: "drama romance"  
- Film 3: "action drama"

"action" için Film 1'de TF-IDF:
- TF = 2/3 = 0.67
- IDF = log(3/2) = 0.405
- TF-IDF = 0.67 × 0.405 = 0.27
```

### 3.2 Cosine Similarity Detaylı Açıklama

**Formül:**
```
cos(θ) = (A · B) / (||A|| × ||B||)

Burada:
- A · B = Σ(Ai × Bi)  (dot product)
- ||A|| = √(Σ Ai²)    (vektör normu)
```

**Örnek Hesaplama:**

```
Film A: [0.5, 0.3, 0.0]
Film B: [0.4, 0.2, 0.1]

A · B = (0.5×0.4) + (0.3×0.2) + (0.0×0.1) = 0.26
||A|| = √(0.25 + 0.09 + 0) = 0.583
||B|| = √(0.16 + 0.04 + 0.01) = 0.458

similarity = 0.26 / (0.583 × 0.458) = 0.97
```

### 3.3 Sparse Matrix

TF-IDF sonucu oluşan matris genellikle **sparse** (seyrek) olur:
- Çoğu hücre 0 değerindedir
- Her film sadece belirli kelimeleri içerir
- Memory tasarrufu için sparse format kullanılır

---

## 🛠️ BÖLÜM 4: UYGULAMA ADIMLARI (Kod Aşaması İçin)

### Faz 1: Veri Hazırlığı
- [ ] `movies_metadata.csv` dosyasını yükle
- [ ] Gerekli kolonları seç (id, title, genres, overview)
- [ ] `id` kolonunu integer'a çevir
- [ ] Duplikatları temizle
- [ ] `genres` JSON'ını parse et → liste yap

### Faz 2: İçerik Oluşturma
- [ ] Her film için content string oluştur (genres + overview)
- [ ] Boş content olanları filtrele
- [ ] NaN değerleri temizle

### Faz 3: Vektörleştirme
- [ ] TfidfVectorizer ile content'leri vektörleştir
- [ ] max_features parametresini ayarla (5000-20000)
- [ ] stop_words='english' kullan

### Faz 4: Benzerlik Hesaplama
- [ ] cosine_similarity ile film-film matrisi oluştur
- [ ] Matrisi DataFrame'e çevir (index = tmdb_id)
- [ ] Dosyaya kaydet (content_similarity.pkl)

### Faz 5: Öneri Fonksiyonu
- [ ] Title → tmdb_id eşlemesi oluştur
- [ ] Tek film için benzer filmler fonksiyonu yaz
- [ ] Çoklu film için ortalama benzerlik fonksiyonu yaz
- [ ] Test et

### Faz 6: Streamlit Entegrasyonu
- [ ] Modülü import et
- [ ] Algoritma seçimine "Content-Based" ekle
- [ ] Kart gösterimini güncelle (genres, overview snippet)
- [ ] Test et

---

## 📁 BÖLÜM 5: DOSYA YAPISI

```
MovieRecommender/
├── data/
│   └── raw/
│       └── movies_metadata.csv    ← GEREKLİ VERİ
├── docs/
│   └── content-based/
│       ├── YOL_HARITASI.md        ← BU DOSYA
│       └── NOTLAR.md              ← (opsiyonel) kişisel notlar
├── models/
│   ├── content_similarity.pkl     ← Oluşturulacak
│   ├── content_metadata.pkl       ← Oluşturulacak
│   └── content_meta.json          ← Oluşturulacak
├── src/
│   ├── recommender_arl.py         ← Mevcut
│   ├── recommender_itemcf.py      ← Yapılacak (2. model)
│   └── recommender_content.py     ← Yapılacak (3. model)
└── app/
    └── Home_🎬_Recommender.py     ← Güncellenecek
```

---

## 📖 BÖLÜM 6: TEMEL KAVRAMLAR SÖZLÜĞÜ

| Kavram | Açıklama |
|--------|----------|
| **Content Profile** | Bir filmin özelliklerinden oluşan profil (genres + overview) |
| **TF-IDF** | Metni sayısal vektöre çeviren yöntem |
| **Cosine Similarity** | İki vektör arasındaki benzerliği ölçen metrik (0-1) |
| **Feature Extraction** | Ham veriden (metin) anlamlı özellikler çıkarma |
| **Vectorization** | Metni sayısal forma dönüştürme |
| **Sparse Matrix** | Çoğu değeri 0 olan matris (TF-IDF sonucu) |
| **Cold Start** | Yeni kullanıcı/film için veri eksikliği problemi |
| **Filter Bubble** | Sadece benzer içerik önerme sorunu |
| **Serendipity** | Beklenmedik ama hoşa giden öneriler |

---

## ❓ KONTROL SORULARI

Kavramları anladığını test et:

1. **TF-IDF'de "IDF" ne işe yarar?**
   - Cevap: Nadir kelimelere daha yüksek ağırlık verir

2. **Cosine similarity 0.95 ne anlama gelir?**
   - Cevap: İki film çok benzer içeriğe sahip

3. **Content-Based'in Item-CF'den farkı nedir?**
   - Cevap: CB film özelliklerine bakar, Item-CF rating pattern'lerine bakar

4. **Filter Bubble problemi nedir?**
   - Cevap: Hep aynı türde öneri yaparak çeşitliliği azaltma

5. **Cold start problemi Content-Based'de var mı?**
   - Cevap: Kısmen çözülmüş - metadata varsa yeni filmler için de çalışır

---

## 🚀 SONRAKİ ADIM

Bu dokümanı anladıktan sonra:
1. `movies_metadata.csv` dosyasını `data/raw/` klasörüne koy
2. Kod yazmaya başla (`src/recommender_content.py`)

Hazır olduğunda haber ver! 🎬

