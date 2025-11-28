from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import services
from services import (
    BundleSummary,
    EvaluationResponse,
    FileStatus,
    RecommendationResponse,
    DEFAULT_LINKS_PATH,
    DEFAULT_RATINGS_PATH,
    evaluate_model,
    get_bundle_summary,
    get_metadata_preview,
    make_recommendations,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

METHOD_LABELS = {
    "score_avg": "score_avg · Skor ortalaması",
    "vector_avg": "vector_avg · Vektör ortalaması",
}

MODE_LABELS = {
    "standard": "standard · Çoklu film benzerliği",
    "profile": "profile · Kullanıcı profil vektörü",
}


@st.cache_resource(show_spinner=False)
def warmup_bundle(reload_token: int) -> Any:
    """Streamlit oturumu boyunca artefaktları cache’le."""
    return services.load_bundle(force_reload=reload_token > 0)


@st.cache_data(show_spinner=False)
def cached_metadata_preview(limit: int = 25) -> pd.DataFrame | None:
    return get_metadata_preview(limit)


def parse_title_input(raw_text: str) -> list[str]:
    tokens = re.split(r"[,;\n]+", raw_text)
    return [token.strip() for token in tokens if token.strip()]


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def store_last_recommendations(df: pd.DataFrame) -> None:
    st.session_state["last_recommendations"] = df.to_dict(orient="records")


def load_last_recommendations() -> pd.DataFrame | None:
    records = st.session_state.get("last_recommendations")
    if not records:
        return None
    return pd.DataFrame.from_records(records)


def render_sidebar() -> tuple[BundleSummary, int, str]:
    with st.sidebar:
        st.title("Kontroller")
        reload_clicked = st.button("Artefaktları Yeniden Yükle", use_container_width=True)
        if reload_clicked:
            st.session_state["reload_counter"] += 1

        warmup_bundle(st.session_state["reload_counter"])
        summary = get_bundle_summary(force_reload=reload_clicked)

        if summary.ready:
            st.success(summary.message)
        else:
            st.error(summary.message)

        render_file_status_table(summary.files)

        st.header("Genel Ayarlar")
        top_n = st.slider("Top-N öneri", min_value=5, max_value=50, value=10, step=1)
        method = st.radio(
            "Çoklu film yöntemi",
            options=list(METHOD_LABELS.keys()),
            format_func=lambda key: METHOD_LABELS[key],
        )
    return summary, top_n, method


def render_file_status_table(files: list[FileStatus]) -> None:
    if not files:
        st.info("Dosya bilgisi bulunamadı.")
        return
    rows = []
    for status in files:
        rows.append(
            {
                "Artefakt": status.label,
                "Durum": "Hazır" if status.exists else "Eksik",
                "Boyut (MB)": status.size_mb if status.size_mb is not None else "-",
                "Güncelleme": status.modified_at.strftime("%Y-%m-%d %H:%M")
                if status.modified_at
                else "-",
                "Dosya": relative_path(status.path),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_manual_tab(top_n: int, method: str) -> None:
    st.subheader("Manuel Öneri")
    st.caption("Film adlarını virgül, noktalı virgül veya satır sonu ile ayırabilirsiniz.")
    default_titles = st.session_state.get("last_title_input", "The Matrix, Toy Story")
    with st.form("manual-form"):
        raw_titles = st.text_area("Film listesi", value=default_titles, height=110)
        submitted = st.form_submit_button("Önerileri Çalıştır", use_container_width=True)

    if submitted:
        st.session_state["last_title_input"] = raw_titles
        titles = parse_title_input(raw_titles)
        with st.spinner("Benzerlik skorları hesaplanıyor..."):
            response = make_recommendations(titles, top_n=top_n, method=method)
        render_recommendation_response(response)
    else:
        cached = load_last_recommendations()
        if cached is not None and not cached.empty:
            st.info("Son çalıştırılan öneriler aşağıda görüntüleniyor.")
            display_recommendation_table(cached)
        else:
            st.info("Henüz bir öneri çalıştırılmadı.")


def render_recommendation_response(response: RecommendationResponse) -> None:
    if response.error:
        st.error(response.error)
        return

    if response.missing_titles:
        st.warning(f"Bulunamayan başlıklar: {', '.join(response.missing_titles)}")

    if response.used_fallback:
        st.info("Hiç eşleşme bulunamadı, popüler fallback listesi gösteriliyor.")

    df = response.dataframe
    if df is None or df.empty:
        st.warning("Gösterilecek öneri bulunamadı.")
        return

    store_last_recommendations(df)
    display_recommendation_table(df)


def display_recommendation_table(df: pd.DataFrame) -> None:
    st.dataframe(df, use_container_width=True, hide_index=True)

    if "similarity" in df.columns:
        chart_df = df.dropna(subset=["similarity"]).head(15)
        if not chart_df.empty:
            chart = chart_df.set_index("title")["similarity"]
            st.bar_chart(chart, use_container_width=True)


def render_inspection_tab() -> None:
    st.subheader("Model İncelemesi")
    df = load_last_recommendations()
    if df is None or df.empty:
        st.info("Önce 'Manuel Öneri' sekmesinden sonuç üretin.")
    else:
        titles = df["title"].tolist()
        selected = st.selectbox("İncelenecek öneri", titles)
        row = df[df["title"] == selected].iloc[0]
        col1, col2, col3 = st.columns(3)
        similarity = row.get("similarity")
        similarity_text = f"{float(similarity):.3f}" if pd.notna(similarity) else "—"
        tmdb_value = row.get("tmdb_id")
        tmdb_text = str(int(tmdb_value)) if pd.notna(tmdb_value) else "—"
        vote_avg = row.get("vote_average")
        vote_text = f"{float(vote_avg):.2f}" if pd.notna(vote_avg) else "—"
        col1.metric("Benzerlik", similarity_text)
        col2.metric("TMDB ID", tmdb_text)
        col3.metric("Oy Ortalaması", vote_text)

        st.markdown(f"**Türler:** {row.get('genres', 'N/A')}")
        st.write(row.get("overview_snippet") or "Açıklama bulunamadı.")

    st.divider()
    st.subheader("Metadata Önizlemesi")
    preview = cached_metadata_preview(25)
    if preview is not None and not preview.empty:
        st.dataframe(preview, use_container_width=True, hide_index=True)
    else:
        st.info("Metadata yüklenemedi. Artefaktların hazır olduğundan emin olun.")


def render_evaluation_tab(default_method: str, default_top_n: int) -> None:
    st.subheader("Değerlendirme Senaryosu")
    default_ratings = st.session_state.get("ratings_path", str(DEFAULT_RATINGS_PATH))
    default_links = st.session_state.get("links_path", str(DEFAULT_LINKS_PATH))

    with st.form("evaluation-form"):
        ratings_path = st.text_input("ratings_small.csv yolu", value=default_ratings)
        links_path = st.text_input("links_small.csv yolu", value=default_links)
        n_users = st.slider("Test edilecek kullanıcı sayısı", 10, 200, 50, step=10)
        eval_top_n = st.slider("HitRate @", 5, 30, default_top_n, key="eval-topn")
        mode = st.radio(
            "Değerlendirme modu",
            options=list(MODE_LABELS.keys()),
            index=0,
            format_func=lambda key: MODE_LABELS[key],
        )
        rating_threshold = st.slider("Beğeni eşiği", 3.0, 5.0, 4.0, step=0.5)
        min_liked = st.number_input("Min. beğenilen film", min_value=2, max_value=20, value=3)
        method = st.radio(
            "Çoklu film yöntemi",
            options=list(METHOD_LABELS.keys()),
            index=list(METHOD_LABELS.keys()).index(default_method),
            key="eval-method",
            format_func=lambda key: METHOD_LABELS[key],
        )
        seed = st.number_input("Rastgelelik tohumu", min_value=0, max_value=9999, value=42)
        run_evaluation = st.form_submit_button("Değerlendirmeyi Başlat", use_container_width=True)

    if run_evaluation:
        st.session_state["ratings_path"] = ratings_path
        st.session_state["links_path"] = links_path
        ratings = Path(ratings_path).expanduser()
        links = Path(links_path).expanduser()

        errors = []
        if not ratings.exists():
            errors.append(f"Ratings dosyası bulunamadı: {ratings}")
        if not links.exists():
            errors.append(f"Links dosyası bulunamadı: {links}")

        if errors:
            for err in errors:
                st.error(err)
            return

        with st.spinner("HitRate hesaplanıyor..."):
            response = evaluate_model(
                ratings_path=ratings,
                links_path=links,
                n_users=n_users,
                top_n=eval_top_n,
                mode=mode,
                rating_threshold=rating_threshold,
                min_liked=min_liked,
                method=method,
                seed=int(seed),
            )
        render_evaluation_response(response, eval_top_n)


def render_evaluation_response(response: EvaluationResponse, top_n: int) -> None:
    if response.error:
        st.error(response.error)
        return

    hit_rate = response.hit_rate if response.hit_rate is not None else 0.0
    hits = response.hits if response.hits is not None else 0
    tested = response.tested if response.tested is not None else 0

    col1, col2, col3 = st.columns(3)
    col1.metric(f"HitRate@{top_n}", f"{hit_rate:.3f}")
    col2.metric("Başarılı kullanıcı", hits)
    col3.metric("Test edilen kullanıcı", tested)

    st.progress(hit_rate if hit_rate <= 1 else 1.0)

    samples = response.samples or []
    if samples:
        st.markdown("**Örnek Kullanıcılar**")
        df = pd.DataFrame(samples)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Örnek kullanıcı verisi bulunamadı.")


def main() -> None:
    st.set_page_config(page_title="Content-Based Test Paneli", layout="wide")
    st.title("Content-Based Modelleri Test Paneli")

    if "reload_counter" not in st.session_state:
        st.session_state["reload_counter"] = 0

    summary, top_n, method = render_sidebar()

    tab_manual, tab_inspect, tab_eval = st.tabs(
        ["Manuel Öneri", "Model İncelemesi", "Değerlendirme Senaryosu"]
    )

    with tab_manual:
        render_manual_tab(top_n, method)
    with tab_inspect:
        render_inspection_tab()
    with tab_eval:
        render_evaluation_tab(method, top_n)

    if not summary.ready:
        st.warning("Artefaktlar hazır olmadan sonuçlar eksik olabilir.")


if __name__ == "__main__":
    main()

