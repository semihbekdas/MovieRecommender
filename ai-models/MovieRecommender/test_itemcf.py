"""
🧪 TEST UI - Item-Based Collaborative Filtering
Profesyonel Test Arayüzü
"""
import streamlit as st
import pandas as pd
import sys
import time
from pathlib import Path

# --- AYARLAR (EN BAŞTA OLMALI) ---
st.set_page_config(page_title="Item-Based Test Lab", layout="wide", page_icon="🧪")

# Yolları ayarla
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# --- MODEL YÜKLEME ---
@st.cache_resource
def load_modules():
    try:
        from src import recommender_itemcf as itemcf
        from src import recommender_arl as arl # Mapping için
        
        # Mapping dosyasını kontrol et
        if not arl.MAPPING_PATH.exists():
            return None, None, "Mapping dosyası eksik. Lütfen terminalde 'python src/recommender_arl.py' çalıştırın."
            
        mapping = arl.load_movie_mapping()
        return itemcf, mapping, None
    except ImportError as e:
        return None, None, f"Modül hatası: {e}"
    except Exception as e:
        return None, None, f"Beklenmeyen hata: {e}"

# --- ARAYÜZ ---
st.title("🧪 Item-Based CF Test Laboratuvarı")
st.caption("Bu arayüz sadece Item-Based (Rating Benzerliği) modelini test eder.")
st.divider()

itemcf, mapping_df, error = load_modules()

if error:
    st.error(f"🚨 Hata: {error}")
    st.stop()

# Sol Panel: Ayarlar
with st.sidebar:
    st.header("⚙️ Ayarlar")
    top_n = st.slider("Öneri Sayısı", 5, 50, 10)
    st.info("Algoritma: Cosine Similarity (User-Item Matrix)")

# Ana Panel
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("1. Film Seçimi")
    # Film listesi
    movies = sorted(mapping_df['title'].unique())
    # Varsayılan seçimler
    default_selections = [m for m in ["The Dark Knight", "Inception"] if m in movies]
    
    selected_movies = st.multiselect(
        "Beğendiğiniz filmleri seçin:", 
        movies, 
        default=default_selections
    )

with col2:
    st.subheader("2. Analiz")
    st.write("") # Boşluk
    if st.button("🚀 Önerileri Getir", type="primary", use_container_width=True):
        if not selected_movies:
            st.warning("Lütfen en az bir film seçin.")
        else:
            with st.spinner("Benzerlikler hesaplanıyor..."):
                start_time = time.time()
                try:
                    # Modeli Çağır
                    recs, missing = itemcf.recommend_item_based(selected_movies, top_n)
                    duration = time.time() - start_time
                    
                    # Sonuçları Göster
                    if missing:
                        st.warning(f"⚠️ Bu filmler için yeterli veri yok: {', '.join(missing)}")
                    
                    if not recs.empty:
                        st.success(f"✅ İşlem tamamlandı ({duration:.3f} sn)")
                        
                        # Tabloyu düzenle
                        display_df = recs.copy()
                        display_df['similarity'] = display_df['similarity'].map('{:.2%}'.format)
                        display_df.columns = ["ID", "Film Adı", "Benzerlik"]
                        
                        st.dataframe(
                            display_df[["Film Adı", "Benzerlik"]], 
                            use_container_width=True,
                            height=400
                        )
                    else:
                        st.info("Sonuç bulunamadı.")
                        
                except Exception as e:
                    st.error(f"Model Hatası: {e}")