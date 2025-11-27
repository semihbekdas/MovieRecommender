

================================================================================
# 🎯 DETAYLI PROJE PLANI - 3 MODEL FİLM ÖNERİ SİSTEMİ
================================================================================

## 📋 GENEL BAKIŞ

**Proje Amacı:** 3 farklı öneri algoritması kullanarak film önerisi yapan sistem
**Veri Seti:** `ratings_small.csv` (tüm modellerde)
**Arayüz:** Tek sayfa, radyo buton ile algoritma seçimi

### Modeller:
1. ✅ **Association Rules (ARL)** - TAMAMLANDI
2. 🔄 **Item-based Collaborative Filtering** - YAPILACAK
3. 🔄 **Content-based Filtering** - YAPILACAK

---

## 📁 DOSYA YAPISI (Hedef)

```
Movie_Recommendations/
├── app/
│   ├── Home_🎬_Recommender.py          # Ana sayfa (3 model entegre)
│   └── pages/
│       └── 1_📊_Dataset_Insights.py    # Mevcut analiz sayfası
├── data/
│   └── raw/
│       ├── ratings_small.csv           # Ana veri
│       ├── links_small.csv             # movieId ↔ tmdbId
│       ├── movies_metadata.csv         # Film bilgileri
│       ├── keywords.csv                # (İleride kullanılabilir)
│       └── credits.csv                 # (İleride kullanılabilir)
├── models/
│   ├── movie_mapping.pkl               # ✅ Mevcut (ARL)
│   ├── association_rules.pkl           # ✅ Mevcut (ARL)
│   ├── artifacts_meta.json             # ✅ Mevcut (ARL)
│   ├── item_similarity.pkl             # 🆕 Item-based CF için
│   ├── item_cf_meta.json               # 🆕 Item-CF metadata
│   ├── content_similarity.pkl          # 🆕 Content-based için
│   ├── content_metadata.pkl            # 🆕 Film metadata (genre, overview)
│   └── content_meta.json               # 🆕 Content-based metadata
├── src/
│   ├── __init__.py
│   ├── recommender_arl.py              # ✅ Mevcut
│   ├── recommender_itemcf.py           # 🆕 Item-based CF
│   └── recommender_content.py          # 🆕 Content-based
└── requirements.txt
```

---

================================================================================
# 📦 MODEL 2: ITEM-BASED COLLABORATIVE FILTERING
================================================================================

## 🎯 Amaç
"Bu filmi beğenenler şunları da beğendi" mantığını rating benzerliği ile kurmak.

## 📄 Dosya: `src/recommender_itemcf.py`

### Sabitler ve Yollar
```python
# Dosya başı
ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
MODELS_DIR = ROOT_DIR / "models"

# Artefakt yolları
ITEM_SIM_PATH = MODELS_DIR / "item_similarity.pkl"
ITEM_CF_META_PATH = MODELS_DIR / "item_cf_meta.json"

# Varsayılan parametreler
DEFAULT_MIN_RATINGS_PER_MOVIE = 5  # Az rating'li filmleri ele
DEFAULT_SIMILARITY_METRIC = "cosine"  # İleride "pearson" eklenebilir
```

### Fonksiyonlar (Detaylı)

#### 1. `load_ratings_data()`
```python
def load_ratings_data(raw_dir: Path = RAW_DATA_DIR) -> pd.DataFrame:
    """
    ratings_small.csv dosyasını yükler.
    
    Returns:
        DataFrame: userId, movieId, rating, timestamp kolonları
    """
```

#### 2. `build_rating_matrix()`
```python
def build_rating_matrix(
    ratings_df: pd.DataFrame,
    min_ratings_per_movie: int = DEFAULT_MIN_RATINGS_PER_MOVIE
) -> pd.DataFrame:
    """
    User-Movie rating matrisi oluşturur.
    
    Args:
        ratings_df: Ham rating verisi
        min_ratings_per_movie: Minimum rating sayısı eşiği
        
    Returns:
        DataFrame: Index=userId, Columns=movieId, Values=rating (NaN dolgu 0)
    """
    # 1. Az rating alan filmleri filtrele
    # 2. pivot_table ile matris oluştur
    # 3. NaN'leri 0 ile doldur
```

#### 3. `compute_item_similarity()`
```python
def compute_item_similarity(
    rating_matrix: pd.DataFrame,
    metric: str = "cosine"
) -> pd.DataFrame:
    """
    Film-Film benzerlik matrisi hesaplar.
    
    Args:
        rating_matrix: User-Movie matrisi
        metric: "cosine" veya "pearson" (şimdilik sadece cosine)
        
    Returns:
        DataFrame: movieId x movieId similarity matrisi
    """
    # sklearn.metrics.pairwise.cosine_similarity kullan
    # İleride pearson için: numpy.corrcoef veya scipy
```

#### 4. `save_item_similarity()` / `load_item_similarity()`
```python
def save_item_similarity(sim_df: pd.DataFrame, path: Path = ITEM_SIM_PATH) -> None:
    """Similarity matrisini diske kaydet."""

def load_item_similarity(path: Path = ITEM_SIM_PATH) -> pd.DataFrame:
    """Kayıtlı similarity matrisini yükle."""
```

#### 5. `save_item_cf_metadata()` / `load_item_cf_metadata()`
```python
def save_item_cf_metadata(metadata: dict, path: Path = ITEM_CF_META_PATH) -> None:
    """Kullanılan parametreleri JSON olarak kaydet."""
    # min_ratings_per_movie, metric, movie_count, timestamp

def load_item_cf_metadata(path: Path = ITEM_CF_META_PATH) -> dict | None:
    """Metadata yükle."""
```

#### 6. `prepare_and_save_item_cf_artifacts()`
```python
def prepare_and_save_item_cf_artifacts(
    raw_dir: Path = RAW_DATA_DIR,
    min_ratings_per_movie: int = DEFAULT_MIN_RATINGS_PER_MOVIE,
    metric: str = DEFAULT_SIMILARITY_METRIC
) -> pd.DataFrame:
    """
    Tam pipeline: Veri → Rating matrisi → Similarity → Kaydet
    
    Returns:
        DataFrame: Similarity matrisi
    """
    # CLI'dan çalıştırıldığında bu fonksiyon tetiklenir
```

#### 7. `_titles_to_movie_ids()` (Yardımcı)
```python
def _titles_to_movie_ids(
    titles: Sequence[str],
    mapping_df: pd.DataFrame
) -> tuple[list[int], list[str]]:
    """
    Film adlarını movieId'ye çevir.
    (ARL'deki ile aynı mantık - ortak modüle taşınabilir)
    """
```

#### 8. `recommend_item_based_single()`
```python
def recommend_item_based_single(
    movie_id: int,
    sim_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Tek film için benzer filmler bul.
    
    Returns:
        DataFrame: title, movieId, similarity
    """
```

#### 9. `recommend_item_based()` (ANA FONKSİYON)
```python
def recommend_item_based(
    liked_titles: Sequence[str],
    top_n: int = 10,
    sim_path: Path = ITEM_SIM_PATH,
    mapping_path: Path = MAPPING_PATH  # ARL'den import
) -> tuple[pd.DataFrame, list[str]]:
    """
    Birden fazla film için ortak öneri üret.
    
    Args:
        liked_titles: Kullanıcının sevdiği filmler
        top_n: Öneri sayısı
        
    Returns:
        (öneriler DataFrame, bulunamayan filmler listesi)
        DataFrame kolonları: title, movieId, similarity
    """
    # 1. Mapping yükle
    # 2. Similarity matrisi yükle
    # 3. Title → movieId çevir
    # 4. Seçili filmlerin sim vektörlerinin ortalamasını al
    # 5. Seçili filmleri çıkar
    # 6. En yüksek similarity'e göre sırala
    # 7. top_n döndür
```

#### 10. `get_movie_stats()` (Opsiyonel - UI için)
```python
def get_movie_stats(
    movie_ids: list[int],
    ratings_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Film bazlı istatistikler: ortalama rating, rating sayısı
    """
```

### CLI Çalıştırma
```python
if __name__ == "__main__":
    # 1. Artefaktları oluştur
    sim_df = prepare_and_save_item_cf_artifacts()
    
    # 2. Test önerisi
    sample_likes = ["Inception", "Interstellar", "The Dark Knight"]
    recs, missing = recommend_item_based(sample_likes, top_n=10)
    print(recs)
```

---

================================================================================
# 📦 MODEL 3: CONTENT-BASED FILTERING
================================================================================

## 🎯 Amaç
Filmlerin içerik bilgisine (genre + overview) bakarak benzer filmler önermek.

## 📄 Dosya: `src/recommender_content.py`

### Sabitler ve Yollar
```python
ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
MODELS_DIR = ROOT_DIR / "models"

# Artefakt yolları
CONTENT_SIM_PATH = MODELS_DIR / "content_similarity.pkl"
CONTENT_METADATA_PATH = MODELS_DIR / "content_metadata.pkl"
CONTENT_META_PATH = MODELS_DIR / "content_meta.json"

# TF-IDF parametreleri
DEFAULT_MAX_FEATURES = 5000
DEFAULT_STOP_WORDS = "english"
```

### Fonksiyonlar (Detaylı)

#### 1. `load_movies_metadata()`
```python
def load_movies_metadata(raw_dir: Path = RAW_DATA_DIR) -> pd.DataFrame:
    """
    movies_metadata.csv yükle ve temizle.
    
    Returns:
        DataFrame: id, title, genres, overview (temizlenmiş)
    """
    # 1. CSV oku
    # 2. Gerekli kolonları seç: id, title, genres, overview
    # 3. id'yi int'e çevir (hatalıları at)
    # 4. Duplikatları temizle
```

#### 2. `parse_genres()`
```python
def parse_genres(value: str) -> list[str]:
    """
    Genres alanını JSON string'den listeye çevir.
    
    Input: "[{'id': 28, 'name': 'Action'}, ...]"
    Output: ["Action", "Drama", ...]
    """
    # ast.literal_eval kullan
    # Hata durumunda boş liste dön
```

#### 3. `build_content_string()`
```python
def build_content_string(
    genres_list: list[str],
    overview: str
) -> str:
    """
    Genre ve overview'i birleştirerek içerik metni oluştur.
    
    İLERİDE GENİŞLETİLEBİLİR:
    - keywords eklenebilir
    - cast/crew eklenebilir
    """
    # Genre'leri boşlukla birleştir
    # Overview ekle
    # NaN kontrolü
```

#### 4. `prepare_content_features()`
```python
def prepare_content_features(metadata_df: pd.DataFrame) -> pd.DataFrame:
    """
    Metadata'dan content feature'ları hazırla.
    
    Returns:
        DataFrame: id, title, genres_list, overview, content
    """
    # 1. parse_genres uygula
    # 2. build_content_string uygula
    # 3. Boş content olanları filtrele
```

#### 5. `compute_tfidf_similarity()`
```python
def compute_tfidf_similarity(
    content_df: pd.DataFrame,
    max_features: int = DEFAULT_MAX_FEATURES,
    stop_words: str = DEFAULT_STOP_WORDS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    TF-IDF + Cosine Similarity hesapla.
    
    Args:
        content_df: content kolonu olan DataFrame
        
    Returns:
        (similarity_df, metadata_df)
        - similarity_df: id x id similarity matrisi
        - metadata_df: id, title, genres_list, overview
    """
    # 1. TfidfVectorizer fit_transform
    # 2. cosine_similarity hesapla
    # 3. DataFrame'e çevir (index = tmdb_id)
```

#### 6. `save_content_artifacts()` / `load_content_artifacts()`
```python
def save_content_artifacts(
    sim_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    sim_path: Path = CONTENT_SIM_PATH,
    meta_path: Path = CONTENT_METADATA_PATH
) -> None:
    """Similarity matrisi ve metadata'yı kaydet."""

def load_content_similarity(path: Path = CONTENT_SIM_PATH) -> pd.DataFrame:
    """Similarity matrisi yükle."""

def load_content_metadata(path: Path = CONTENT_METADATA_PATH) -> pd.DataFrame:
    """Content metadata yükle."""
```

#### 7. `save_content_meta()` / `load_content_meta()`
```python
def save_content_meta(metadata: dict, path: Path = CONTENT_META_PATH) -> None:
    """Parametreleri JSON olarak kaydet."""
    # max_features, stop_words, movie_count, timestamp

def load_content_meta(path: Path = CONTENT_META_PATH) -> dict | None:
    """Meta bilgileri yükle."""
```

#### 8. `prepare_and_save_content_artifacts()`
```python
def prepare_and_save_content_artifacts(
    raw_dir: Path = RAW_DATA_DIR,
    max_features: int = DEFAULT_MAX_FEATURES,
    stop_words: str = DEFAULT_STOP_WORDS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Tam pipeline: Metadata → Content → TF-IDF → Similarity → Kaydet
    
    Returns:
        (similarity_df, metadata_df)
    """
```

#### 9. `_map_title_to_tmdb_id()` (Yardımcı)
```python
def _map_title_to_tmdb_id(
    titles: Sequence[str],
    content_meta_df: pd.DataFrame
) -> tuple[list[int], list[str]]:
    """
    Film adlarını tmdb_id'ye çevir.
    
    Not: Content-based tmdb_id kullanır (ARL movieId değil!)
    """
```

#### 10. `recommend_content_based()` (ANA FONKSİYON)
```python
def recommend_content_based(
    liked_titles: Sequence[str],
    top_n: int = 10,
    sim_path: Path = CONTENT_SIM_PATH,
    meta_path: Path = CONTENT_METADATA_PATH
) -> tuple[pd.DataFrame, list[str]]:
    """
    İçerik bazlı öneri üret.
    
    Returns:
        (öneriler DataFrame, bulunamayan filmler)
        DataFrame kolonları: title, tmdb_id, similarity, genres, overview_snippet
    """
    # 1. Similarity ve metadata yükle
    # 2. Title → tmdb_id çevir
    # 3. Seçili filmlerin sim vektörlerinin ortalaması
    # 4. Seçili filmleri çıkar
    # 5. En yüksek similarity'e göre sırala
    # 6. Genre ve overview snippet ekle
    # 7. top_n döndür
```

### CLI Çalıştırma
```python
if __name__ == "__main__":
    # 1. Artefaktları oluştur
    sim_df, meta_df = prepare_and_save_content_artifacts()
    
    # 2. Test önerisi
    sample_likes = ["Inception", "Interstellar"]
    recs, missing = recommend_content_based(sample_likes, top_n=10)
    print(recs)
```

---

================================================================================
# 🖥️ STREAMLIT ENTEGRASYONU
================================================================================

## 📄 Dosya: `app/Home_🎬_Recommender.py` (Güncelleme)

### Yeni Import'lar
```python
from src import recommender_arl as arl
from src import recommender_itemcf as itemcf
from src import recommender_content as content
```

### Yeni Sabitler
```python
ALGORITHM_OPTIONS = {
    "🔗 Association Rules": "arl",
    "🎬 Item-based CF": "itemcf",
    "📝 Content-based": "content"
}
```

### UI Yapısı (Güncellenmiş)

#### Sidebar Değişiklikleri
```python
with st.sidebar:
    # ... mevcut kod ...
    
    st.markdown("---")
    st.markdown("### 🤖 Algoritma Seçimi")
    
    selected_algo = st.radio(
        "Öneri algoritması",
        options=list(ALGORITHM_OPTIONS.keys()),
        index=0,
        help="Farklı algoritmalar farklı sonuçlar üretir"
    )
    
    algo_code = ALGORITHM_OPTIONS[selected_algo]
```

#### Algoritma Bilgi Kutuları
```python
# Her algoritma için açıklama göster
if algo_code == "arl":
    st.info("🔗 **Association Rules:** Film birliktelik kurallarına göre öneri")
elif algo_code == "itemcf":
    st.info("🎬 **Item-based CF:** Rating benzerliğine göre öneri")
else:
    st.info("📝 **Content-based:** Tür ve açıklama benzerliğine göre öneri")
```

#### Öneri Hesaplama (Algoritma Bazlı)
```python
if algo_code == "arl":
    recs, missing, stats = recommend_from_rules(...)
    metric_name = "Skor"
    metric_col = "score"
    
elif algo_code == "itemcf":
    recs, missing = itemcf.recommend_item_based(liked_titles, top_n)
    metric_name = "Benzerlik"
    metric_col = "similarity"
    
else:  # content
    recs, missing = content.recommend_content_based(liked_titles, top_n)
    metric_name = "Benzerlik"
    metric_col = "similarity"
```

#### Kart Gösterimi (Algoritma Bazlı Metrik)
```python
# ARL için: score, confidence, lift
# Item-CF için: similarity
# Content için: similarity, genres

if algo_code == "arl":
    # Mevcut kart tasarımı
    show_score_confidence_lift(row)
    
elif algo_code == "itemcf":
    st.markdown(f"📊 Benzerlik: **{row['similarity']:.1%}**")
    
else:
    st.markdown(f"📊 Benzerlik: **{row['similarity']:.1%}**")
    st.markdown(f"🎭 Türler: {row.get('genres', 'N/A')}")
```

---

## 🔄 MODEL KARŞILAŞTIRMA SEKMESİ

### Yeni Bölüm: "⚖️ Karşılaştırma"
```python
st.markdown("---")
st.subheader("⚖️ Model Karşılaştırması")

if liked_titles:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🔗 Association Rules")
        arl_recs, _, _ = recommend_from_rules(tuple(liked_titles), mapping_df, rules_df, 5)
        if not arl_recs.empty:
            for _, row in arl_recs.iterrows():
                st.markdown(f"• {row['title']} (skor: {row['score']:.2f})")
        else:
            st.warning("Öneri bulunamadı")
    
    with col2:
        st.markdown("#### 🎬 Item-based CF")
        itemcf_recs, _ = itemcf.recommend_item_based(liked_titles, 5)
        if not itemcf_recs.empty:
            for _, row in itemcf_recs.iterrows():
                st.markdown(f"• {row['title']} ({row['similarity']:.1%})")
        else:
            st.warning("Öneri bulunamadı")
    
    with col3:
        st.markdown("#### 📝 Content-based")
        content_recs, _ = content.recommend_content_based(liked_titles, 5)
        if not content_recs.empty:
            for _, row in content_recs.iterrows():
                st.markdown(f"• {row['title']} ({row['similarity']:.1%})")
        else:
            st.warning("Öneri bulunamadı")
```

---

## 🔄 FALLBACK MEKANİZMASI

### Her Model İçin Fallback
```python
def get_fallback_recommendations(algo_code: str, mapping_df, top_n: int = 10):
    """
    Model öneri üretemezse genel popüler filmler döndür.
    """
    if algo_code == "itemcf":
        # En yüksek ortalama similarity'e sahip filmler
        return get_most_similar_movies_overall(...)
    
    elif algo_code == "content":
        # En popüler filmler (vote_count'a göre)
        return get_most_popular_movies(...)
    
    else:  # arl
        # Mevcut global_top_recommendations fonksiyonu
        return global_top_recommendations(...)
```

---

================================================================================
# ✅ YAPILACAKLAR LİSTESİ (CHECKBOX FORMAT)
================================================================================

## FAZA 1: Item-based Collaborative Filtering

### Backend (`src/recommender_itemcf.py`)
- [ ] Dosya oluştur ve import'ları ekle
- [ ] Sabitler ve yol tanımları
- [ ] `load_ratings_data()` fonksiyonu
- [ ] `build_rating_matrix()` fonksiyonu
- [ ] `compute_item_similarity()` fonksiyonu (cosine)
- [ ] `save/load_item_similarity()` fonksiyonları
- [ ] `save/load_item_cf_metadata()` fonksiyonları
- [ ] `prepare_and_save_item_cf_artifacts()` tam pipeline
- [ ] `_titles_to_movie_ids()` yardımcı fonksiyon
- [ ] `recommend_item_based_single()` tek film öneri
- [ ] `recommend_item_based()` çoklu film öneri
- [ ] CLI test kodu (`if __name__ == "__main__"`)
- [ ] Terminal'den test: `python src/recommender_itemcf.py`

### Test
- [ ] Similarity matrisi boyutunu kontrol et
- [ ] Örnek film için benzer filmler mantıklı mı?
- [ ] Çoklu seçimde öneriler değişiyor mu?

---

## FAZA 2: Content-based Filtering

### Backend (`src/recommender_content.py`)
- [ ] Dosya oluştur ve import'ları ekle
- [ ] Sabitler ve yol tanımları
- [ ] `load_movies_metadata()` fonksiyonu
- [ ] `parse_genres()` fonksiyonu
- [ ] `build_content_string()` fonksiyonu (genişletilebilir yapı)
- [ ] `prepare_content_features()` fonksiyonu
- [ ] `compute_tfidf_similarity()` fonksiyonu
- [ ] `save/load_content_artifacts()` fonksiyonları
- [ ] `save/load_content_meta()` fonksiyonları
- [ ] `prepare_and_save_content_artifacts()` tam pipeline
- [ ] `_map_title_to_tmdb_id()` yardımcı fonksiyon
- [ ] `recommend_content_based()` ana öneri fonksiyonu
- [ ] CLI test kodu
- [ ] Terminal'den test: `python src/recommender_content.py`

### Test
- [ ] TF-IDF matris boyutunu kontrol et
- [ ] Benzer türdeki filmler aynı cluster'da mı?
- [ ] Overview içeriği etkili mi?

---

## FAZA 3: Streamlit Entegrasyonu

### Ana Sayfa Güncellemesi (`app/Home_🎬_Recommender.py`)
- [ ] Yeni modülleri import et
- [ ] Sidebar'a algoritma radyo butonu ekle
- [ ] Algoritma bazlı load fonksiyonları ekle
- [ ] Algoritma bazlı öneri hesaplama
- [ ] Kart gösterimini algoritma bazlı güncelle
- [ ] Metrik isimlerini algoritma bazlı değiştir
- [ ] Fallback mekanizması her model için

### Model Karşılaştırma
- [ ] Karşılaştırma bölümü ekle
- [ ] 3 kolon: ARL, Item-CF, Content
- [ ] Aynı filmler için 3 farklı sonuç göster
- [ ] Özet tablo formatı

### UI/UX İyileştirmeleri
- [ ] Algoritma açıklama kutuları
- [ ] Loading spinner'lar
- [ ] Hata mesajları
- [ ] Boş sonuç durumları

---

## FAZA 4: Test ve Optimizasyon

### Genel Test
- [ ] Tüm modelleri ayrı ayrı çalıştır
- [ ] Streamlit'te 3 algoritma arası geçiş
- [ ] Karşılaştırma bölümü çalışıyor mu?
- [ ] Fallback durumları test et

### Performans
- [ ] Similarity matrisleri cache'leniyor mu?
- [ ] İlk yükleme süresi kabul edilebilir mi?
- [ ] Memory kullanımı kontrol

### Dokümantasyon
- [ ] Fonksiyon docstring'leri ekle
- [ ] README güncelle
- [ ] Gerekli paketleri requirements.txt'e ekle

---

## 📌 NOTLAR

### Önemli Kararlar
1. Veri seti: `ratings_small.csv` (tüm modeller)
2. Similarity: Cosine (Pearson sonra eklenebilir)
3. Content: Genre + Overview (keywords/credits sonra)
4. UI: Tek sayfa, radyo buton seçimi
5. Fallback: Her model için genel öneriler

### İleriye Dönük İyileştirmeler
- [ ] Pearson correlation ekleme
- [ ] keywords.csv entegrasyonu
- [ ] credits.csv (yönetmen, oyuncu) entegrasyonu
- [ ] Hybrid model (3 modelin birleşimi)
- [ ] Model performans karşılaştırma metrikleri

---

## ⏱️ TAHMİNİ SÜRE

| Faz | Tahmini Süre |
|-----|--------------|
| Faz 1: Item-based CF | 2-3 saat |
| Faz 2: Content-based | 2-3 saat |
| Faz 3: Streamlit | 2-3 saat |
| Faz 4: Test & Fix | 1-2 saat |
| **TOPLAM** | **7-11 saat** |

---

================================================================================
# 🚀 BAŞLAMA NOKTASI
================================================================================

Hazır olduğunda şu komutla başlayacağız:

1. **İlk adım:** `src/recommender_itemcf.py` dosyasını oluştur
2. **Sonra:** `python src/recommender_itemcf.py` ile test et
3. **Ardından:** Content-based'e geç
4. **Son:** Streamlit entegrasyonu

Onay ver, başlayalım! 🎬

---

