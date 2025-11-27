"""
📊 DATASET INSIGHTS - VERİ ANALİZİ VE GRAFİKLER
Ağır işlemler: CSV okuma, NetworkX, görselleştirmeler

Bu sayfa yalnızca gerektiğinde yüklenir.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from datetime import datetime

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src import recommender_arl as arl

st.set_page_config(
    page_title="📊 Dataset Insights",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    """
<style>
    .metric-card {
        background: linear-gradient(135deg, #1f1c2c 0%, #928dab 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    .insight-box {
        background: linear-gradient(135deg, #1f1c2c 0%, #3a1c71 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 6px solid #ff6a00;
        margin: 1.5rem 0;
        color: #f4f4ff;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_raw_frames():
    """Ham CSV'leri oku - AĞIR İŞLEM."""
    return arl.load_raw_data()


@st.cache_data(show_spinner=False)
def load_artifacts():
    """Model dosyaları."""
    mapping_df = arl.load_movie_mapping()
    rules_df = arl.load_association_rules()
    metadata = arl.load_artifact_metadata()
    return mapping_df, rules_df, metadata


@st.cache_data(show_spinner=False)
def compute_overview_stats(ratings_df: pd.DataFrame, mapping_df: pd.DataFrame, min_rating: float):
    """Genel metrikler."""
    liked_df = arl.filter_liked_ratings(ratings_df, min_rating=min_rating)
    user_like_counts = liked_df.groupby("userId")["movieId"].nunique()
    return {
        "total_ratings": len(ratings_df),
        "total_users": ratings_df["userId"].nunique(),
        "total_movies": mapping_df["movieId"].nunique(),
        "avg_rating": ratings_df["rating"].mean(),
        "avg_liked_per_user": user_like_counts.mean() if not user_like_counts.empty else 0.0,
    }


@st.cache_data(show_spinner=False)
def top_movies_by_count(
    ratings_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    top_n: int = 15,
    liked_only: bool = False,
    min_rating: float | None = None,
) -> pd.DataFrame:
    """En çok izlenen filmler."""
    df = ratings_df
    if liked_only:
        threshold = min_rating if min_rating is not None else arl.DEFAULT_MIN_RATING
        df = arl.filter_liked_ratings(ratings_df, min_rating=threshold)
    counts = df["movieId"].value_counts().head(top_n).reset_index()
    counts.columns = ["movieId", "count"]
    merged = counts.merge(mapping_df, on="movieId", how="left")
    return merged


@st.cache_data(show_spinner=False)
def user_activity_histogram(ratings_df: pd.DataFrame) -> list[int]:
    """Kullanıcı başına film sayısı."""
    per_user = ratings_df.groupby("userId")["movieId"].nunique()
    return per_user.tolist()


def _parse_genres(value: str) -> list[str]:
    """Genres alanını parse et."""
    if not isinstance(value, str):
        return []
    try:
        parsed = ast.literal_eval(value)
        return [item.get("name") for item in parsed if isinstance(item, dict) and "name" in item]
    except (ValueError, SyntaxError, TypeError):
        return []


@st.cache_data(show_spinner=False)
def genre_popularity(metadata_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Tür dağılımı."""
    genres_series = metadata_df["genres"].apply(_parse_genres)
    exploded = genres_series.explode().dropna()
    counts = exploded.value_counts().head(top_n).reset_index()
    counts.columns = ["genre", "count"]
    return counts


def ids_to_titles(id_set, mapping_df: pd.DataFrame) -> list[str]:
    """ID → Title."""
    id_to_title = mapping_df.set_index("movieId")["title"].to_dict()
    return [id_to_title.get(mid, f"Movie {mid}") for mid in id_set]


@st.cache_data(show_spinner=False)
def rules_with_titles(rules_df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    """Kurallara başlık ekle."""
    if rules_df.empty:
        return rules_df
    df = rules_df.copy()
    df["antecedents_str"] = df["antecedents"].apply(lambda s: ", ".join(ids_to_titles(s, mapping_df)))
    df["consequents_str"] = df["consequents"].apply(lambda s: ", ".join(ids_to_titles(s, mapping_df)))
    return df


@st.cache_data(show_spinner=False)
def compute_genre_analysis(metadata_df: pd.DataFrame, mapping_df: pd.DataFrame, ratings_df: pd.DataFrame, top_n: int = 15):
    """Tür analizi."""
    genre_counts = genre_popularity(metadata_df, top_n=top_n)
    
    top_genres = genre_counts.head(10)['genre'].tolist()
    genre_cooc_data = []
    
    for i, g1 in enumerate(top_genres):
        for g2 in top_genres[i+1:]:
            count = np.random.randint(50, 500)  # Simülasyon
            genre_cooc_data.append({'Genre1': g1, 'Genre2': g2, 'Count': count})
    
    genre_cooc_df = pd.DataFrame(genre_cooc_data).sort_values('Count', ascending=False).head(20)
    
    return genre_counts, genre_cooc_df


@st.cache_data(show_spinner=False)
def compute_advanced_metrics(rules_df: pd.DataFrame) -> dict:
    """İleri metrikleri hesapla."""
    if rules_df.empty:
        return {}
    
    metrics = {
        'total_rules': len(rules_df),
        'avg_support': rules_df['support'].mean(),
        'avg_confidence': rules_df['confidence'].mean(),
        'avg_lift': rules_df['lift'].mean(),
        'avg_leverage': rules_df['leverage'].mean() if 'leverage' in rules_df.columns else 0,
        'strong_rules': len(rules_df[rules_df['lift'] > 2.0]),
        'very_strong_rules': len(rules_df[rules_df['lift'] > 3.0]),
        'max_lift': rules_df['lift'].max(),
        'max_confidence': rules_df['confidence'].max(),
        'median_support': rules_df['support'].median(),
    }
    
    if 'consequent support' in rules_df.columns:
        conviction = (1 - rules_df['consequent support']) / (1 - rules_df['confidence'])
        conviction = conviction.replace([np.inf, -np.inf], np.nan)
        metrics['avg_conviction'] = conviction.dropna().mean()
        metrics['max_conviction'] = conviction.dropna().max()
    else:
        metrics['avg_conviction'] = 0
        metrics['max_conviction'] = 0
    
    return metrics


def create_3d_scatter(rules_df: pd.DataFrame, mapping_df: pd.DataFrame, sample_size: int = 200):
    """3D scatter: support × confidence × lift."""
    if rules_df.empty:
        return None
    
    sample_rules = rules_df.sample(n=min(sample_size, len(rules_df)), random_state=42).copy()
    
    def ids_to_names(id_set):
        id_to_title = mapping_df.set_index('movieId')['title'].to_dict()
        return ', '.join([id_to_title.get(mid, f"Movie {mid}") for mid in list(id_set)[:2]])
    
    sample_rules['antecedents_str'] = sample_rules['antecedents'].apply(ids_to_names)
    sample_rules['consequents_str'] = sample_rules['consequents'].apply(ids_to_names)
    sample_rules['rule'] = sample_rules.apply(
        lambda x: f"{x['antecedents_str']} → {x['consequents_str']}",
        axis=1
    )
    
    fig = go.Figure(data=[go.Scatter3d(
        x=sample_rules['support'],
        y=sample_rules['confidence'],
        z=sample_rules['lift'],
        mode='markers',
        marker=dict(
            size=8,
            color=sample_rules['lift'],
            colorscale='Turbo',
            showscale=True,
            colorbar=dict(title="Lift"),
            line=dict(width=0.5, color='white')
        ),
        text=sample_rules['rule'],
        hovertemplate='<b>%{text}</b><br>Support: %{x:.3f}<br>Confidence: %{y:.3f}<br>Lift: %{z:.2f}<extra></extra>'
    )])
    
    fig.update_layout(
        title='3D Rule Space',
        scene=dict(xaxis_title='Support', yaxis_title='Confidence', zaxis_title='Lift'),
        height=600,
    )
    
    return fig


def network_graph(rules_df: pd.DataFrame, mapping_df: pd.DataFrame, top_n: int = 20):
    """NetworkX network grafiği - AĞIR İŞLEM."""
    if rules_df.empty:
        return None

    top_rules = rules_df.nlargest(top_n, "lift")
    G = nx.DiGraph()

    for _, row in top_rules.iterrows():
        antecedent_title = ", ".join(ids_to_titles(row["antecedents"], mapping_df))
        consequent_title = ", ".join(ids_to_titles(row["consequents"], mapping_df))
        G.add_edge(antecedent_title, consequent_title, weight=row["lift"])

    if G.number_of_edges() == 0:
        return None

    pos = nx.spring_layout(G, k=0.6, iterations=60, seed=42)
    
    edge_traces = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_traces.append(
            go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                mode="lines",
                line=dict(width=2, color="#888"),
                hoverinfo="none",
            )
        )

    node_x, node_y, node_text, node_size = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_size.append(18 + 4 * G.degree(node))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        marker=dict(size=node_size, color="#ff6a00", line=dict(width=2, color="#fff")),
        hoverinfo="text",
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        title="Film Birliktelik Ağı",
        showlegend=False,
        hovermode="closest",
        margin=dict(b=0, l=0, r=0, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=620,
    )
    return fig


def plot_metric_card(title: str, value: str):
    st.markdown(
        f"""
        <div class="metric-card">
            <h4 style="margin: 0; opacity: 0.9;">{title}</h4>
            <h2 style="margin: 0.5rem 0 0; font-size: 2.2rem;">{value}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.title("📊 Dataset Insights")
    st.caption("Detaylı veri analizi ve görselleştirmeler")
    st.markdown("---")

    st.markdown(
        """
        <div class="insight-box">
            <b>ℹ️ Bu sayfa hakkında:</b><br/>
            Bu sayfa ham CSV verilerini yükler ve detaylı analiz yapar. İlk yükleme 8-10 saniye sürebilir.
            Ana öneri sayfası bu yüklemelerden etkilenmez.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Veri yükleme
    try:
        with st.spinner("📂 Ham veriler yükleniyor... (8-10 saniye)"):
            ratings_df, _links_df, metadata_df = load_raw_frames()
            mapping_df, rules_df, metadata = load_artifacts()
    except Exception as exc:
        st.error(f"❌ Veri yüklenemedi: {exc}")
        st.stop()

    st.success("✅ Veriler yüklendi!")

    # İstatistikler
    min_rating = metadata.get('min_rating_for_like', arl.DEFAULT_MIN_RATING) if metadata else arl.DEFAULT_MIN_RATING
    overview_stats = compute_overview_stats(ratings_df, mapping_df, min_rating)
    top_rated = top_movies_by_count(ratings_df, mapping_df, top_n=15, liked_only=False)
    top_liked = top_movies_by_count(ratings_df, mapping_df, top_n=15, liked_only=True, min_rating=min_rating)
    user_activity = user_activity_histogram(ratings_df)
    genre_df, genre_cooc_df = compute_genre_analysis(metadata_df, mapping_df, ratings_df)
    titled_rules = rules_with_titles(rules_df, mapping_df)
    advanced_metrics = compute_advanced_metrics(rules_df)

    # Genel bakış
    st.subheader("1️⃣ Genel Bakış")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        plot_metric_card("Toplam Film", f"{overview_stats['total_movies']:,}")
    with col2:
        plot_metric_card("Toplam Kullanıcı", f"{overview_stats['total_users']:,}")
    with col3:
        plot_metric_card("Toplam Rating", f"{overview_stats['total_ratings']:,}")
    with col4:
        plot_metric_card("Ort. Beğeni/Kullanıcı", f"{overview_stats['avg_liked_per_user']:.1f}")

    st.markdown("---")

    # Veri analizi
    st.subheader("2️⃣ Veri Analizi")
    col_a, col_b = st.columns([1.2, 1])
    
    with col_a:
        st.markdown("#### 🎟️ En Çok Rating Alan Filmler")
        if not top_rated.empty:
            fig = px.bar(top_rated, x="title", y="count", color_discrete_sequence=["#ee0979"])
            fig.update_layout(height=420, xaxis_title="Film", yaxis_title="Rating Sayısı")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_b:
        st.markdown("#### 👥 Kullanıcı Başına Film Sayısı")
        fig = px.histogram(x=user_activity, nbins=20, labels={"x": "Film Sayısı", "y": "Kullanıcı"}, color_discrete_sequence=["#1f1c2c"])
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    col_c, col_d = st.columns(2)
    
    with col_c:
        st.markdown("#### ⭐ En Çok Beğenilen Filmler")
        if not top_liked.empty:
            fig = px.bar(top_liked, x="title", y="count", color_discrete_sequence=["#ff6a00"])
            fig.update_layout(height=420, xaxis_title="Film", yaxis_title="Beğeni Sayısı")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_d:
        st.markdown("#### 🎞️ Tür Dağılımı")
        if not genre_df.empty:
            fig = px.pie(genre_df, names="genre", values="count", color_discrete_sequence=px.colors.sequential.Oranges)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=420, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Association Rules
    st.subheader("3️⃣ Association Rules Analizi")
    if not titled_rules.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            plot_metric_card("Toplam Kural", f"{len(titled_rules):,}")
        with col2:
            plot_metric_card("Ort. Confidence", f"{titled_rules['confidence'].mean():.2f}")
        with col3:
            plot_metric_card("Ort. Lift", f"{titled_rules['lift'].mean():.2f}")

        col4, col5, col6 = st.columns(3)
        with col4:
            fig = px.histogram(titled_rules, x="support", nbins=30, title="Support Dağılımı")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        with col5:
            fig = px.histogram(titled_rules, x="confidence", nbins=30, title="Confidence Dağılımı")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        with col6:
            fig = px.histogram(titled_rules, x="lift", nbins=30, title="Lift Dağılımı")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 🎯 Support vs Confidence")
        titled_rules["rule"] = titled_rules.apply(
            lambda x: f"{x['antecedents_str']} → {x['consequents_str']}", axis=1
        )
        fig = px.scatter(
            titled_rules,
            x="support",
            y="confidence",
            size="lift",
            color="lift",
            hover_data=["rule"],
            color_continuous_scale="Turbo",
            height=480,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 🌐 3D Rule Space")
        fig_3d = create_3d_scatter(titled_rules, mapping_df, sample_size=200)
        if fig_3d:
            st.plotly_chart(fig_3d, use_container_width=True)
        
        st.markdown("#### 🕸️ Film Birliktelik Ağı")
        with st.spinner("Network grafiği oluşturuluyor... (NetworkX)"):
            fig_net = network_graph(titled_rules, mapping_df, top_n=20)
            if fig_net:
                st.plotly_chart(fig_net, use_container_width=True)
    else:
        st.warning("Kural bulunamadı.")

    st.markdown("---")

    # İleri analiz
    st.subheader("4️⃣ İleri Analiz")
    if advanced_metrics:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center;">
                <h3>📊 Conviction</h3>
                <h1>{advanced_metrics.get('avg_conviction', 0):.2f}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center;">
                <h3>🎯 Leverage</h3>
                <h1>{advanced_metrics.get('avg_leverage', 0):.4f}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center;">
                <h3>💪 Max Lift</h3>
                <h1>{advanced_metrics.get('max_lift', 0):.2f}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center;">
                <h3>⚡ Güçlü Kurallar</h3>
                <h1>{advanced_metrics.get('strong_rules', 0)}</h1>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Dışa aktarım
    st.subheader("5️⃣ Dışa Aktarım")
    if not titled_rules.empty:
        export_rules = titled_rules.copy()
        export_rules["antecedents"] = export_rules["antecedents_str"]
        export_rules["consequents"] = export_rules["consequents_str"]
        csv = export_rules[["antecedents", "consequents", "support", "confidence", "lift"]].to_csv(index=False)
        
        st.download_button(
            label="📥 Kuralları CSV İndir",
            data=csv,
            file_name=f"association_rules_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
