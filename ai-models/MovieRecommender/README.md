# 🎬 MovieRecommender - Film Öneri Sistemi

Farklı öneri algoritmalarını (Association Rules, Content-Based Filtering) kullanarak kişiselleştirilmiş film önerileri sunan kapsamlı bir film öneri sistemi.

---

## 📋 İçindekiler

- [Proje Hakkında](#-proje-hakkında)
- [Özellikler](#-özellikler)
- [Proje Yapısı](#-proje-yapısı)
- [Gereksinimler](#-gereksinimler)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Öneri Algoritmaları](#-öneri-algoritmaları)
- [Streamlit Arayüzleri](#-streamlit-arayüzleri)
- [Geliştirme Durumu](#-geliştirme-durumu)
- [Gelecek Planlar](#-gelecek-planlar)
- [Veri Kaynağı](#-veri-kaynağı)

---

## 🎯 Proje Hakkında

Bu proje, farklı makine öğrenmesi tekniklerini kullanarak film öneri sistemi geliştirmeyi amaçlar. Kaggle'daki "The Movies Dataset" üzerinde çalışır ve şu anda iki farklı öneri yaklaşımı içerir:

1. **Association Rules (Birliktelik Kuralları):** Kullanıcıların birlikte beğendiği filmleri analiz ederek "X filmini seven Y filmini de sever" kuralları çıkarır.
2. **Content-Based Filtering (İçerik Tabanlı):** Film türleri ve açıklamalarına göre benzer içerikli filmler önerir.

---

## ✨ Özellikler

### ✅ Tamamlanan Özellikler

| Özellik | Açıklama | Durum |
|---------|----------|-------|
| **Association Rules Backend** | Apriori algoritması ile birliktelik kuralları çıkarımı | ✅ Tamamlandı |
| **Content-Based Backend** | TF-IDF + Cosine Similarity ile içerik benzerliği | ✅ Tamamlandı |
| **Ana Öneri Arayüzü** | ARL tabanlı film önerileri sunan Streamlit uygulaması | ✅ Tamamlandı |
| **Dataset Insights** | Veri analizi ve görselleştirme sayfası | ✅ Tamamlandı |
| **Content-Based Test Paneli** | İçerik tabanlı modelin test ve değerlendirme arayüzü | ✅ Tamamlandı |
| **HitRate Değerlendirmesi** | Model performans metriği hesaplama | ✅ Tamamlandı |
| **CLI Araçları** | Komut satırından model oluşturma ve öneri alma | ✅ Tamamlandı |

### 🔄 Geliştirme Aşamasında

| Özellik | Açıklama | Durum |
|---------|----------|-------|
| **Item-based CF** | Rating benzerliğine dayalı işbirlikçi filtreleme | 📋 Planlandı |
| **Algoritma Entegrasyonu** | Tüm algoritmaları tek arayüzde birleştirme | 📋 Planlandı |
| **Model Karşılaştırması** | 3 farklı algoritmanın sonuçlarını yan yana gösterme | 📋 Planlandı |

---

## 📁 Proje Yapısı

```
MovieRecommender/
├── 📂 app/                              # Streamlit uygulamaları
│   ├── Home_🎬_Recommender.py           # Ana öneri sayfası (ARL tabanlı)
│   └── pages/
│       └── 1_📊_Dataset_Insights.py     # Veri analizi sayfası
│
├── 📂 Content-Based/                    # İçerik tabanlı öneri modülü
│   ├── data_pipeline.py                 # Veri işleme ve TF-IDF oluşturma
│   ├── recommender_content.py           # Öneri motoru
│   ├── user_profile.py                  # Kullanıcı profili tabanlı öneri
│   ├── evaluate_content.py              # Model değerlendirme (HitRate)
│   ├── README.md                        # Modül dokümantasyonu
│   ├── YOL_HARITASI.md                  # Kavramsal açıklamalar
│   └── models/                          # Oluşturulan model dosyaları
│       ├── tfidf_vectorizer.pkl         # TF-IDF Vectorizer
│       ├── tfidf_matrix.npz             # Sparse TF-IDF matrisi
│       ├── metadata.parquet             # İşlenmiş film metadata'sı
│       └── content_meta.json            # Model meta bilgileri
│
├── 📂 src/                              # Backend kaynak kodları
│   └── recommender_arl.py               # Association Rules modülü
│
├── 📂 test-web/                         # Content-Based test arayüzü
│   ├── app.py                           # Streamlit test paneli
│   ├── services.py                      # Backend servisleri
│   ├── README.md                        # Kullanım kılavuzu
│   └── requirements.txt                 # Bağımlılıklar
│
├── 📂 data/                             # Ham veri dosyaları
│   ├── ratings_small.csv                # Kullanıcı puanlamaları (küçük)
│   ├── ratings.csv                      # Kullanıcı puanlamaları (tam)
│   ├── movies_metadata.csv              # Film bilgileri
│   ├── links_small.csv                  # Film ID eşleşmeleri (küçük)
│   ├── links.csv                        # Film ID eşleşmeleri (tam)
│   ├── keywords.csv                     # Film anahtar kelimeleri
│   ├── credits.csv                      # Oyuncu/yönetmen bilgileri
│   └── raw/                             # Ham veri yedekleri
│
├── requirements.txt                     # Proje bağımlılıkları
├── yapilacaklar.txt                     # Algoritma açıklamaları
└── yapilacaklarplan.md                  # Detaylı proje planı
```

---

## 📦 Gereksinimler

- **Python:** 3.10 veya üstü
- **Temel Kütüphaneler:**

```
pandas>=2.0
numpy>=1.26
scipy>=1.11
scikit-learn>=1.4
mlxtend>=0.23
pyarrow>=15.0
streamlit>=1.30
plotly>=5.18
networkx>=3.2
```

---

## 🚀 Kurulum

### 1. Depoyu Klonlayın

```bash
git clone https://github.com/kullanici/MovieRecommender.git
cd MovieRecommender
```

### 2. Sanal Ortam Oluşturun (Önerilir)

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 4. Veri Dosyalarını Hazırlayın

Kaggle'dan "The Movies Dataset"i indirin ve `data/` klasörüne yerleştirin:
- [The Movies Dataset - Kaggle](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset)

Gerekli dosyalar:
- `ratings_small.csv` veya `ratings.csv`
- `movies_metadata.csv`
- `links_small.csv` veya `links.csv`

---

## 💻 Kullanım

### Association Rules Modeli

#### 1. Model Oluşturma

```bash
python src/recommender_arl.py
```

Bu komut şunları yapar:
- Ham verileri yükler
- Film eşleştirme tablosu oluşturur
- Birliktelik kurallarını çıkarır
- Model dosyalarını `models/` klasörüne kaydeder

#### 2. Streamlit Arayüzü

```bash
cd app
streamlit run Home_🎬_Recommender.py
```

### Content-Based Modeli

#### 1. Model Oluşturma

```bash
cd Content-Based
python data_pipeline.py
```

#### 2. CLI ile Öneri Alma

```bash
python recommender_content.py --titles "Inception,The Matrix"
```

#### 3. Model Değerlendirme

```bash
python evaluate_content.py --n-users 200 --top-n 10
```

#### 4. Test Paneli

```bash
cd test-web
streamlit run app.py
```

---

## 🤖 Öneri Algoritmaları

### 1. Association Rules (Birliktelik Kuralları)

**Dosya:** `src/recommender_arl.py`

**Nasıl Çalışır:**
1. Kullanıcıların beğendiği filmleri (rating ≥ 4.0) belirler
2. Kullanıcı-Film boolean matrisi oluşturur
3. Apriori algoritması ile sık film setlerini bulur
4. Association Rules ile "X → Y" kuralları çıkarır
5. Support, Confidence ve Lift metriklerine göre filtreler

**Metrikler:**
- **Support:** Kuralın ne kadar sık görüldüğü
- **Confidence:** X'i beğenen kullanıcıların Y'yi de beğenme olasılığı
- **Lift:** Kuralın rastgele birliktelikten ne kadar güçlü olduğu

**Örnek Kullanım:**

```python
from src.recommender_arl import recommend_with_association_rules

liked_movies = ["Inception", "Interstellar", "The Dark Knight"]
recommendations, missing = recommend_with_association_rules(liked_movies, top_n=10)
print(recommendations)
```

---

### 2. Content-Based Filtering (İçerik Tabanlı)

**Dosya:** `Content-Based/recommender_content.py`

**Nasıl Çalışır:**
1. Film türleri (genres) ve açıklamalarını (overview) birleştirir
2. TF-IDF vektörleştirme ile sayısal temsil oluşturur
3. Cosine Similarity ile film benzerliklerini hesaplar
4. Seçilen filmlere en benzer içerikteki filmleri önerir

**Özellikler:**
- Rating verisi gerektirmez (cold-start problemi yok)
- Sadece film içeriğine bakarak çalışır
- Kullanıcı profili oluşturma desteği

**Örnek Kullanım:**

```python
from Content_Based.recommender_content import cli_recommend

titles = ["Inception", "The Matrix"]
recommendations = cli_recommend(titles, top_n=10, method="score_avg")
print(recommendations)
```

---

## 🖥️ Streamlit Arayüzleri

### 1. Ana Öneri Sayfası (`app/Home_🎬_Recommender.py`)

**Özellikler:**
- Film arama ve seçme
- Association Rules tabanlı öneriler
- Score, Confidence, Lift metrikleri
- Görsel öneri kartları
- Detaylı öneri tablosu

**Çalıştırma:**
```bash
streamlit run app/Home_🎬_Recommender.py
```

### 2. Dataset Insights (`app/pages/1_📊_Dataset_Insights.py`)

**Özellikler:**
- Veri seti istatistikleri
- En popüler filmler grafiği
- Tür dağılımı analizi
- Association Rules görselleştirmeleri
- 3D Rule Space grafiği
- Film birliktelik ağı (NetworkX)

### 3. Content-Based Test Paneli (`test-web/app.py`)

**Özellikler:**
- Manuel film öneri testi
- Model inceleme araçları
- HitRate değerlendirme senaryosu
- JSON çıktı indirme

---

## 📊 Geliştirme Durumu

### ✅ Tamamlanan Modüller

| Modül | Dosya | Açıklama |
|-------|-------|----------|
| ARL Backend | `src/recommender_arl.py` | Apriori + Association Rules |
| ARL Arayüzü | `app/Home_🎬_Recommender.py` | Streamlit öneri sayfası |
| Dataset Analizi | `app/pages/1_📊_Dataset_Insights.py` | Görselleştirmeler |
| Content Pipeline | `Content-Based/data_pipeline.py` | TF-IDF oluşturma |
| Content Recommender | `Content-Based/recommender_content.py` | Öneri motoru |
| User Profile | `Content-Based/user_profile.py` | Profil tabanlı öneri |
| Evaluation | `Content-Based/evaluate_content.py` | HitRate hesaplama |
| Test Panel | `test-web/app.py` | Content-Based test UI |

### 📋 Yapılacaklar

- [ ] Item-based Collaborative Filtering modülü (`src/recommender_itemcf.py`)
- [ ] 3 algoritmanın ana arayüzde entegrasyonu
- [ ] Algoritma karşılaştırma bölümü
- [ ] Hybrid öneri sistemi
- [ ] API endpoint'leri (FastAPI)
- [ ] Docker container desteği

---

## 🔮 Gelecek Planlar

### Kısa Vadeli
1. **Item-based CF Modülü:** Rating benzerliğine dayalı işbirlikçi filtreleme
2. **Algoritma Seçimi:** Tek arayüzden 3 farklı algoritma seçebilme
3. **Karşılaştırma Tablosu:** Aynı filmler için farklı algoritma sonuçları

### Orta Vadeli
1. **Hybrid Model:** 3 algoritmanın ağırlıklı birleşimi
2. **keywords.csv Entegrasyonu:** Anahtar kelime tabanlı benzerlik
3. **credits.csv Entegrasyonu:** Oyuncu/yönetmen benzerliği

### Uzun Vadeli
1. **Deep Learning:** Neural Collaborative Filtering
2. **Gerçek Zamanlı Güncelleme:** Streaming veri desteği
3. **A/B Test Altyapısı:** Farklı modelleri karşılaştırma

---

## 📚 Veri Kaynağı

Bu proje Kaggle'daki **The Movies Dataset**'i kullanmaktadır:

- **Kaynak:** [The Movies Dataset - Kaggle](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset)
- **Film Sayısı:** ~45,000 film
- **Rating Sayısı:** ~26 milyon (tam) / ~100,000 (küçük)
- **Kullanıcı Sayısı:** ~270,000 (tam) / ~700 (küçük)

---

## 🛠️ Teknik Detaylar

### Kullanılan Teknolojiler

| Kategori | Teknoloji |
|----------|-----------|
| Programlama Dili | Python 3.10+ |
| Veri İşleme | Pandas, NumPy |
| Makine Öğrenmesi | scikit-learn, mlxtend |
| Metin İşleme | TF-IDF Vectorizer |
| Görselleştirme | Plotly, NetworkX |
| Web Arayüzü | Streamlit |
| Veri Formatları | CSV, Parquet, Pickle |

### Model Dosyaları

| Dosya | Boyut (yaklaşık) | Açıklama |
|-------|------------------|----------|
| `movie_mapping.pkl` | ~200 KB | Film ID-başlık eşleştirmesi |
| `association_rules.pkl` | ~5-10 MB | Birliktelik kuralları |
| `tfidf_matrix.npz` | ~50-100 MB | Sparse TF-IDF matrisi |
| `metadata.parquet` | ~20 MB | Film metadata'sı |

---

## 📝 Lisans

Bu proje eğitim amaçlı geliştirilmiştir.

---

## 👤 Geliştirici

**MovieRecommender** - Çoklu Algoritma Film Öneri Sistemi

---

## 🙏 Teşekkürler

- Kaggle ve The Movies Dataset için Rounak Banik'e
- mlxtend kütüphanesi için Sebastian Raschka'ya
- Streamlit ekibine

