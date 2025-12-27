# MovieMind 🎬

MovieMind, modern bir React ön yüzü, güçlü bir Node.js arka yüzü ve gelişmiş Python tabanlı yapay zeka modellerini birleştiren, kişiselleştirilmiş film önerileri sunan kapsamlı bir film öneri sistemidir.

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Teknolojiler](#️-teknolojiler)
- [Proje Yapısı](#-proje-yapısı)
- [Kurulum](#-kurulum)
- [Uygulamayı Çalıştırma](#️-uygulamayı-çalıştırma)
- [Frontend](#-frontend)
- [Backend](#-backend)
- [AI Models](#-ai-models-yapay-zeka-modelleri)
- [API Endpoints](#-api-endpoints)
- [Öneri Algoritmaları](#-öneri-algoritmaları-detayları)
- [Katkıda Bulunanlar](#-katkıda-bulunanlar)
- [Lisans](#-lisans)

---

## 🚀 Özellikler

- **Çoklu Model Önerileri**:
  - **Model 1: Birliktelik Kuralları (Association Rules - Apriori):** Kullanıcıların birlikte beğendiği filmleri analiz ederek "X filmini seven Y filmini de sever" kuralları çıkarır.
  - **Model 2: İçerik Tabanlı Filtreleme (Content-Based Filtering):** Film türleri ve açıklamalarına göre benzer içerikli filmler önerir.
  - **Model 3: Öğe Tabanlı İşbirlikçi Filtreleme (Item-Based Collaborative Filtering):** Rating benzerliğine dayalı öneriler sunar.
- **Kullanıcı Profilleri**: İzleme listeleri, favoriler ve arkadaş sistemleri.
- **Sosyal Özellikler**: Arkadaş ekleme ve listelerini görüntüleme.
- **Gerçek Zamanlı Veri**: Güncel puanlar ve posterler için TMDB entegrasyonu.
- **Modern Arayüz**: Tailwind CSS ile oluşturulmuş karanlık temalı (dark mode), duyarlı tasarım.

---

## 🛠️ Teknolojiler

| Katman | Teknolojiler |
|--------|--------------|
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS, React Router |
| **Backend** | Node.js, Express, SQLite, Sequelize, JWT |
| **AI/ML** | Python, Flask, Pandas, Scikit-learn, Mlxtend |

---

## 📁 Proje Yapısı

```
MovieRecommender/
├── 📂 frontend/                    # React Frontend Uygulaması
│   ├── src/
│   │   ├── api/                    # Axios API yapılandırması
│   │   ├── components/             # React bileşenleri
│   │   │   └── Navbar.tsx
│   │   ├── context/                # React Context (Auth)
│   │   │   └── AuthContext.tsx
│   │   ├── pages/                  # Sayfa bileşenleri
│   │   │   ├── Home.tsx            # Ana sayfa
│   │   │   ├── Login.tsx           # Giriş sayfası
│   │   │   ├── Register.tsx        # Kayıt sayfası
│   │   │   ├── Profile.tsx         # Kullanıcı profili
│   │   │   ├── MovieDetail.tsx     # Film detay sayfası
│   │   │   └── UserProfile.tsx     # Diğer kullanıcı profili
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── 📂 backend/                     # Node.js Backend API
│   ├── src/
│   │   ├── config/                 # Yapılandırma dosyaları
│   │   │   ├── auth.js             # JWT ayarları
│   │   │   ├── db.js               # Veritabanı bağlantısı
│   │   │   └── recommenderServices.js  # AI servis bağlantısı
│   │   ├── middleware/             # Express middleware
│   │   │   └── authMiddleware.js   # JWT doğrulama
│   │   ├── models/                 # Sequelize modelleri
│   │   │   ├── User.js
│   │   │   ├── Movie.js
│   │   │   ├── Rating.js
│   │   │   └── Friendship.js
│   │   ├── routes/                 # API rotaları
│   │   │   ├── auth.js             # /api/auth
│   │   │   ├── users.js            # /api/users
│   │   │   ├── friends.js          # /api/friends
│   │   │   ├── movies.js           # /api/movies
│   │   │   └── recommendations.js  # /api/recommendations
│   │   ├── services/               # Harici servisler
│   │   │   ├── posterService.js
│   │   │   └── tmdbService.js
│   │   ├── seed/                   # Veritabanı seed
│   │   │   └── seedMovies.js
│   │   └── server.js               # Ana sunucu dosyası
│   ├── database.sqlite
│   └── package.json
│
├── 📂 ai-models/MovieRecommender/  # Python AI Modelleri
│   ├── api_server.py               # Flask API sunucusu
│   ├── src/
│   │   ├── recommender_arl.py      # Association Rules modülü
│   │   └── recommender_itemcf.py   # Item-Based CF modülü
│   ├── Content-Based/              # İçerik tabanlı öneri modülü
│   │   ├── data_pipeline.py        # Veri işleme ve TF-IDF
│   │   ├── recommender_content.py  # Öneri motoru
│   │   ├── user_profile.py         # Kullanıcı profili öneri
│   │   ├── evaluate_content.py     # Model değerlendirme
│   │   └── models/                 # Model dosyaları
│   ├── models/                     # ARL model dosyaları
│   │   ├── association_rules.pkl
│   │   ├── movie_mapping.pkl
│   │   └── item_similarity.pkl
│   ├── app/                        # Streamlit uygulamaları
│   │   ├── Home_🎬_Recommender.py
│   │   └── pages/
│   └── requirements.txt
│
├── 📂 data/                        # Veri dosyaları
│   ├── movies_metadata.csv
│   ├── ratings.csv / ratings_small.csv
│   ├── links.csv / links_small.csv
│   ├── keywords.csv
│   └── credits.csv
│
├── package.json                    # Root package.json (monorepo scripts)
├── requirements.txt                # Python bağımlılıkları (tüm AI modelleri için)
└── README.md
```

---

## 📦 Kurulum

### 1. Depoyu Klonlayın

```bash
git clone https://github.com/semihbekdas/MovieRecommender.git
cd MovieRecommender
```

### 2. Bağımlılıkları Yükleyin

Ana dizinde şu komutu çalıştırarak hem kök dizin, hem backend hem de frontend bağımlılıklarını yükleyebilirsiniz:

```bash
npm run install:all
```

### 3. Python Kurulumu

Python'un yüklü olduğundan emin olun. Gerekli Python paketlerini ana dizinden yükleyin:

```bash
pip install -r requirements.txt
```

### 4. Veritabanını Seed Edin (Opsiyonel)

Film verilerini veritabanına yüklemek için:

```bash
npm run seed
```

---

## 🏃‍♂️ Uygulamayı Çalıştırma

Tüm servisleri (Frontend, Backend, AI Sunucusu) ana dizinden tek bir komutla başlatabilirsiniz:

```bash
npm start
```

| Servis | URL | Açıklama |
|--------|-----|----------|
| **Frontend** | http://localhost:5173 | React web uygulaması |
| **Backend** | http://localhost:3000 | Node.js REST API |
| **AI Sunucusu** | http://localhost:9001 | Python Flask ML API |

---

## 💻 Frontend

React, TypeScript ve Tailwind CSS ile geliştirilmiş modern web arayüzü.

### Teknolojiler

- **React 19** - UI kütüphanesi
- **Vite** - Build aracı ve dev server
- **TypeScript** - Tip güvenliği
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Sayfa yönlendirme
- **Axios** - HTTP istemcisi

### Sayfalar

| Sayfa | Dosya | Açıklama |
|-------|-------|----------|
| Ana Sayfa | `Home.tsx` | Film listeleme ve arama |
| Giriş | `Login.tsx` | Kullanıcı girişi |
| Kayıt | `Register.tsx` | Yeni kullanıcı kaydı |
| Profil | `Profile.tsx` | Kullanıcı profili, favoriler, izleme listesi |
| Film Detay | `MovieDetail.tsx` | Film bilgileri ve puanlama |
| Kullanıcı Profili | `UserProfile.tsx` | Diğer kullanıcıların profilleri |

### Ayrı Çalıştırma

```bash
cd frontend
npm run dev
```

---

## ⚙️ Backend

Node.js ve Express ile geliştirilmiş RESTful API.

### Teknolojiler

- **Node.js** - Runtime
- **Express** - Web framework
- **SQLite** - Veritabanı
- **Sequelize** - ORM
- **JWT** - Kimlik doğrulama
- **bcryptjs** - Şifre hashleme

### Veritabanı Modelleri

| Model | Açıklama |
|-------|----------|
| `User` | Kullanıcı bilgileri (username, email, password) |
| `Movie` | Film bilgileri (title, overview, genres, poster) |
| `Rating` | Kullanıcı puanlamaları |
| `Friendship` | Arkadaşlık ilişkileri |

### Ayrı Çalıştırma

```bash
cd backend
npm start
```

---

## 🤖 AI Models (Yapay Zeka Modelleri)

Python ve Flask ile geliştirilmiş makine öğrenmesi modelleri.

### Teknolojiler

- **Python 3.10+** - Programlama dili
- **Flask** - Web framework
- **Pandas** - Veri işleme
- **Scikit-learn** - ML kütüphanesi
- **Mlxtend** - Association Rules için

### Modeller

| Model | Dosya | Açıklama |
|-------|-------|----------|
| Association Rules | `src/recommender_arl.py` | Apriori tabanlı birliktelik kuralları |
| Content-Based | `Content-Based/recommender_content.py` | TF-IDF + Cosine Similarity |
| Item-Based CF | `src/recommender_itemcf.py` | İşbirlikçi filtreleme |

### Streamlit Arayüzleri

```bash
cd ai-models/MovieRecommender/app
streamlit run Home_🎬_Recommender.py
```

### Ayrı Çalıştırma

```bash
cd ai-models/MovieRecommender
python api_server.py
```

---

## 🌐 API Endpoints

### Backend API (Port 3000)

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/api/auth/register` | Kullanıcı kaydı |
| POST | `/api/auth/login` | Kullanıcı girişi |
| GET | `/api/users/:id` | Kullanıcı bilgisi |
| GET | `/api/movies` | Film listesi |
| GET | `/api/movies/:id` | Film detayı |
| POST | `/api/movies/:id/rate` | Film puanlama |
| GET | `/api/friends` | Arkadaş listesi |
| POST | `/api/friends/add` | Arkadaş ekleme |
| GET | `/api/recommendations` | Öneri alma |

### AI API (Port 9001)

| Method | Endpoint | Model | Açıklama |
|--------|----------|-------|----------|
| POST | `/recommend` | Association Rules | Birliktelik kuralları tabanlı öneri |
| POST | `/recommend/content` | Content-Based | İçerik tabanlı öneri |
| POST | `/recommend/itemcf` | Item-Based CF | İşbirlikçi filtreleme önerisi |
| GET | `/health` | - | Sunucu durumu kontrolü |

### Örnek İstek (AI API)

```bash
curl -X POST http://localhost:9001/recommend \
  -H "Content-Type: application/json" \
  -d '{"liked_movies": ["Inception", "The Dark Knight"], "top_n": 5}'
```

---

## 🤖 Öneri Algoritmaları Detayları

Bu proje, Kaggle'daki "The Movies Dataset" üzerinde çalışan farklı makine öğrenmesi tekniklerini kullanır.

### 1. Association Rules (Birliktelik Kuralları)

**Nasıl Çalışır:**
1. Kullanıcıların beğendiği filmleri (puan ≥ 4.0) belirler.
2. Apriori algoritması ile sık film setlerini bulur.
3. "X → Y" kuralları çıkarır (Support, Confidence ve Lift metriklerine göre).

### 2. Content-Based Filtering (İçerik Tabanlı)

**Nasıl Çalışır:**
1. Film türleri (genres) ve açıklamalarını (overview) birleştirir.
2. TF-IDF vektörleştirme ile sayısal temsil oluşturur.
3. Cosine Similarity ile film benzerliklerini hesaplar.
4. Soğuk başlangıç (cold-start) problemi olmadan, sadece içeriğe bakarak öneri yapar.

### 3. Item-Based Collaborative Filtering (Öğe Tabanlı İşbirlikçi Filtreleme)

**Nasıl Çalışır:**
1. Kullanıcıların filmlere verdiği puanları (ratings) kullanır.
2. User-Item matrisi oluşturur.
3. Filmler arasındaki benzerliği Cosine Similarity ile hesaplar (Bu filmi beğenenler, şu filmi de beğendi mantığı).
4. Kullanıcının geçmişte yüksek puan verdiği filmlere matematiksel olarak en yakın (benzer) filmleri önerir.

---

## 📚 Veri Kaynağı

Bu proje Kaggle'daki **The Movies Dataset**'i kullanmaktadır:

- **Kaynak:** [The Movies Dataset - Kaggle](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset)
- **Film Sayısı:** ~45,000 film
- **Rating Sayısı:** ~26 milyon (tam) / ~100,000 (küçük)

---

## 👥 Katkıda Bulunanlar

Bu proje, farklı uzmanlık alanlarının birleşimiyle ortaya çıkmıştır:

- **Full Stack Geliştirme & Entegrasyon**: Projenin web altyapısı, frontend ve backend geliştirmesi.
- **Yapay Zeka & Veri Bilimi**: `ai-models` klasörü altındaki öneri sistemleri, veri analizi ve model eğitimi.

---

## 📝 Lisans

Bu proje eğitim amaçlı geliştirilmiştir.
