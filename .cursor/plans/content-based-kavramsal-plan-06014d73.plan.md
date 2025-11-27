<!-- 06014d73-07ac-4622-8521-6efc0c340952 26f1eb8c-30f5-49c4-946b-db5d3996fcf2 -->
# Content-Based Filtering (İçerik Tabanlı Filtreleme) Kavramsal Rehber

## 1. Content-Based Filtering Nedir?

Content-Based Filtering, **filmlerin kendine özgü özelliklerine** (içeriğine) bakarak öneri yapan bir yöntemdir. Diğer kullanıcıların ne izlediğini veya ne puanladığını **hiç bilmese bile** çalışabilir.

**Temel mantık:**

> "Aksiyon filmi seviyorsan, sana başka aksiyon filmleri öneririm."

Bu yöntem şu soruyu sorar:

- "Bu filmin **içeriği** (türü, açıklaması, yönetmeni, oyuncuları) neye benziyor?"
- "Kullanıcının sevdiği filmlerin içeriğine benzer başka filmler hangileri?"

---

## 2. Diğer Yöntemlerden Farkları

### 2.1 ARL (Association Rules) vs Content-Based

| Özellik | Association Rules | Content-Based |

|---------|-------------------|---------------|

| **Veri kaynağı** | Rating matrisi (userId, movieId, rating) | Film metadata (genres, overview, cast) |

| **Mantık** | "A'yı seven B'yi de sever" (birliktelik) | "A'ya benzeyen filmler hangileri?" (içerik benzerliği) |

| **Kullanıcı bilgisi** | Tüm kullanıcıların davranışına bakar | Sadece senin geçmişine bakar |

| **Cold start** | Yeni film için kural üretemez | Yeni filmin metadata'sı varsa hemen öneri yapabilir |

### 2.2 Item-based CF vs Content-Based

| Özellik | Item-based CF | Content-Based |

|---------|---------------|---------------|

| **Benzerlik hesabı** | Rating pattern'lerine göre | İçerik özelliklerine göre |

| **Veri kaynağı** | userId-movieId-rating | genres, overview, keywords, cast |

| **Örnek** | "Bu filmi beğenenler şunu da beğendi" | "Bu film aksiyon, o da aksiyon" |

| **Cold start** | Yeni film için rating yoksa çalışmaz | Metadata varsa hemen çalışır |

### 2.3 Özet: Üç Yöntemin Karşılaştırması

```
ARL:         [User Behaviors] → Birliktelik Kuralları → Öneri
Item-CF:     [User Ratings]   → Rating Benzerliği    → Öneri  
Content:     [Film Features]  → İçerik Benzerliği    → Öneri
```

---

## 3. Content-Based Nasıl Çalışır?

### Adım 1: Film Özelliklerini Topla

Her film için "içerik profili" oluşturulur:

```
Film: Inception
├── Genres: Action, Sci-Fi, Thriller
├── Overview: "A thief who steals corporate secrets through dream-sharing technology..."
├── Keywords: dream, subconscious, heist (opsiyonel)
└── Cast/Crew: Leonardo DiCaprio, Christopher Nolan (opsiyonel)
```

### Adım 2: Metin Birleştirme

Bu özellikler tek bir metin haline getirilir:

```
content = "Action Sci-Fi Thriller A thief who steals corporate secrets through dream-sharing technology..."
```

### Adım 3: TF-IDF Vektörleştirme

**TF-IDF Nedir?**

- **TF (Term Frequency):** Bir kelimenin o belgede kaç kez geçtiği
- **IDF (Inverse Document Frequency):** Kelimenin tüm belgelerde ne kadar nadir olduğu
- **TF-IDF = TF × IDF:** Hem sık geçen hem de ayırt edici kelimelere yüksek skor

**Örnek:**

- "the" kelimesi her filmde geçer → düşük IDF → düşük TF-IDF
- "dream" kelimesi sadece Inception gibi filmlerde geçer → yüksek IDF → yüksek TF-IDF

**Sonuç:** Her film bir sayı vektörüne dönüşür:

```
Inception:   [0.12, 0.45, 0.00, 0.89, 0.23, ...]  (5000 boyutlu vektör)
Interstellar: [0.08, 0.42, 0.15, 0.91, 0.18, ...]
Titanic:      [0.01, 0.05, 0.78, 0.02, 0.65, ...]
```

### Adım 4: Cosine Similarity (Kosinüs Benzerliği)

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

### Adım 5: En Benzer Filmleri Bul

Kullanıcı "Inception" seçtiğinde:

1. Inception'ın TF-IDF vektörünü al
2. Diğer tüm filmlerle cosine similarity hesapla
3. En yüksek similarity skoruna sahip filmleri sırala
4. İlk N tanesini öner

---

## 4. Projedeki Veri Kaynakları

Content-Based için kullanılacak dosya: `movies_metadata.csv`

| Kolon | Açıklama | Kullanım |

|-------|----------|----------|

| `id` | TMDB ID | Film eşleştirme |

| `title` | Film adı | Gösterim |

| `genres` | Tür listesi (JSON) | Ana içerik özelliği |

| `overview` | Film açıklaması | Metin benzerliği |

| `vote_average` | Ortalama puan | Opsiyonel filtreleme |

| `vote_count` | Oy sayısı | Opsiyonel popülerlik |

**Genres formatı (JSON string):**

```json
[{"id": 28, "name": "Action"}, {"id": 878, "name": "Science Fiction"}]
```

Bu parse edilip listeye çevrilecek: `["Action", "Science Fiction"]`

---

## 5. Content-Based Avantajları

1. **Cold Start Çözümü:** Yeni eklenen bir film için metadata varsa hemen öneri yapabilir
2. **Şeffaflık:** "Bu film sana şundan dolayı önerildi: Aksiyon + Sci-Fi" açıklanabilir
3. **Bağımsızlık:** Diğer kullanıcıların davranışına ihtiyaç duymaz
4. **Niş İçerik:** Az izlenen ama içeriği benzer filmleri bulabilir

## 6. Content-Based Dezavantajları

1. **Filter Bubble (Filtre Balonu):** Hep aynı türde filmler önerir, çeşitlilik azalır
2. **Metadata Kalitesi:** Kötü/eksik açıklamalar kötü önerilere yol açar
3. **Yüzeysel Benzerlik:** İki film aynı türde olsa bile kalite farkı yakalanmaz
4. **Serendipity Eksikliği:** "Sürpriz" öneriler üretmez, tahmin edilebilir

---

## 7. Önemli Kavramlar Özeti

| Kavram | Açıklama |

|--------|----------|

| **Content Profile** | Bir filmin özelliklerinden oluşan profil (genres + overview) |

| **TF-IDF** | Metni sayısal vektöre çeviren yöntem |

| **Cosine Similarity** | İki vektör arasındaki benzerliği ölçen metrik (0-1) |

| **Feature Extraction** | Ham veriden (metin) anlamlı özellikler çıkarma |

| **Vectorization** | Metni sayısal forma dönüştürme |

| **Sparse Matrix** | Çoğu değeri 0 olan matris (TF-IDF sonucu) |

---

## 8. Sonraki Adımlar

Bu kavramları anladıktan sonra kod aşamasına geçilecek:

1. `movies_metadata.csv`'den genre ve overview çekme
2. TF-IDF vektörleştirme (`sklearn.feature_extraction.text.TfidfVectorizer`)
3. Cosine similarity matrisi hesaplama
4. Öneri fonksiyonu yazma
5. Streamlit entegrasyonu