"""
🎬 Item-Based Collaborative Filtering Modülü
Profesyonel Standart: Tip korumalı, modüler ve artifact tabanlı yapı.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# --- AYARLAR VE YOLLAR ---
ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
MODELS_DIR = ROOT_DIR / "models"

# Dosya Yolları
# RATINGS_PATH = RAW_DATA_DIR / "ratings.csv"  <-- Bunu yoruma al veya sil
RATINGS_PATH = RAW_DATA_DIR / "ratings_small.csv" # <-- Sadece bunu kullan

MAPPING_PATH = MODELS_DIR / "movie_mapping.pkl"    # ARL'den gelen ortak mapping
ITEM_SIM_PATH = MODELS_DIR / "item_similarity.pkl" # Bizim üreteceğimiz model

# Parametreler
MIN_VOTES_PER_MOVIE = 10  # Gürültüyü azaltmak için az oy alanları ele

def load_data() -> pd.DataFrame:
    """Ratings verisini yükler ve doğrular."""
    if not RATINGS_PATH.exists():
        # Yedek kontrol (data klasöründe olabilir mi?)
        alt_path = ROOT_DIR / "data" / "ratings_small.csv"
        if alt_path.exists():
            print(f"📂 Veri okunuyor: {alt_path.name}")
            return pd.read_csv(alt_path)
        raise FileNotFoundError(f"Ratings dosyası bulunamadı: {RATINGS_PATH}")
    
    print(f"📂 Veri okunuyor: {RATINGS_PATH.name}")
    df = pd.read_csv(RATINGS_PATH)
    return df

def create_item_similarity_matrix(ratings: pd.DataFrame) -> pd.DataFrame:
    """
    User-Item matrisini oluşturur ve Cosine Similarity hesaplar.
    """
    print("🔄 User-Item matrisi oluşturuluyor...")
    
    # 1. Pivot Table (Satır: User, Sütun: Movie, Değer: Rating)
    # Bellek optimizasyonu için float32 kullanabiliriz ama şimdilik standart float kalsın
    user_movie_matrix = ratings.pivot_table(
        index="userId", 
        columns="movieId", 
        values="rating"
    )
    
    # 2. Filtreleme (Çok az oy alan filmleri çıkar)
    movie_counts = user_movie_matrix.count(axis=0) # Sütun bazlı sayım
    filtered_matrix = user_movie_matrix.loc[:, movie_counts >= MIN_VOTES_PER_MOVIE]
    
    print(f"   📉 Filtreleme: {user_movie_matrix.shape[1]} -> {filtered_matrix.shape[1]} film (Min {MIN_VOTES_PER_MOVIE} oy)")
    
    # 3. Boşlukları Doldurma (Oy verilmeyenler 0 kabul edilir)
    filtered_matrix_filled = filtered_matrix.fillna(0)
    
    print("🧮 Benzerlik matrisi hesaplanıyor (Cosine)...")
    # Film-Film benzerliği için matrisin transpozu alınır
    # sklearn cosine_similarity satır-satır çalışır, bu yüzden Transpoz alıyoruz.
    # Sonuç: (Movies x Movies) matrisi
    item_similarity = cosine_similarity(filtered_matrix_filled.T)
    
    # DataFrame'e çevir (index ve kolonlar movieId olacak)
    item_sim_df = pd.DataFrame(
        item_similarity, 
        index=filtered_matrix.columns, 
        columns=filtered_matrix.columns
    )
    
    return item_sim_df

def save_model(sim_df: pd.DataFrame):
    """Hesaplanan modeli diske kaydeder."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ITEM_SIM_PATH, "wb") as f:
        pickle.dump(sim_df, f)
    print(f"💾 Model kaydedildi: {ITEM_SIM_PATH}")

def load_model() -> pd.DataFrame:
    """Modeli diskten yükler."""
    if not ITEM_SIM_PATH.exists():
        raise FileNotFoundError("Model dosyası yok. Önce bu dosyayı 'main' olarak çalıştırıp eğitin.")
    with open(ITEM_SIM_PATH, "rb") as f:
        return pickle.load(f)

def recommend_item_based(
    liked_titles: Sequence[str], 
    top_n: int = 10
) -> tuple[pd.DataFrame, list[str]]:
    """
    Dışarıdan çağrılacak ana öneri fonksiyonu.
    
    Returns:
        (results_df, missing_titles_list)
    """
    # 1. Gerekli dosyaları yükle
    try:
        sim_df = load_model()
        # Mapping dosyası ARL tarafından oluşturulmuş olmalı
        if not MAPPING_PATH.exists():
            # ARL modülünü çağırıp oluşturmayı dene (Fallback)
            print("⚠️ Mapping dosyası bulunamadı, oluşturulmaya çalışılıyor...")
            try:
                from src import recommender_arl
                recommender_arl.prepare_and_save_artifacts()
            except Exception:
                raise FileNotFoundError("Mapping dosyası yok. Lütfen önce 'src/recommender_arl.py' çalıştırın.")
        
        mapping_df = pd.read_pickle(MAPPING_PATH)
    except FileNotFoundError as e:
        return pd.DataFrame(), [str(e)]

    # 2. Title -> ID Dönüşümü
    # Case insensitive eşleşme için
    mapping_df['title_lower'] = mapping_df['title'].str.lower().str.strip()
    title_to_id = mapping_df.set_index("title_lower")["movieId"].to_dict()
    id_to_title = mapping_df.set_index("movieId")["title"].to_dict()
    
    liked_ids = []
    missing_titles = []
    
    for title in liked_titles:
        clean_title = title.strip().lower()
        if clean_title in title_to_id:
            mid = title_to_id[clean_title]
            # Modelde bu ID var mı? (Filtrelemeye takılmış olabilir)
            if mid in sim_df.index:
                liked_ids.append(mid)
            else:
                # Film var ama yeterli oyu yoksa
                missing_titles.append(f"{title} (Yetersiz Veri)")
        else:
            missing_titles.append(title)
            
    if not liked_ids:
        return pd.DataFrame(), missing_titles

    # 3. Öneri Hesaplama (Weighted Average Logic)
    # Seçilen filmlerin benzerlik sütunlarını al
    selected_sims = sim_df.loc[:, liked_ids]
    
    # Satır bazında ortalama al (Hangi diğer filmler bu seçilenlere benziyor?)
    # axis=1: Sütunları topla/ortala
    avg_scores = selected_sims.mean(axis=1)
    
    # Zaten seçilenleri listeden çıkar
    avg_scores = avg_scores.drop(liked_ids, errors="ignore")
    
    # Sırala ve ilk N'i al
    top_scores = avg_scores.sort_values(ascending=False).head(top_n)
    
    # 4. Sonuçları Formatla
    results = []
    for mid, score in top_scores.items():
        results.append({
            "movieId": mid,
            "title": id_to_title.get(mid, f"Unknown ({mid})"),
            "similarity": score
        })
        
    return pd.DataFrame(results), missing_titles

# --- PIPELINE ÇALIŞTIRICI ---
if __name__ == "__main__":
    print("🚀 Item-Based Model Eğitimi Başlatılıyor...")
    try:
        ratings_data = load_data()
        sim_matrix = create_item_similarity_matrix(ratings_data)
        save_model(sim_matrix)
        print("\n✅ İşlem Başarıyla Tamamlandı!")
        print(f"   Model Boyutu: {sim_matrix.shape[0]}x{sim_matrix.shape[1]} film")
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")
        import traceback
        traceback.print_exc()