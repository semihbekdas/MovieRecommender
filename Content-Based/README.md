# 🎬 Content-Based Film Öneri Sistemi

Content-Based Filtering (İçerik Tabanlı Filtreleme) kullanarak film önerileri sunan bir öneri sistemi.

---

## 📋 İçindekiler

- [Genel Bakış](#genel-bakış)
- [Gereksinimler](#gereksinimler)
- [Kurulum](#kurulum)
- [Veri Dosyaları](#veri-dosyaları)
- [Modül Açıklamaları](#modül-açıklamaları)
- [Kullanım](#kullanım)
- [Model Oluşturma](#model-oluşturma)
- [Değerlendirme](#değerlendirme)
- [Proje Yapısı](#proje-yapısı)

---

## 🎯 Genel Bakış

Bu sistem, filmlerin içerik özelliklerini (türler, açıklamalar) kullanarak benzer filmleri bulmak için **TF-IDF vektörleştirme** ve **Cosine Similarity** yöntemlerini kullanır.

### Nasıl Çalışır?

1. **Veri İşleme**: Film metadata'sı (genres, overview) işlenerek metin haline getirilir
2. **TF-IDF Vektörleştirme**: Her film için sayısal vektör oluşturulur
3. **Benzerlik Hesabı**: Filmler arası cosine similarity hesaplanır
4. **Öneri**: Kullanıcının beğendiği filmlere benzer filmler önerilir

---

## 📦 Gereksinimler

```
pandas>=2.0
numpy>=1.26
scipy>=1.11
scikit-learn>=1.4
pyarrow>=15.0
```

---

## 🚀 Kurulum

### 1. Bağımlılıkları Yükle

```bash
# Proje kök dizininden
pip install -r requirements.txt

# veya manuel olarak
pip install pandas numpy scipy scikit-learn pyarrow
```

### 2. Veri Dosyasını Kopyala

`movies_metadata.csv` dosyası `Content-Based` klasörüne kopyalanmalıdır:

```powershell
# PowerShell
Copy-Item "data\movies_metadata.csv" "Content-Based\movies_metadata.csv"
```

```bash
# Linux/Mac
cp data/movies_metadata.csv Content-Based/movies_metadata.csv
```

---

## 📁 Veri Dosyaları

### Gerekli Dosya

| Dosya | Açıklama | Kaynak |
|-------|----------|--------|
| `movies_metadata.csv` | Film metadata'sı (türler, açıklamalar vb.) | `data/` klasöründen kopyalanmalı |

### Oluşturulan Model Dosyaları (`models/` klasörü)

| Dosya | Açıklama |
|-------|----------|
| `tfidf_vectorizer.pkl` | Eğitilmiş TF-IDF Vectorizer objesi |
| `tfidf_matrix.npz` | Sparse TF-IDF matrisi (film vektörleri) |
| `metadata.parquet` | İşlenmiş film metadata'sı |
| `content_meta.json` | Model meta bilgileri (tarih, parametreler) |

---

## 📚 Modül Açıklamaları

### `data_pipeline.py`
Ana veri işleme ve model oluşturma modülü.

**Görevleri:**
- `movies_metadata.csv` dosyasını okur ve temizler
- Genre ve overview bilgilerini birleştirerek "content" metni oluşturur
- TF-IDF vektörleştirme yapar
- Model artefaktlarını (vectorizer, matrix, metadata) kaydeder

### `recommender_content.py`
Film öneri motoru.

**Görevleri:**
- Model artefaktlarını yükler
- Film başlığından öneri yapar
- Cosine similarity hesaplar
- Sonuçları formatlar

### `user_profile.py`
Kullanıcı profili tabanlı öneri modülü.

**Görevleri:**
- Birden fazla film seçiminden kullanıcı profili oluşturur
- Rating ağırlıklı profil hesaplar
- Profil tabanlı öneriler üretir

### `evaluate_content.py`
Model değerlendirme modülü.

**Görevleri:**
- Hit Rate hesaplar
- Farklı modlarda (random-split, leave-one-out) değerlendirme yapar
- Detaylı istatistikler üretir

---

## 💻 Kullanım

### 1. Model Oluşturma (İlk Kurulum)

```bash
cd Content-Based
python data_pipeline.py
```

**Parametreler:**

| Parametre | Varsayılan | Açıklama |
|-----------|------------|----------|
| `--source` | `movies_metadata.csv` | Veri dosyası yolu |
| `--max-features` | `12000` | TF-IDF max feature sayısı |
| `--ngram-min` | `1` | N-gram alt sınırı |
| `--ngram-max` | `2` | N-gram üst sınırı |
| `--min-content-chars` | `20` | Minimum metin uzunluğu |
| `--rebuild` | `False` | Mevcut modeli yeniden oluştur |

**Örnek:**

```bash
# Varsayılan ayarlarla
python data_pipeline.py

# Özel parametrelerle
python data_pipeline.py --max-features 15000 --ngram-max 3

# Modeli yeniden oluştur
python data_pipeline.py --rebuild
```

### 2. Film Bazlı Öneri

```bash
python recommender_content.py --title "Inception"
```

**Parametreler:**

| Parametre | Varsayılan | Açıklama |
|-----------|------------|----------|
| `--title` | (gerekli) | Film başlığı |
| `--top-n` | `10` | Önerilecek film sayısı |

**Örnek Çıktı:**

```
Sorgulanan Film: Inception (2010)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Rank  Title                    Score   Genres
   1     Interstellar             0.87    Sci-Fi, Drama
   2     The Matrix               0.82    Action, Sci-Fi
   3     Memento                  0.79    Mystery, Thriller
   ...
```

### 3. Kullanıcı Profili Tabanlı Öneri

```bash
python user_profile.py --titles "Inception,The Matrix,Interstellar"
```

**Parametreler:**

| Parametre | Varsayılan | Açıklama |
|-----------|------------|----------|
| `--titles` | (gerekli) | Virgülle ayrılmış film listesi |
| `--ratings` | `` | Filmlere verilen puanlar (opsiyonel) |
| `--top-n` | `10` | Önerilecek film sayısı |

**Örnek (Rating ile):**

```bash
python user_profile.py --titles "Inception,The Matrix,Titanic" --ratings "5,4,3"
```

### 4. Model Değerlendirme

```bash
python evaluate_content.py
```

**Parametreler:**

| Parametre | Varsayılan | Açıklama |
|-----------|------------|----------|
| `--n-users` | `200` | Test edilecek kullanıcı sayısı |
| `--top-n` | `10` | Öneri listesi uzunluğu |
| `--mode` | `random-split` | Değerlendirme modu |
| `--method` | `item-sim` | Öneri metodu |

**Örnek:**

```bash
# Varsayılan değerlendirme
python evaluate_content.py

# Daha fazla kullanıcı ile
python evaluate_content.py --n-users 500 --top-n 20
```

---

## 📊 Model Oluşturma Adımları

### Adım 1: Veriyi Hazırla

```powershell
# Veriyi Content-Based klasörüne kopyala
Copy-Item "data\movies_metadata.csv" "Content-Based\movies_metadata.csv"
```

### Adım 2: Modeli Oluştur

```bash
cd Content-Based
python data_pipeline.py
```

**Beklenen Çıktı:**

```
[INFO] movies_metadata.csv okunuyor...
[INFO] 45466 film yüklendi
[INFO] Genres ve overview birleştiriliyor...
[INFO] TF-IDF vektörleştirme yapılıyor...
[INFO] Artefaktlar kaydediliyor...
[SUCCESS] Model oluşturuldu!
  - Vectorizer: models/tfidf_vectorizer.pkl
  - Matrix: models/tfidf_matrix.npz
  - Metadata: models/metadata.parquet
```

### Adım 3: Modeli Test Et

```bash
python recommender_content.py --title "The Godfather"
```

---

## 📈 Değerlendirme Metrikleri

### Hit Rate
- Kullanıcının beğendiği bir filmin öneri listesinde olma oranı
- Yüksek = daha iyi

### Örnek Değerlendirme

```bash
python evaluate_content.py --n-users 200 --mode random-split
```

**Çıktı:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       CONTENT-BASED EVALUATION SONUÇLARI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hit Rate @ 10: 0.42 (42%)
Tested Users:  200
Method:        item-sim
Mode:          random-split
```

---

## 📂 Proje Yapısı

```
Content-Based/
├── README.md                 # Bu dosya
├── YOL_HARITASI.md          # Detaylı kavramsal açıklamalar
├── movies_metadata.csv      # Ham veri (data/ klasöründen kopyalanmalı)
├── data_pipeline.py         # Veri işleme ve model oluşturma
├── recommender_content.py   # Film öneri motoru
├── user_profile.py          # Kullanıcı profili tabanlı öneri
├── evaluate_content.py      # Model değerlendirme
└── models/                  # Oluşturulan model dosyaları
    ├── tfidf_vectorizer.pkl
    ├── tfidf_matrix.npz
    ├── metadata.parquet
    └── content_meta.json
```

---

## 🔧 Hızlı Başlangıç (Quick Start)

```bash
# 1. Proje dizinine git
cd MovieRecommender

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Veriyi kopyala
Copy-Item "data\movies_metadata.csv" "Content-Based\movies_metadata.csv"

# 4. Content-Based dizinine geç
cd Content-Based

# 5. Modeli oluştur
python data_pipeline.py

# 6. Öneri al
python recommender_content.py --title "Inception"

# 7. Kullanıcı profili ile öneri
python user_profile.py --titles "Inception,The Matrix"
```

---

## ❓ Sık Sorulan Sorular

### Model dosyaları nerede?
`Content-Based/models/` klasöründe oluşturulur.

### "FileNotFoundError: TF-IDF artefaktları bulunamadı" hatası alıyorum
Önce `python data_pipeline.py` komutunu çalıştırarak modeli oluşturun.

### Modeli yeniden oluşturmak istiyorum
```bash
python data_pipeline.py --rebuild
```

### Farklı bir veri dosyası kullanmak istiyorum
```bash
python data_pipeline.py --source "path/to/your/metadata.csv"
```

---

## 📖 Daha Fazla Bilgi

Kavramsal açıklamalar ve detaylı teknik bilgi için [YOL_HARITASI.md](./YOL_HARITASI.md) dosyasına bakın.

---

## 👤 Geliştirici

**MovieRecommender** - Content-Based Film Öneri Sistemi
