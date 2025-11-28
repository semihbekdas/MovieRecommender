from __future__ import annotations

import json
import random
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
    TitleOption,
    DEFAULT_LINKS_PATH,
    DEFAULT_RATINGS_PATH,
    evaluate_model,
    get_bundle_summary,
    get_metadata_preview,
    get_metadata_stats,
    get_rating_stats,
    get_title_options,
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

DEFAULT_EVAL_INPUTS = {
    "ratings_path": str(DEFAULT_RATINGS_PATH),
    "links_path": str(DEFAULT_LINKS_PATH),
    "n_users": 50,
    "top_n": 10,
    "mode": "standard",
    "rating_threshold": 4.0,
    "min_liked": 3,
    "method": "score_avg",
    "seed": 42,
}

EVALUATION_HELP_MD = """
**Amaç**
- MovieLens kullanıcılarından örnekler alır, her kullanıcının çok beğendiği filmlerden birini gizleyip modelin bu filmi Top-N içinde yakalayıp yakalayamadığını ölçer.

**Girdi Dosyaları**
- `ratings_small.csv`: Kullanıcı-film-puan satırları (`data/ratings_small.csv` varsayılan).
- `links_small.csv`: `movieId` → `tmdbId` eşleşmeleri (`data/links_small.csv` varsayılan).

**Parametrelerin Etkisi**
- `Test edilecek kullanıcı sayısı`: Daha yüksek değer daha uzun ama daha güvenilir sonuç verir.
- `HitRate @`: Gizlenen filmin öneri listesinde aranacağı üst sınır.
- `Değerlendirme modu`: `standard` → `recommender_content.recommend_multi`; `profile` → `user_profile.build_user_profile`.
- `Beğeni eşiği` ve `Min. beğenilen film`: Kullanıcının değerlendirmeye alınması için gereken şartlar.
- `Çoklu film yöntemi`: `score_avg` skor ortalaması; `vector_avg` TF-IDF vektör ortalaması (yalnızca `standard` modda anlamlı).
- `Rastgelelik tohumu`: Aynı kullanıcı örneklemesini tekrar üretir.

**Çalışma Adımları**
1. Dosyalar okunur ve MovieLens → TMDB eşleşmeleri hazırlanır.
2. Şartları sağlayan kullanıcılar arasından rastgele seçim yapılır.
3. Her kullanıcı için beğenilen filmlerden biri gizlenir, kalanlarla öneri listesi üretilir.
4. Gizlenen film Top-N içinde ise “hit” sayılır.

**Çıktılar**
- `HitRate@N`: `hits/tested` oranı; progress bar ve metrik olarak gösterilir.
- `Başarılı kullanıcı / Test edilen kullanıcı`: Toplam hit sayısı ve değerlendirilen kullanıcı adedi.
- `Örnek Kullanıcılar` tablosu: İlk 10 kullanıcının `userId`, gizlenen film adı/ID’si, hit durumu, rank ve gerçek rating bilgisi.

**Nasıl Yorumlanır?**
- Yüksek HitRate, modelin sevilen filmleri üst sıralara getirdiğini gösterir.
- Hiç kullanıcı test edilemiyorsa threshold/min_liked değerleri fazla sıkı olabilir.
- `rank` değerleri düşükse (1-3) model gizlenen filmi üst sıralarda konumlandırıyor demektir.
"""


@st.cache_resource(show_spinner=False)
def warmup_bundle(reload_token: int) -> Any:
    """Streamlit oturumu boyunca artefaktları cache’le."""
    return services.load_bundle(force_reload=reload_token > 0)


@st.cache_data(show_spinner=False)
def cached_metadata_preview(limit: int = 25) -> pd.DataFrame | None:
    return get_metadata_preview(limit)


@st.cache_data(show_spinner=False)
def cached_title_options(limit: int = 5000) -> tuple[list[str], dict[str, TitleOption]]:
    options = get_title_options(limit=limit)
    label_map = {opt.label: opt for opt in options}
    labels = list(label_map.keys())
    return labels, label_map


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
        top_n = st.slider(
            "Top-N öneri",
            min_value=5,
            max_value=50,
            value=10,
            step=1,
            help="Öneri tablosunda kaç filmi görmek istediğinizi belirtir.",
        )
        method = st.radio(
            "Çoklu film yöntemi",
            options=list(METHOD_LABELS.keys()),
            help=(
                "score_avg: seçilen her film için skor hesaplayıp ortalamasını alır. "
                "vector_avg: TF-IDF vektörlerinin ortalaması ile tek profil oluşturur."
            ),
            format_func=lambda key: METHOD_LABELS[key],
        )
        st.caption("i) Ayarlar tüm sekmeleri etkiler; değişiklikten sonra manuel öneriyi tekrar çalıştırın.")
    return summary, top_n, method


def render_file_status_table(files: list[FileStatus]) -> None:
    if not files:
        st.info("Dosya bilgisi bulunamadı.")
        return
    st.caption("i) Bu tablo Content-Based modellerinin ihtiyaç duyduğu artefaktların mevcut durumunu gösterir.")
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
    st.caption("i) Film listesinden beğendiğiniz başlıkları arayarak seçin, ardından önerileri çalıştırın.")
    labels, label_map = cached_title_options()

    if not labels:
        st.error("Seçilebilir film listesi oluşturulamadı. Artefaktları kontrol edin.")
        return

    default_labels = [
        label
        for label in st.session_state.get("selected_title_labels", [])
        if label in label_map
    ]

    with st.form("manual-form"):
        selected_labels = st.multiselect(
            "Film arama ve seçim",
            options=labels,
            default=default_labels,
            placeholder="Film adı yazmaya başlayın...",
            help=(
                "Liste metadata setinden öne çıkan filmleri içerir. "
                "Arama kutusuna yazdığınız anda sonuçlar filtrelenir."
            ),
        )
        st.caption("i) Aynı başlığı tekrar seçmenize gerek yok; seçim kutusu otomatik olarak kontrol eder.")
        submitted = st.form_submit_button("Önerileri Çalıştır", use_container_width=True)

    st.session_state["selected_title_labels"] = selected_labels

    if submitted:
        titles = [label_map[label].title for label in selected_labels]
        if not titles:
            st.warning("Önce en az bir film seçmelisiniz.")
            return
        with st.spinner("Benzerlik skorları hesaplanıyor..."):
            response = make_recommendations(titles, top_n=top_n, method=method)
        render_recommendation_response(response)
    else:
        cached = load_last_recommendations()
        if cached is not None and not cached.empty:
            st.info("Son çalıştırılan öneriler aşağıda görüntüleniyor.")
            display_recommendation_table(cached)
        else:
            st.info("Seçim yaptıktan sonra 'Önerileri Çalıştır' butonuna basın.")


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
    st.caption("i) HitRate@N metriği ile gizlenen filmlerin öneri listesinde yer alıp almadığını ölçer.")
    with st.expander("Bu sekme nasıl çalışıyor?", expanded=False):
        st.markdown(EVALUATION_HELP_MD)

    default_ratings = st.session_state.get("ratings_path", str(DEFAULT_RATINGS_PATH))
    default_links = st.session_state.get("links_path", str(DEFAULT_LINKS_PATH))

    with st.form("evaluation-form"):
        ratings_path = st.text_input(
            "ratings_small.csv yolu",
            value=default_ratings,
            help="Kullanıcı-film puanlamalarını içeren CSV. MovieLens örneği data/ratings_small.csv."
        )
        links_path = st.text_input(
            "links_small.csv yolu",
            value=default_links,
            help="MovieLens movieId değerlerini TMDB kimliklerine eşleyen CSV."
        )
        n_users = st.slider(
            "Test edilecek kullanıcı sayısı",
            10,
            200,
            50,
            step=10,
            help="Rastgele seçilecek kullanıcı sayısı; daha yüksek değer daha uzun sürer."
        )
        eval_top_n = st.slider(
            "HitRate @",
            5,
            30,
            default_top_n,
            key="eval-topn",
            help="Kullanıcının gizlenen filmi öneri listesinde ilk N içinde yakalanırsa 'hit' sayılır."
        )
        mode = st.radio(
            "Değerlendirme modu",
            options=list(MODE_LABELS.keys()),
            index=0,
            help=(
                "standard: seçilen filmlerle rc.recommend_multi çalışır. "
                "profile: user_profile ile ağırlıklı kullanıcı vektörü oluşturur."
            ),
            format_func=lambda key: MODE_LABELS[key],
        )
        rating_threshold = st.slider(
            "Beğeni eşiği",
            3.0,
            5.0,
            4.0,
            step=0.5,
            help="Bu puanın üzerindeki filmler 'beğenilen' kabul edilip profil oluşturulur."
        )
        min_liked = st.number_input(
            "Min. beğenilen film",
            min_value=2,
            max_value=20,
            value=3,
            help="Bir kullanıcının değerlendirilmeye girebilmesi için gereken minimum beğeni adedi."
        )
        method = st.radio(
            "Çoklu film yöntemi",
            options=list(METHOD_LABELS.keys()),
            index=list(METHOD_LABELS.keys()).index(default_method),
            key="eval-method",
            help="Değerlendirme standard moduna özel; manuel öneride kullanılan aynı mantık.",
            format_func=lambda key: METHOD_LABELS[key],
        )
        seed = st.number_input(
            "Rastgelelik tohumu",
            min_value=0,
            max_value=9999,
            value=42,
            help="Aynı tohum aynı kullanıcı örneklemesiyle sonuçların tekrarlanmasını sağlar."
        )
        run_evaluation = st.form_submit_button(
            "Değerlendirmeyi Başlat",
            use_container_width=True,
        )
        st.caption("i) Bu buton evaluate_content.evaluate fonksiyonunu verilen parametrelerle çalıştırır.")

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
        payload = {
            "inputs": {
                "ratings_path": str(ratings),
                "links_path": str(links),
                "n_users": n_users,
                "top_n": eval_top_n,
                "mode": mode,
                "rating_threshold": rating_threshold,
                "min_liked": min_liked,
                "method": method,
                "seed": int(seed),
            },
            "outputs": {
                "hit_rate": response.hit_rate,
                "hits": response.hits,
                "tested": response.tested,
                "samples": response.samples,
                "error": response.error,
            },
        }
        st.session_state["last_eval_payload"] = payload
        render_evaluation_response(response, eval_top_n)

    render_share_section()


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
        payload = st.session_state.get("last_eval_payload")
        seed = None
        if payload and "inputs" in payload:
            seed = payload["inputs"].get("seed")
        rng = random.Random(seed)
        hit_samples = [s for s in samples if s.get("hit")]
        non_hit_samples = [s for s in samples if not s.get("hit")]
        rng.shuffle(non_hit_samples)
        ordered_samples = hit_samples + non_hit_samples

        st.markdown("**Örnek Kullanıcılar**")
        df = pd.DataFrame(ordered_samples)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Örnek kullanıcı verisi bulunamadı.")


def render_share_section() -> None:
    st.subheader("İnput/Output Paylaşımı")
    payload = st.session_state.get("last_eval_payload")
    if not payload:
        st.info("Önce bir değerlendirme çalıştırın, ardından sonuçları paylaşabilirsiniz.")
        return

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    st.json(payload)
    st.download_button(
        "JSON olarak indir",
        data=serialized.encode("utf-8"),
        file_name="evaluation_result.json",
        mime="application/json",
        use_container_width=True,
    )


def render_selection_logic_banner() -> None:
    payload = st.session_state.get("last_eval_payload")
    if payload and "inputs" in payload:
        inputs = payload["inputs"]
    else:
        inputs = DEFAULT_EVAL_INPUTS
    st.info(
        "Kullanıcı seçme akışı: ratings_small.csv içindeki kullanıcılardan "
        f"`rating >= {inputs['rating_threshold']}` koşulunu sağlayan ve en az "
        f"{inputs['min_liked']} favori filme sahip olanlar filtrelenir. "
        f"Rastgele {inputs['n_users']} kullanıcı seçilip her biri için bir film gizlenir; "
        f"gizlenen film öneri listesinde Top-{inputs['top_n']} içinde yer alırsa hit sayılır "
        f"(`mode={inputs['mode']}`, `method={inputs['method']}`, `seed={inputs['seed']}`)."
    )


def render_global_stats() -> None:
    st.subheader("Veri Özeti")
    meta_col1, meta_col2, meta_col3 = st.columns(3)
    try:
        meta_stats = get_metadata_stats()
        meta_col1.metric("Metadata Film Sayısı", f"{meta_stats.total_titles:,}")
        meta_col2.metric("Özet İçeren Film", f"{meta_stats.non_empty_overview:,}")
        meta_col3.metric("Benzersiz Tür Sayısı", f"{meta_stats.distinct_genres:,}")
    except Exception as exc:  # pragma: no cover - görsel uyarı
        st.warning(f"Metadata istatistikleri alınamadı: {exc}")

    ratings_path = Path(st.session_state.get("ratings_path", str(DEFAULT_RATINGS_PATH)))
    rat_col1, rat_col2, rat_col3 = st.columns(3)
    try:
        stats = get_rating_stats(str(ratings_path))
        rat_col1.metric("Ratings Satırı", f"{stats.total_rows:,}")
        rat_col2.metric("Benzersiz Kullanıcı", f"{stats.unique_users:,}")
        rat_col3.metric("Benzersiz Film", f"{stats.unique_movies:,}")
        st.caption(
            f"Kaynak: {stats.path} · Kullanıcı başına ortalama {stats.avg_ratings_per_user:.2f} puan."
        )
    except Exception as exc:  # pragma: no cover - görsel uyarı
        st.warning(f"Ratings istatistikleri alınamadı ({ratings_path}): {exc}")


def main() -> None:
    st.set_page_config(page_title="Content-Based Test Paneli", layout="wide")
    st.title("Content-Based Modelleri Test Paneli")

    if "reload_counter" not in st.session_state:
        st.session_state["reload_counter"] = 0
    st.session_state.setdefault("ratings_path", str(DEFAULT_RATINGS_PATH))
    st.session_state.setdefault("links_path", str(DEFAULT_LINKS_PATH))

    summary, top_n, method = render_sidebar()
    render_selection_logic_banner()
    render_global_stats()

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

