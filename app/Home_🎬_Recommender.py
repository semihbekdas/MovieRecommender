"""
🎬 MOVIE RECOMMENDER - ANA SAYFA
Hızlı öneri sistemi - Sadece model dosyaları ile çalışır

İlk yükleme: ~1 saniye ⚡
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import pandas as pd
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src import recommender_arl as arl

FILTER_MIN_SUPPORT = 0.01
FILTER_MIN_CONFIDENCE = 0.30
FILTER_MIN_LIFT = 1.0

st.set_page_config(
    page_title="🎬 Movie Recommender Pro",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(90deg, #ff6a00 0%, #ee0979 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 1.5rem 0;
        letter-spacing: -1px;
    }
    .sub-header {
        text-align: center;
        font-size: 1.3rem;
        color: #666;
        margin-top: -1rem;
        margin-bottom: 2rem;
    }
    .movie-card {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        margin-bottom: 1.5rem;
    }
    .insight-box {
        background: linear-gradient(135deg, #1f1c2c 0%, #3a1c71 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 6px solid #ff6a00;
        margin: 1.5rem 0;
        box-shadow: 0 8px 30px rgba(0,0,0,0.35);
        color: #f4f4ff;
    }
    .stTabs [data-baseweb="tab-list"] { 
        gap: 1.5rem;
        background: linear-gradient(90deg, #f7f9fc 0%, #e8eef5 100%);
        padding: 1rem;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-weight: 700;
        font-size: 1.1rem;
        border-radius: 8px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #ff6a00 0%, #ee0979 100%);
        color: white !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_artifacts():
    """Model dosyalarını yükle (PKL only - HIZLI)."""
    if not arl.MAPPING_PATH.exists() or not arl.RULES_PATH.exists():
        raise FileNotFoundError(
            "Model dosyaları bulunamadı! Terminalde şu komutu çalıştırın:\n\n"
            "    python src/recommender_arl.py\n\n"
        )
    
    mapping_df = arl.load_movie_mapping()
    rules_df = arl.load_association_rules()
    metadata = arl.load_artifact_metadata()
    
    return mapping_df, rules_df, metadata


@st.cache_data(show_spinner=False)
def filter_rules(rules_full: pd.DataFrame, min_sup: float, min_conf: float, min_lft: float) -> pd.DataFrame:
    """Kuralları filtrele."""
    return rules_full[
        (rules_full['support'] >= min_sup) &
        (rules_full['confidence'] >= min_conf) &
        (rules_full['lift'] >= min_lft)
    ].copy()


@st.cache_data(show_spinner=False)
def get_sorted_titles(mapping: pd.DataFrame) -> list[str]:
    """Film listesi."""
    return sorted(mapping["title"].dropna().unique().tolist())


def ids_to_titles(id_set, mapping_df: pd.DataFrame) -> list[str]:
    """ID → Title."""
    id_to_title = mapping_df.set_index("movieId")["title"].to_dict()
    return [id_to_title.get(mid, f"Movie {mid}") for mid in id_set]


@st.cache_data(show_spinner=False)
def recommend_from_rules(
    liked_titles: tuple[str, ...],  # List yerine tuple (hashable olmalı)
    mapping_df: pd.DataFrame,
    rules_df: pd.DataFrame,
    top_n: int = 10,
) -> tuple[pd.DataFrame, list[str], dict]:
    """Öneri üret."""
    empty_df = pd.DataFrame(columns=["title", "movieId", "score", "confidence", "lift", "support"])
    stats = {"liked_count": 0, "candidate_rules": 0, "suggestion_rows": 0}

    if not liked_titles or rules_df.empty:
        return empty_df, [], stats

    liked_ids, missing_titles = arl._titles_to_movie_ids(liked_titles, mapping_df)
    stats["liked_count"] = len(liked_ids)
    if not liked_ids:
        return empty_df, missing_titles, stats

    liked_set = set(liked_ids)
    subset_mask = rules_df["antecedents"].apply(lambda ants: bool(ants) and ants.issubset(liked_set))
    candidate_rules = rules_df[subset_mask]
    stats["candidate_rules"] = len(candidate_rules)
    if candidate_rules.empty:
        return empty_df, missing_titles, stats

    suggestions: list[dict] = []
    for _, row in candidate_rules.iterrows():
        for movie_id in row["consequents"]:
            if movie_id in liked_set:
                continue
            suggestions.append(
                {
                    "movieId": int(movie_id),
                    "support": row["support"],
                    "confidence": row["confidence"],
                    "lift": row["lift"],
                    "score": row.get("score", row["confidence"] * row["lift"]),
                }
            )

    if not suggestions:
        return empty_df, missing_titles, stats

    recommendation_df = (
        pd.DataFrame(suggestions)
        .groupby("movieId")
        .agg(
            support=("support", "max"),
            confidence=("confidence", "max"),
            lift=("lift", "max"),
            score=("score", "max"),
        )
        .reset_index()
    )

    recommendation_df = recommendation_df.merge(mapping_df[["movieId", "title"]], on="movieId", how="left")
    recommendation_df = recommendation_df[
        ["title", "movieId", "score", "confidence", "lift", "support"]
    ].sort_values(["score", "confidence", "lift"], ascending=False)
    stats["suggestion_rows"] = len(recommendation_df)

    return recommendation_df.head(top_n), missing_titles, stats


def global_top_recommendations(rules_df: pd.DataFrame, mapping_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """En yüksek lift'li filmler (fallback)."""
    if rules_df.empty:
        return pd.DataFrame(columns=["title", "movieId", "score", "confidence", "lift", "support"])

    suggestions: list[dict] = []
    for _, row in rules_df.sort_values("lift", ascending=False).iterrows():
        for movie_id in row["consequents"]:
            suggestions.append(
                {
                    "movieId": int(movie_id),
                    "support": row.get("support", 0),
                    "confidence": row.get("confidence", 0),
                    "lift": row.get("lift", 0),
                    "score": row.get("score", row.get("confidence", 0) * row.get("lift", 0)),
                }
            )

    if not suggestions:
        return pd.DataFrame(columns=["title", "movieId", "score", "confidence", "lift", "support"])

    fallback_df = pd.DataFrame(suggestions).drop_duplicates("movieId")
    fallback_df = fallback_df.merge(mapping_df[["movieId", "title"]], on="movieId", how="left")
    fallback_df = fallback_df[["title", "movieId", "score", "confidence", "lift", "support"]]
    fallback_df = fallback_df.sort_values(["score", "lift", "confidence"], ascending=False)
    return fallback_df.head(top_n)


def main():
    st.markdown('<h1 class="main-header">🎬 Movie Recommender Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Birliktelik kurallarıyla akıllı film önerileri</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown(
        """
        <div class="insight-box">
            <b>⚡ Hızlı Öneri:</b><br/>
            1️⃣ Soldaki menüden sevdiğiniz filmleri seçin<br/>
            2️⃣ Sistem otomatik olarak benzer filmleri listeler<br/>
            3️⃣ Detaylı analiz için <b>📊 Dataset Insights</b> sayfasına gidin
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar
    min_support = FILTER_MIN_SUPPORT
    min_confidence = FILTER_MIN_CONFIDENCE
    min_lift = FILTER_MIN_LIFT

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/200/movie-projector.png", width=150)
        st.title("⚙️ Ayarlar")

        st.markdown("### 🎯 Öneri Sayısı")
        top_n = st.slider("Kaç öneri?", min_value=5, max_value=30, value=10, step=1)

        st.markdown("### 📐 Kural Eşikleri")
        tab_default, tab_custom = st.tabs(["🔒 Varsayılan", "⚙️ İleri"])
        
        with tab_default:
            st.metric("Min Support", f">= {FILTER_MIN_SUPPORT:.3f}")
            st.metric("Min Confidence", f">= {FILTER_MIN_CONFIDENCE:.2f}")
            st.metric("Min Lift", f">= {FILTER_MIN_LIFT:.1f}")
        
        with tab_custom:
            advanced_enabled = st.toggle("İleri ayar etkinleştir", value=False)
            custom_support = st.slider("Min Support", 0.005, 0.10, FILTER_MIN_SUPPORT, 0.005, disabled=not advanced_enabled)
            custom_confidence = st.slider("Min Confidence", 0.10, 0.90, FILTER_MIN_CONFIDENCE, 0.05, disabled=not advanced_enabled)
            custom_lift = st.slider("Min Lift", 1.0, 5.0, FILTER_MIN_LIFT, 0.1, disabled=not advanced_enabled)
            
            if advanced_enabled:
                min_support = custom_support
                min_confidence = custom_confidence
                min_lift = custom_lift

        st.markdown("---")
        st.markdown("### 🎬 Film Seçimi")

    # Model yükleme
    try:
        with st.spinner("⚡ Model yükleniyor..."):
            mapping_df, rules_df_full, metadata = load_artifacts()
    except FileNotFoundError as exc:
        st.error(f"❌ {exc}")
        st.code("python src/recommender_arl.py", language="bash")
        st.stop()
    except Exception as exc:
        st.error(f"❌ Hata: {exc}")
        st.stop()

    rules_df = filter_rules(rules_df_full, min_support, min_confidence, min_lift)
    st.success(f"✅ {len(rules_df):,} / {len(rules_df_full):,} kural yüklendi!")

    title_options = get_sorted_titles(mapping_df)
    
    # Session state ile kullanıcı seçimini koru
    if 'liked_movies' not in st.session_state:
        # İlk açılışta örnek filmler göster
        st.session_state.liked_movies = [t for t in ["Inception", "Interstellar", "The Dark Knight"] if t in title_options]

    with st.sidebar:
        liked_titles = st.multiselect(
            "Sevdiğiniz filmler",
            options=title_options,
            default=st.session_state.liked_movies,
            help="Film adı yazarak arayabilirsiniz",
            key="movie_selector"
        )
        
        # Kullanıcı seçimini session'a kaydet
        if liked_titles != st.session_state.liked_movies:
            st.session_state.liked_movies = liked_titles

    # Öneri sistemi
    st.markdown("---")
    st.subheader("🎯 Film Önerileri")

    recs = pd.DataFrame()
    missing_titles = []
    fallback_used = False

    if not liked_titles:
        st.info("💭 Sol menüden film seçin.")
        recs = global_top_recommendations(rules_df, mapping_df, top_n)
        fallback_used = True
    else:
        st.markdown("#### 🎬 Seçtiğiniz Filmler")
        cols = st.columns(min(4, len(liked_titles)))
        gradients = [
            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        ]
        for idx, title in enumerate(liked_titles):
            col = cols[idx % len(cols)]
            col.markdown(f"""
            <div style="background: {gradients[idx % len(gradients)]}; padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 1rem;">
                <b>✓ {title}</b>
            </div>
            """, unsafe_allow_html=True)
        
        with st.spinner("🔍 Öneriler hesaplanıyor..."):
            recs, missing_titles, stats = recommend_from_rules(
                tuple(liked_titles),  # List → Tuple (cache için gerekli)
                mapping_df, 
                rules_df, 
                top_n
            )
        
        if missing_titles:
            st.warning(f"⚠️ Bulunamayan: {', '.join(missing_titles)}")
        
        st.info(f"🎯 {stats.get('candidate_rules', 0):,} kural eşleşti")
        
        if recs.empty:
            st.warning("😔 Bu kombinasyon için öneri bulunamadı. Daha popüler filmler deneyin.")
            recs = global_top_recommendations(rules_df, mapping_df, top_n)
            if not recs.empty:
                fallback_used = True
                st.info("🔁 Genel öneriler gösteriliyor")

    # Öneri kartları
    if not recs.empty:
        st.markdown("---")
        if fallback_used:
            st.success(f"✨ {len(recs)} genel öneri")
        else:
            st.success(f"🎉 {len(recs)} kişisel öneri bulundu!")

        st.markdown("#### 🌟 Öneriler")
        
        grid_cols = st.columns(3)
        for idx, (_, row) in enumerate(recs.iterrows()):
            col = grid_cols[idx % 3]
            gradients = [
                'linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)',
                'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
                'linear-gradient(135deg, #134e5e 0%, #71b280 100%)',
            ]
            
            col.markdown(
                f"""
                <div style="background: {gradients[idx % 3]}; padding: 1.5rem; border-radius: 15px; color: white; box-shadow: 0 6px 20px rgba(0,0,0,0.3); margin-bottom: 1.5rem;">
                    <h3 style="margin-top: 0;">#{idx+1} {row['title']}</h3>
                    <hr style="border: 1px solid rgba(255,255,255,0.3); margin: 1rem 0;">
                    <div style="display: flex; justify-content: space-between; margin: 0.5rem 0;">
                        <span>📊 Score:</span>
                        <b>{row['score']:.2f}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin: 0.5rem 0;">
                        <span>🎯 Confidence:</span>
                        <b>{row['confidence']:.1%}</b>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin: 0.5rem 0;">
                        <span>🚀 Lift:</span>
                        <b>{row['lift']:.2f}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown("---")
        st.markdown("#### 📋 Detaylı Tablo")
        display_df = recs[["title", "score", "confidence", "lift", "support"]].copy()
        display_df.columns = ["Film", "Skor", "Confidence", "Lift", "Support"]
        st.dataframe(display_df, use_container_width=True, height=400)
    
    st.markdown("---")
    st.info("💡 **İpucu:** Detaylı analiz, grafikler ve istatistikler için sol menüden **📊 Dataset Insights** sayfasına gidin!")


if __name__ == "__main__":
    main()