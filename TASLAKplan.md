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

