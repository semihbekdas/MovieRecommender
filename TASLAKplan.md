# 🎬 Film Öneri Sistemi - TASLAK Proje Planı

## 📋 Proje Özeti

| Bilgi | Değer |
|-------|-------|
| **Amaç** | 3 farklı öneri algoritması + web developer'lara çıktı |
| **Veri Seti** | MovieLens FULL (26M rating - `ratings.csv`) |
| **Ekip** | Veri bilimi (model) + Web geliştirme (arayüz) |

> ⚠️ **Önemli:** Tüm modeller büyük veri seti (`ratings.csv` - 26M rating) kullanacak.

---

## 🗂️ Proje Yapısı (Hedef)

```
Movie_Recommendations/
├── src/                          # 🎯 TÜM MODELLER BURADA
│   ├── __init__.py
│   ├── recommender_arl.py        # ✅ Mevcut
│   ├── recommender_itemcf.py     # ⏳ Oluşturulacak
│   └── recommender_content.py    # ⏳ Content-Based'den taşınacak
├── models/                       # Model artifact'ları
│   ├── arl/
│   ├── itemcf/
│   └── content/
├── data/raw/                     # Ham veriler
│   ├── ratings.csv               # 26M rating (KULLANILACAK)
│   ├── movies_metadata.csv
│   └── links.csv
├── output/                       # 🆕 Web developer çıktıları
│   ├── api.py
│   └── README.md
└── app/                          # Streamlit arayüzü
```

---

## 🎯 Model Durumu

| Model | Durum | Veri | Dosya |
|-------|-------|------|-------|
| **1. ARL** | ✅ Tamamlandı | ratings.csv | `src/recommender_arl.py` |
| **2. Content-Based** | 🔄 Taşınacak | movies_metadata.csv | `src/recommender_content.py` |
| **3. Item-based CF** | ⏳ Yapılacak | ratings.csv | `src/recommender_itemcf.py` |

---

## 📦 Model 1: Association Rules (ARL)

### Durum: ✅ TAMAMLANDI

**Mantık:** "Bu filmi beğenenler şunları da beğendi" - sepet analizi

**Dosya:** `src/recommender_arl.py`

**Artifact'lar:**
```
models/arl/
├── movie_mapping.pkl      # movieId → title (9K film)
├── association_rules.pkl  # Kurallar (41K+)
└── meta.json              # Parametreler
```

---

## 📦 Model 2: Content-Based Filtering

### Durum: 🔄 SRC'YE TAŞINACAK

**Mantık:** Film içeriği (tür + açıklama) benzerliği

**Mevcut Konum:** `Content-Based/`
**Hedef Konum:** `src/recommender_content.py`

**Artifact'lar:**
```
models/content/
├── tfidf_vectorizer.pkl
├── tfidf_matrix.npz
├── metadata.parquet
└── meta.json
```

---

## 📦 Model 3: Item-based Collaborative Filtering

### Durum: ⏳ YAPILACAK

**Mantık:** Rating benzerliğine göre film-film ilişkisi

**Dosya:** `src/recommender_itemcf.py`

**Artifact'lar:**
```
models/itemcf/
├── item_similarity.pkl    # Film-film benzerlik matrisi
├── movie_mapping.pkl      # movieId → title
└── meta.json              # Parametreler
```

---

## 🔄 Web Developer ile Veri Alışverişi

### Akış Şeması

```
┌─────────────────┐     REQUEST      ┌─────────────────┐
│   WEB FRONTEND  │ ───────────────► │   PYTHON API    │
│   (React/Vue)   │                  │   (Flask/Fast)  │
└─────────────────┘                  └─────────────────┘
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │   3 MODEL       │
                                     │   ARL/CF/CB     │
                                     └─────────────────┘
                                              │
                                              ▼
┌─────────────────┐     RESPONSE     ┌─────────────────┐
│   WEB FRONTEND  │ ◄─────────────── │   JSON ÇIKTI    │
└─────────────────┘                  └─────────────────┘
```

---

## 📥 WEB'DEN BİZE GELİCEK VERİ (REQUEST)

### İstek Formatı

```json
{
  "user_selection": {
    "liked_movies": [
      {
        "title": "Inception",
        "movieId": 27205
      },
      {
        "title": "Interstellar", 
        "movieId": 157336
      },
      {
        "title": "The Dark Knight",
        "movieId": 155
      }
    ],
    "top_n": 10,
    "model": "arl"
  }
}
```

### Alternatif Basit Format (Sadece başlık)

```json
{
  "liked_titles": ["Inception", "Interstellar", "The Dark Knight"],
  "top_n": 10,
  "model": "arl"
}
```

---

## 📤 BİZDEN WEB'E GİDECEK VERİ (RESPONSE)

### Başarılı Öneri Yanıtı

```json
{
  "status": "success",
  "model_used": "arl",
  "request_summary": {
    "liked_movies": ["Inception", "Interstellar", "The Dark Knight"],
    "top_n": 10
  },
  "recommendations": [
    {
      "rank": 1,
      "movieId": 49026,
      "title": "Django Unchained",
      "score": 4.29,
      "metrics": {
        "confidence": 0.467,
        "lift": 9.20,
        "support": 0.018
      },
      "metadata": {
        "genres": ["Drama", "Western"],
        "year": 2012,
        "vote_average": 8.0,
        "overview": "With the help of a German bounty hunter, a freed slave..."
      }
    },
    {
      "rank": 2,
      "movieId": 205596,
      "title": "The Imitation Game",
      "score": 3.46,
      "metrics": {
        "confidence": 0.367,
        "lift": 9.45,
        "support": 0.015
      },
      "metadata": {
        "genres": ["Biography", "Drama", "War"],
        "year": 2014,
        "vote_average": 8.1,
        "overview": "British mathematician Alan Turing helps crack the Enigma..."
      }
    },
    {
      "rank": 3,
      "movieId": 11324,
      "title": "Shutter Island",
      "score": 3.11,
      "metrics": {
        "confidence": 0.367,
        "lift": 8.47,
        "support": 0.016
      },
      "metadata": {
        "genres": ["Mystery", "Thriller"],
        "year": 2010,
        "vote_average": 8.2,
        "overview": "Two U.S. Marshals are sent to a remote island..."
      }
    }
  ],
  "missing_titles": [],
  "used_fallback": false,
  "generated_at": "2024-12-09T20:10:00Z"
}
```

### Model Bazlı Metrik Farklılıkları

**ARL Modeli için `metrics`:**
```json
{
  "confidence": 0.467,
  "lift": 9.20,
  "support": 0.018,
  "score": 4.29
}
```

**Content-Based Modeli için `metrics`:**
```json
{
  "similarity": 0.85,
  "genre_match": 0.80
}
```

**Item-based CF için `metrics`:**
```json
{
  "similarity": 0.78,
  "common_users": 1250
}
```

### Hata Yanıtı

```json
{
  "status": "error",
  "error_code": "MOVIE_NOT_FOUND",
  "error_message": "Şu filmler bulunamadı: ['Unknown Movie']",
  "partial_results": null
}
```

### Fallback Yanıtı (Film bulunamazsa)

```json
{
  "status": "success",
  "model_used": "arl",
  "recommendations": [...],
  "missing_titles": ["Unknown Movie"],
  "used_fallback": true,
  "fallback_reason": "Seçilen filmler için kural bulunamadı, popüler filmler önerildi"
}
```

---

## 🎬 Film Listesi Endpoint'i

Web'in film seçtirmesi için tüm filmleri listeleyeceğimiz endpoint:

### Request
```
GET /api/movies?search=inc&limit=20
```

### Response
```json
{
  "movies": [
    {
      "movieId": 27205,
      "title": "Inception",
      "year": 2010,
      "genres": ["Action", "Sci-Fi", "Thriller"],
      "vote_average": 8.4,
      "poster_path": "/9gk7adHYeDvHkCSEqAvQNLV5Ber.jpg"
    },
    {
      "movieId": 157336,
      "title": "Interstellar",
      "year": 2014,
      "genres": ["Adventure", "Drama", "Sci-Fi"],
      "vote_average": 8.6,
      "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg"
    }
  ],
  "total_count": 2
}
```

---

## 📋 Yapılacaklar Listesi

### Faz 1: Modelleri Tamamla
- [ ] ARL'yi büyük veri ile yeniden eğit (Google Colab)
- [ ] `src/recommender_content.py` oluştur (taşı)
- [ ] `src/recommender_itemcf.py` oluştur
- [ ] Tüm artifact'ları `models/` altına organize et

### Faz 2: API Katmanı
- [ ] `output/api.py` - Standart API wrapper
- [ ] JSON request/response handler
- [ ] Hata yönetimi

### Faz 3: Web Entegrasyonu
- [ ] Film listesi endpoint'i
- [ ] 3 model için tek endpoint
- [ ] CORS ve güvenlik ayarları

---

## 📦 Web Developer'a Teslim Paketi

```
teslim/
├── models/                    # Hazır model dosyaları
│   ├── arl/
│   ├── content/
│   └── itemcf/
├── api/
│   ├── api.py                 # Python API
│   ├── requirements.txt
│   └── example_usage.py
├── docs/
│   ├── API.md                 # Bu dokümandaki JSON formatları
│   ├── ENDPOINTS.md
│   └── examples/
│       ├── request.json
│       └── response.json
└── data/
    └── movie_catalog.json     # Film listesi (autocomplete için)
```

---

## 🎮 ÇALIŞMA AKIŞI - DETAYLI AÇIKLAMA

### Senaryo: Kullanıcı Film Önerisi Almak İstiyor

---

### ADIM 1: Kullanıcı Web Sitesinde Film Seçiyor

```
┌─────────────────────────────────────────────────────────────┐
│                    🎬 FİLM ÖNERİ SİTESİ                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Sevdiğiniz filmleri seçin:                               │
│   ┌─────────────────────────────────────────┐              │
│   │ 🔍 Film ara...                          │              │
│   └─────────────────────────────────────────┘              │
│                                                             │
│   ✅ Inception (2010)                                       │
│   ✅ Interstellar (2014)                                    │
│   ✅ The Dark Knight (2008)                                 │
│                                                             │
│   Öneri modeli:  ○ ARL  ● Content  ○ ItemCF                │
│                                                             │
│   [ 🎯 Önerileri Getir ]                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Kullanıcının yaptığı:**
- Arama kutusuna "Inception" yazıyor
- Dropdown'dan filmi seçiyor
- Birkaç film seçiyor
- Model seçiyor (opsiyonel, varsayılan olabilir)
- "Önerileri Getir" butonuna tıklıyor

---

### ADIM 2: Web (Frontend) Bizim API'mize İstek Gönderiyor

**HTTP Request:**
```
POST https://api.filmönerisi.com/recommend
Content-Type: application/json
```

**Request Body (Web'den bize gelen):**
```json
{
  "liked_movies": [
    {
      "movieId": 27205,
      "title": "Inception"
    },
    {
      "movieId": 157336,
      "title": "Interstellar"
    },
    {
      "movieId": 155,
      "title": "The Dark Knight"
    }
  ],
  "model": "arl",
  "top_n": 10
}
```

**Minimum Versiyon (Sadece title ile):**
```json
{
  "liked_titles": ["Inception", "Interstellar", "The Dark Knight"],
  "model": "arl",
  "top_n": 10
}
```

---

### ADIM 3: Bizim Backend Modeli Çalıştırıyor

```python
# API endpoint (Flask/FastAPI)
@app.post("/recommend")
def get_recommendations(request):
    liked_titles = request.liked_titles
    model = request.model  # "arl", "content", "itemcf"
    top_n = request.top_n
    
    if model == "arl":
        # ARL modeli çalışıyor
        results = recommender_arl.recommend_with_association_rules(
            liked_titles=liked_titles,
            top_n=top_n
        )
    elif model == "content":
        # Content-Based modeli çalışıyor
        results = recommender_content.recommend_multi(
            liked_titles=liked_titles,
            top_n=top_n
        )
    elif model == "itemcf":
        # Item-based CF modeli çalışıyor
        results = recommender_itemcf.recommend_item_based(
            liked_titles=liked_titles,
            top_n=top_n
        )
    
    return format_response(results)
```

**Model İç İşleyişi (ARL örneği):**
```
Kullanıcı seçimi: ["Inception", "Interstellar", "The Dark Knight"]
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Title → MovieId çevirme                                 │
│     "Inception" → 27205                                     │
│     "Interstellar" → 157336                                 │
│     "The Dark Knight" → 155                                 │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Kural eşleştirme                                        │
│     {155} → {49026}  (confidence: 0.47, lift: 9.2)         │
│     {27205, 155} → {11324}  (confidence: 0.37, lift: 8.5)  │
│     ...41,000+ kural taranıyor                              │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Skor hesaplama ve sıralama                              │
│     score = confidence × lift                               │
│     Django Unchained: 4.29                                  │
│     The Imitation Game: 3.46                                │
│     Shutter Island: 3.11                                    │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Metadata ekleme                                         │
│     - Film adı, yıl, tür, poster                           │
│     - TMDB/IMDB bilgileri                                   │
└─────────────────────────────────────────────────────────────┘
```

---

### ADIM 4: Bizden Web'e Response Gidiyor

**HTTP Response:**
```
HTTP/1.1 200 OK
Content-Type: application/json
```

**Response Body (Bizden web'e giden):**
```json
{
  "status": "success",
  "model_used": "arl",
  "input": {
    "liked_movies": ["Inception", "Interstellar", "The Dark Knight"],
    "top_n": 10
  },
  "output": {
    "total_recommendations": 10,
    "recommendations": [
      {
        "rank": 1,
        "movieId": 49026,
        "title": "Django Unchained",
        "year": 2012,
        "genres": ["Drama", "Western"],
        "poster_url": "https://image.tmdb.org/t/p/w500/7oWY8VDWW7thTzWh3OKYRkWUlD5.jpg",
        "vote_average": 8.0,
        "overview": "With the help of a German bounty hunter, a freed slave sets out to rescue his wife...",
        "metrics": {
          "score": 4.29,
          "confidence": 0.467,
          "lift": 9.20,
          "support": 0.018
        }
      },
      {
        "rank": 2,
        "movieId": 205596,
        "title": "The Imitation Game",
        "year": 2014,
        "genres": ["Biography", "Drama", "War"],
        "poster_url": "https://image.tmdb.org/t/p/w500/noUp0XOqIcmgefRnRZa1nhtRvWO.jpg",
        "vote_average": 8.1,
        "overview": "During World War II, mathematician Alan Turing tries to crack the Enigma code...",
        "metrics": {
          "score": 3.46,
          "confidence": 0.367,
          "lift": 9.45,
          "support": 0.015
        }
      },
      {
        "rank": 3,
        "movieId": 11324,
        "title": "Shutter Island",
        "year": 2010,
        "genres": ["Mystery", "Thriller"],
        "poster_url": "https://image.tmdb.org/t/p/w500/kve20tXwUZpu4GUX8l6X7Z4jmL6.jpg",
        "vote_average": 8.2,
        "overview": "Two U.S. marshals are sent to a psychiatric hospital on an island...",
        "metrics": {
          "score": 3.11,
          "confidence": 0.367,
          "lift": 8.47,
          "support": 0.016
        }
      }
    ]
  },
  "meta": {
    "generated_at": "2024-12-09T20:24:00Z",
    "processing_time_ms": 145,
    "model_version": "2024-12-09"
  }
}
```

---

### ADIM 5: Web Sitesi Önerileri Gösteriyor

```
┌─────────────────────────────────────────────────────────────┐
│                    🎬 SİZİN İÇİN ÖNERİLER                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ╔═══════════════════╗  ╔═══════════════════╗              │
│  ║ #1                ║  ║ #2                ║              │
│  ║ [POSTER]          ║  ║ [POSTER]          ║              │
│  ║ Django Unchained  ║  ║ The Imitation Game║              │
│  ║ ⭐ 8.0 | 2012     ║  ║ ⭐ 8.1 | 2014     ║              │
│  ║ Drama, Western    ║  ║ Biography, Drama  ║              │
│  ║ 📊 Skor: 4.29     ║  ║ 📊 Skor: 3.46     ║              │
│  ╚═══════════════════╝  ╚═══════════════════╝              │
│                                                             │
│  ╔═══════════════════╗  ╔═══════════════════╗              │
│  ║ #3                ║  ║ #4                ║              │
│  ║ [POSTER]          ║  ║ [POSTER]          ║              │
│  ║ Shutter Island    ║  ║ Sherlock Holmes   ║              │
│  ║ ⭐ 8.2 | 2010     ║  ║ ⭐ 7.6 | 2009     ║              │
│  ║ Mystery, Thriller ║  ║ Action, Adventure ║              │
│  ║ 📊 Skor: 3.11     ║  ║ 📊 Skor: 2.91     ║              │
│  ╚═══════════════════╝  ╚═══════════════════╝              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 VERİ AKIŞ ÖZETİ

```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│   KULLANICI  │        │     WEB      │        │   BİZ (ML)   │
│   (Tarayıcı) │        │  (Frontend)  │        │  (Backend)   │
└──────────────┘        └──────────────┘        └──────────────┘
       │                       │                       │
       │ 1. Film seçer         │                       │
       │──────────────────────►│                       │
       │                       │                       │
       │                       │ 2. JSON Request       │
       │                       │──────────────────────►│
       │                       │                       │
       │                       │    liked_titles       │
       │                       │    model: "arl"       │
       │                       │    top_n: 10          │
       │                       │                       │
       │                       │                      ┌┴┐
       │                       │                      │ │ 3. Model
       │                       │                      │ │    çalışır
       │                       │                      │ │
       │                       │                      └┬┘
       │                       │                       │
       │                       │ 4. JSON Response      │
       │                       │◄──────────────────────│
       │                       │                       │
       │                       │    recommendations[]  │
       │                       │    - title            │
       │                       │    - poster_url       │
       │                       │    - score            │
       │                       │    - genres           │
       │                       │                       │
       │ 5. Öneriler gösterir  │                       │
       │◄──────────────────────│                       │
       │                       │                       │
       ▼                       ▼                       ▼
```

---

## 🎯 WEB DEVELOPER'IN BİLMESİ GEREKENLER

### 1. Film Listesi Nasıl Alınır?

**Request:**
```
GET /api/movies?search=inc&limit=20
```

**Response:**
```json
{
  "movies": [
    {"movieId": 27205, "title": "Inception", "year": 2010, "poster_url": "..."},
    {"movieId": 49047, "title": "Gravity", "year": 2013, "poster_url": "..."}
  ]
}
```

### 2. Öneri Nasıl Alınır?

**Request:**
```
POST /api/recommend
{
  "liked_titles": ["Inception", "Interstellar"],
  "model": "arl",
  "top_n": 10
}
```

**Response:** (Yukarıdaki tam response örneği)

### 3. Hangi Model Ne Zaman Kullanılır?

| Model | Ne Zaman | Avantaj |
|-------|----------|---------|
| `arl` | Varsayılan | Hızlı, popüler kombinasyonlar |
| `content` | "Benzer içerik" isterse | Tür/açıklama bazlı |
| `itemcf` | "Beğenenler beğendi" isterse | Rating benzerliği |

### 4. Hata Durumları

```json
// Film bulunamadı
{"status": "error", "error_code": "MOVIE_NOT_FOUND", "message": "..."}

// Model hatası
{"status": "error", "error_code": "MODEL_ERROR", "message": "..."}

// Öneri yok (fallback kullanıldı)
{"status": "success", "used_fallback": true, "fallback_reason": "..."}
```

---

## 🎬 3 MODEL AYNI ANDA GÖSTERİLECEK

### Kullanıcı Deneyimi

Kullanıcı film seçtiğinde **3 model birden çalışacak** ve sonuçlar **yan yana 3 sütunda** gösterilecek:

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                           🎬 FİLM ÖNERİ SİSTEMİ                                    │
│                     Seçtiğiniz: Inception, Interstellar                            │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐  │
│  │   🛒 ARL MODELİ       │  │  📝 CONTENT-BASED    │  │  👥 ITEM-BASED CF     │  │
│  │  "Birlikte Alınanlar" │  │  "Benzer İçerik"     │  │  "Beğenenler Beğendi" │  │
│  ├───────────────────────┤  ├───────────────────────┤  ├───────────────────────┤  │
│  │ 1. Django Unchained   │  │ 1. Tenet             │  │ 1. Pulp Fiction       │  │
│  │    ⭐ Skor: 4.29      │  │    🎯 Benzerlik: 0.89 │  │    👍 Benzerlik: 0.82 │  │
│  │                       │  │                       │  │                       │  │
│  │ 2. Imitation Game     │  │ 2. Dunkirk           │  │ 2. Fight Club         │  │
│  │    ⭐ Skor: 3.46      │  │    🎯 Benzerlik: 0.85 │  │    👍 Benzerlik: 0.79 │  │
│  │                       │  │                       │  │                       │  │
│  │ 3. Shutter Island     │  │ 3. Memento           │  │ 3. The Matrix         │  │
│  │    ⭐ Skor: 3.11      │  │    🎯 Benzerlik: 0.82 │  │    👍 Benzerlik: 0.76 │  │
│  │                       │  │                       │  │                       │  │
│  │ 4. Sherlock Holmes    │  │ 4. Prestige          │  │ 4. Se7en              │  │
│  │    ⭐ Skor: 2.91      │  │    🎯 Benzerlik: 0.78 │  │    👍 Benzerlik: 0.73 │  │
│  │                       │  │                       │  │                       │  │
│  │ 5. Iron Man           │  │ 5. Source Code       │  │ 5. Goodfellas         │  │
│  │    ⭐ Skor: 2.78      │  │    🎯 Benzerlik: 0.75 │  │    👍 Benzerlik: 0.71 │  │
│  └───────────────────────┘  └───────────────────────┘  └───────────────────────┘  │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📥 YENİ REQUEST FORMATI (3 MODEL BİRDEN)

Web'den bize gelen istek:

```json
{
  "liked_titles": ["Inception", "Interstellar", "The Dark Knight"],
  "top_n": 5,
  "models": ["arl", "content", "itemcf"]
}
```

VEYA tek endpoint ile tüm modeller:

```json
{
  "liked_titles": ["Inception", "Interstellar", "The Dark Knight"],
  "top_n": 5
}
```
> Not: `models` belirtilmezse 3 model de çalışır

---

## 📤 YENİ RESPONSE FORMATI (3 MODEL BİRDEN)

Bizden web'e giden yanıt:

```json
{
  "status": "success",
  "input": {
    "liked_movies": ["Inception", "Interstellar", "The Dark Knight"],
    "top_n": 5
  },
  "results": {
    "arl": {
      "model_name": "Association Rules",
      "description": "Bu filmleri beğenenler şunları da beğendi",
      "icon": "🛒",
      "recommendations": [
        {
          "rank": 1,
          "movieId": 49026,
          "title": "Django Unchained",
          "year": 2012,
          "genres": ["Drama", "Western"],
          "poster_url": "https://image.tmdb.org/t/p/w500/7oWY8VDWW7.jpg",
          "vote_average": 8.0,
          "metrics": {
            "score": 4.29,
            "confidence": 0.467,
            "lift": 9.20
          }
        },
        {
          "rank": 2,
          "movieId": 205596,
          "title": "The Imitation Game",
          "year": 2014,
          "genres": ["Biography", "Drama"],
          "poster_url": "https://image.tmdb.org/t/p/w500/noUp0X.jpg",
          "vote_average": 8.1,
          "metrics": {
            "score": 3.46,
            "confidence": 0.367,
            "lift": 9.45
          }
        }
      ]
    },
    "content": {
      "model_name": "Content-Based",
      "description": "Benzer içerikli filmler",
      "icon": "📝",
      "recommendations": [
        {
          "rank": 1,
          "movieId": 577922,
          "title": "Tenet",
          "year": 2020,
          "genres": ["Action", "Sci-Fi", "Thriller"],
          "poster_url": "https://image.tmdb.org/t/p/w500/k68nP.jpg",
          "vote_average": 7.3,
          "metrics": {
            "similarity": 0.89,
            "genre_match": 0.95
          }
        },
        {
          "rank": 2,
          "movieId": 374720,
          "title": "Dunkirk",
          "year": 2017,
          "genres": ["Action", "Drama", "War"],
          "poster_url": "https://image.tmdb.org/t/p/w500/ebSnO.jpg",
          "vote_average": 7.9,
          "metrics": {
            "similarity": 0.85,
            "genre_match": 0.80
          }
        }
      ]
    },
    "itemcf": {
      "model_name": "Item-based CF",
      "description": "Bu filmleri yüksek puanlayan kullanıcıların beğendiği filmler",
      "icon": "👥",
      "recommendations": [
        {
          "rank": 1,
          "movieId": 680,
          "title": "Pulp Fiction",
          "year": 1994,
          "genres": ["Crime", "Drama"],
          "poster_url": "https://image.tmdb.org/t/p/w500/dM2w.jpg",
          "vote_average": 8.5,
          "metrics": {
            "similarity": 0.82,
            "common_users": 15420
          }
        },
        {
          "rank": 2,
          "movieId": 550,
          "title": "Fight Club",
          "year": 1999,
          "genres": ["Drama"],
          "poster_url": "https://image.tmdb.org/t/p/w500/bptf.jpg",
          "vote_average": 8.4,
          "metrics": {
            "similarity": 0.79,
            "common_users": 12350
          }
        }
      ]
    }
  },
  "meta": {
    "generated_at": "2024-12-09T20:28:00Z",
    "processing_time_ms": 320,
    "models_used": ["arl", "content", "itemcf"]
  }
}
```

---

## 📊 3 MODEL KARŞILAŞTIRMA TABLOSU

| Özellik | ARL | Content-Based | Item-based CF |
|---------|-----|---------------|---------------|
| **İkon** | 🛒 | 📝 | 👥 |
| **Başlık** | Birlikte Alınanlar | Benzer İçerik | Beğenenler Beğendi |
| **Metrik Adı** | Score | Similarity | Similarity |
| **Ek Metrik** | confidence, lift | genre_match | common_users |
| **Açıklama** | Market sepet analizi | Tür/açıklama benzerliği | Rating benzerliği |

---

## 🔄 VERİ AKIŞI (3 MODEL)

```
                           ┌─────────────────┐
                           │  KULLANICI      │
                           │  Film seçiyor   │
                           └────────┬────────┘
                                    │
                                    ▼
                           ┌─────────────────┐
                           │  WEB FRONTEND   │
                           │  Request gönder │
                           └────────┬────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     │              │              │
                     ▼              ▼              ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │   ARL    │  │ CONTENT  │  │ ITEM-CF  │
              │  Model   │  │  Model   │  │  Model   │
              └────┬─────┘  └────┬─────┘  └────┬─────┘
                   │             │             │
                   └──────────┬──┴─────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  BİRLEŞİK JSON  │
                     │  3 model sonucu │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  WEB FRONTEND   │
                     │  3 sütun göster │
                     └─────────────────┘
```

---

