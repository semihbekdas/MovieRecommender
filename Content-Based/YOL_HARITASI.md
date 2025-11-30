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

### 5.1 API Referansı (Hızlı Bakış)

- **`Content-Based/data_pipeline.py`**
  - `parse_args()` → CLI parametrelerini (kaynak dosya, ngram ayarları, `--rebuild`) okur.
  - `run_pipeline(args)` → metadata temizliği + TF-IDF eğitimi + artefakt kaydı (`models/`).
- **`Content-Based/recommender_content.py`**
  - `load_artifacts(force_reload=False)` → TF-IDF matrisini ve metadata'yı cache'ler.
  - `titles_to_ids(titles, bundle)` → Başlıkları TMDB id listesine çevirir.
  - `recommend_single(movie_id, top_n, method)` / `recommend_multi(movie_ids, top_n, method)` → Standart öneriler.
  - `cli_recommend(titles, top_n, method)` → CLI çıktısını DataFrame olarak döndürür.
- **`Content-Based/user_profile.py`**
  - `build_user_profile(movie_ids, ratings=None)` → TF-IDF vektörlerinin (opsiyonel rating ağırlıklı) normalize ortalaması.
  - `recommend_with_profile(titles, ratings=None, top_n=10)` → Profil tabanlı öneri + fallback.
- **`Content-Based/evaluate_content.py`**
  - `evaluate(ratings_path, links_path, n_users, top_n, mode, rating_threshold, ...)` → HitRate@N çıktısı.

### 5.2 CLI Komutları

Planlanan akış şu komutlarla uçtan uca denenebilir:

```bash
# Artefaktları yeniden üret
python3 Content-Based/data_pipeline.py --rebuild

# Standart içerik tabanlı öneri
python3 Content-Based/recommender_content.py --titles "Inception,Interstellar" --top-n 5

# User profile yaklaşımı
python3 Content-Based/user_profile.py --titles "Inception,Interstellar,The Matrix" --ratings "5,4.5,4"

# HitRate@N değerlendirmesi
python3 Content-Based/evaluate_content.py --n-users 100 --top-n 10 --mode profile
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

## 🎯 BÖLÜM 7: GELİŞMİŞ - USER PROFILE YAKLAŞIMI (Opsiyonel)

### 7.1 User Profile Nedir?

Standart Content-Based'de:
- Kullanıcı bir film seçer → O filme benzer filmler önerilir

**User Profile yaklaşımında:**
- Kullanıcının **tüm sevdiği filmlerin** TF-IDF vektörleri birleştirilir
- Ortaya bir "**kullanıcı içerik profili**" çıkar
- Bu profil ile tüm filmlerin benzerliği hesaplanır

### 7.2 Neden User Profile?

| Standart Yaklaşım | User Profile Yaklaşımı |
|-------------------|------------------------|
| "Inception'a benzer filmler" | "Senin zevkine benzer filmler" |
| Tek filme odaklanır | Tüm izleme geçmişini değerlendirir |
| Anlık öneri | Kümülatif profil |

### 7.3 User Profile Nasıl Oluşturulur?

#### Yöntem 1: Basit Ortalama

Kullanıcının sevdiği filmlerin TF-IDF vektörlerinin ortalaması:

```
user_profile = mean(tfidf_vectors[liked_movies])
```

**Örnek:**
```
Kullanıcı şunları sevdi:
- Inception:    [0.5, 0.3, 0.0, 0.8]
- Interstellar: [0.4, 0.4, 0.1, 0.7]
- The Matrix:   [0.6, 0.2, 0.0, 0.9]

User Profile = [(0.5+0.4+0.6)/3, (0.3+0.4+0.2)/3, (0.0+0.1+0.0)/3, (0.8+0.7+0.9)/3]
             = [0.50, 0.30, 0.03, 0.80]
```

#### Yöntem 2: Rating Ağırlıklı Ortalama (Daha İyi!)

Kullanıcının verdiği puana göre ağırlıklandırma:

```
user_profile = weighted_mean(tfidf_vectors[liked_movies], weights=ratings)
```

**Formül:**
```
user_profile = Σ(rating_i × tfidf_vector_i) / Σ(rating_i)
```

**Örnek:**
```
Kullanıcının puanları:
- Inception:    5.0 puan → [0.5, 0.3, 0.0, 0.8]
- Interstellar: 4.0 puan → [0.4, 0.4, 0.1, 0.7]
- The Matrix:   3.0 puan → [0.6, 0.2, 0.0, 0.9]

Toplam ağırlık = 5 + 4 + 3 = 12

User Profile = (5×[0.5,0.3,0.0,0.8] + 4×[0.4,0.4,0.1,0.7] + 3×[0.6,0.2,0.0,0.9]) / 12

Hesaplama:
- Boyut 1: (5×0.5 + 4×0.4 + 3×0.6) / 12 = (2.5 + 1.6 + 1.8) / 12 = 0.49
- Boyut 2: (5×0.3 + 4×0.4 + 3×0.2) / 12 = (1.5 + 1.6 + 0.6) / 12 = 0.31
- Boyut 3: (5×0.0 + 4×0.1 + 3×0.0) / 12 = (0.0 + 0.4 + 0.0) / 12 = 0.03
- Boyut 4: (5×0.8 + 4×0.7 + 3×0.9) / 12 = (4.0 + 2.8 + 2.7) / 12 = 0.79

User Profile = [0.49, 0.31, 0.03, 0.79]
```

**Fark:** Yüksek puan verilen filmler profile daha çok katkı sağlar!

### 7.4 User Profile ile Öneri

1. User profile vektörünü oluştur
2. Tüm filmlerle cosine similarity hesapla
3. İzlenmiş filmleri çıkar
4. En yüksek benzerliğe sahip filmleri öner

```python
# Pseudo kod
user_profile = compute_user_profile(liked_movies, ratings, tfidf_matrix)
similarities = cosine_similarity([user_profile], tfidf_matrix)[0]
recommendations = get_top_n(similarities, exclude=liked_movies, n=10)
```

### 7.5 Görsel Karşılaştırma

```
STANDART YAKLAŞIM:
                    Inception ←→ Film X (benzerlik hesapla)
                              ←→ Film Y
                              ←→ Film Z

USER PROFILE YAKLAŞIMI:
    Inception  ─┐
    Interstellar ─┼→ [USER PROFILE] ←→ Film X (benzerlik hesapla)
    The Matrix ─┘                   ←→ Film Y
                                    ←→ Film Z
```

### 7.6 Avantajlar ve Dezavantajlar

#### ✅ Avantajlar
1. **Daha Kişisel:** Tüm izleme geçmişini değerlendirir
2. **Rating Duyarlı:** Çok sevilen filmler daha etkili
3. **Tutarlı Öneriler:** Anlık değil, kümülatif tercih yansıtır
4. **Çeşitlilik:** Farklı türlerden sevilen filmler profilde dengelenir

#### ❌ Dezavantajlar
1. **Hesaplama Maliyeti:** Her kullanıcı için ayrı profil
2. **Profil Güncellemesi:** Yeni film eklendikçe güncellenmeli
3. **Başlangıç Sorunu:** Az film izlemiş kullanıcıda zayıf profil

### 7.7 Kod Yapısı (Uygulama İçin Rehber)

```python
def build_user_profile(
    liked_movie_ids: list[int],
    ratings: list[float] | None,  # None ise basit ortalama
    tfidf_matrix: sparse_matrix,
    movie_id_to_idx: dict
) -> np.ndarray:
    """
    Kullanıcı içerik profili oluşturur.
    
    Args:
        liked_movie_ids: Beğenilen film ID'leri
        ratings: Her film için kullanıcı puanı (opsiyonel)
        tfidf_matrix: Tüm filmlerin TF-IDF matrisi
        movie_id_to_idx: movie_id → matris index eşlemesi
    
    Returns:
        user_profile: (n_features,) boyutunda vektör
    """
    # 1. Beğenilen filmlerin TF-IDF vektörlerini al
    indices = [movie_id_to_idx[mid] for mid in liked_movie_ids]
    vectors = tfidf_matrix[indices].toarray()
    
    # 2. Ağırlıklı ortalama hesapla
    if ratings is None:
        # Basit ortalama
        user_profile = vectors.mean(axis=0)
    else:
        # Rating ağırlıklı ortalama
        weights = np.array(ratings).reshape(-1, 1)
        user_profile = (vectors * weights).sum(axis=0) / weights.sum()
    
    return user_profile


def recommend_with_user_profile(
    user_profile: np.ndarray,
    tfidf_matrix: sparse_matrix,
    exclude_ids: list[int],
    top_n: int = 10
) -> pd.DataFrame:
    """
    User profile ile öneri üret.
    """
    # Tüm filmlerle benzerlik
    similarities = cosine_similarity([user_profile], tfidf_matrix)[0]
    
    # İzlenmiş filmleri çıkar ve sırala
    # ...
    
    return recommendations
```

### 7.8 Uygulama Seçenekleri

Bu proje için iki seçenek var:

| Seçenek | Açıklama | Karmaşıklık |
|---------|----------|-------------|
| **A) Basit** | Sadece film-film benzerliği (standart) | ⭐ |
| **B) Gelişmiş** | User Profile + rating ağırlıklı | ⭐⭐⭐ |

**Önerim:** Önce **Seçenek A**'yı tamamla, çalıştıktan sonra **Seçenek B**'yi ekle.

---

## 📈 BÖLÜM 8: DEĞERLENDİRME (Model Testi)

### 8.1 Neden Değerlendirme?

Model öneri üretiyor ama öneriler gerçekten iyi mi? Bunu ölçmek için basit bir test yapabiliriz.

### 8.2 Test Yaklaşımı: Leave-One-Out

`ratings_small.csv` dosyasını kullanarak kabaca test edebilirsin:

```
1. Bir kullanıcı seç (örn: userId = 42)
2. Bu kullanıcının sevdiği filmlerden BİRİNİ GİZLE
3. Kalan filmlerle Content-Based öneri üret
4. Gizlediğin film, öneri listesinde var mı?
```

**Görsel:**
```
Kullanıcı 42'nin sevdiği filmler:
[Inception, Interstellar, The Matrix, Fight Club, Memento]
         ↓
Gizle: "The Matrix"
         ↓
Kalan filmlerle öneri üret: [Inception, Interstellar, Fight Club, Memento]
         ↓
Öneriler: [Dark Knight, Prestige, THE MATRIX, Shutter Island, ...]
                                    ↑
                            GİZLENEN FİLM BULUNDU! ✅
```

### 8.3 Temel Metrik: Hit Rate@N

**Hit Rate@N:** Gizlenen film, önerilen ilk N film içinde mi?

```
Hit@10 = Gizlenen film top-10'da mı? (1 veya 0)
```

**Birden fazla kullanıcı için:**
```
Hit Rate@10 = (Hit olan kullanıcı sayısı) / (Toplam test kullanıcısı)
```

**Örnek:**
```
100 kullanıcı test edildi
72 kullanıcıda gizlenen film top-10'da çıktı

Hit Rate@10 = 72 / 100 = 0.72 = %72
```

### 8.4 Basit Değerlendirme Kodu (Pseudo)

```python
def evaluate_content_based(ratings_df, tfidf_matrix, n_users=100, top_n=10):
    """
    Content-Based modeli için Hit Rate@N hesapla.
    """
    hits = 0
    tested = 0
    
    # Rastgele kullanıcılar seç
    users = ratings_df['userId'].unique()
    sample_users = random.sample(list(users), min(n_users, len(users)))
    
    for user_id in sample_users:
        # Kullanıcının sevdiği filmler (rating >= 4)
        liked = ratings_df[
            (ratings_df['userId'] == user_id) & 
            (ratings_df['rating'] >= 4)
        ]['movieId'].tolist()
        
        if len(liked) < 3:  # En az 3 film olmalı
            continue
        
        # Rastgele bir filmi gizle
        hidden_movie = random.choice(liked)
        remaining = [m for m in liked if m != hidden_movie]
        
        # Kalan filmlerle öneri üret
        recommendations = recommend_content_based(remaining, top_n=top_n)
        recommended_ids = recommendations['movieId'].tolist()
        
        # Gizlenen film önerilerde var mı?
        if hidden_movie in recommended_ids:
            hits += 1
        
        tested += 1
    
    hit_rate = hits / tested if tested > 0 else 0
    return hit_rate, hits, tested
```

### 8.5 Yorumlama

| Hit Rate@10 | Yorum |
|-------------|-------|
| > 0.50 | İyi performans |
| 0.30 - 0.50 | Kabul edilebilir |
| < 0.30 | İyileştirme gerekli |

**Not:** Bu basit bir değerlendirme. Gerçek projelerde daha sofistike metrikler kullanılır (NDCG, MAP, Precision@K, Recall@K).

### 8.6 Diğer Basit Metrikler (Opsiyonel)

| Metrik | Açıklama |
|--------|----------|
| **MRR** (Mean Reciprocal Rank) | Gizlenen film kaçıncı sırada? (1/rank) |
| **Coverage** | Öneri sisteminin kaç farklı film önerdiği |
| **Diversity** | Önerilen filmlerin birbirine ne kadar farklı olduğu |

---

## 🚀 SONRAKİ ADIM

Bu dokümanı anladıktan sonra:
1. Veri zaten `Content-Based/` klasöründe ✅
2. Kod yazmaya başla (`src/recommender_content.py`)

**Uygulama Sırası:**
1. Önce standart Content-Based'i tamamla
2. Çalıştıktan sonra User Profile özelliğini ekle

Hazır olduğunda haber ver! 🎬

