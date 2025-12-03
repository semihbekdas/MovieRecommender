from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import plotly.express as px
import plotly.graph_objects as go

import services
from services import (
    BundleSummary,
    ComparisonResult,
    EvaluationResponse,
    FileStatus,
    RecommendationResponse,
    TitleOption,
    DEFAULT_LINKS_PATH,
    DEFAULT_RATINGS_PATH,
    evaluate_model,
    evaluate_multiple_thresholds,
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
    "min_liked": 5,
    "method": "score_avg",
    "seed": 42,
    "n_hidden": 2,
}

EVALUATION_HELP_MD = """
**Amaç**
- MovieLens kullanıcılarından örnekler alır, her kullanıcının çok beğendiği filmlerden **K tanesini gizleyip** modelin bu filmleri Top-N içinde yakalayıp yakalayamadığını ölçer.

**Leave-K-Out Yaklaşımı**
- `n_hidden=1`: Klasik leave-one-out (tek film gizle)
- `n_hidden=2+`: Birden fazla film gizle, kaç tanesi yakalandığına bak (daha gerçekçi değerlendirme)

**Girdi Dosyaları**
- `ratings.csv`: Kullanıcı-film-puan satırları (`data/ratings.csv` varsayılan).
- `links.csv`: `movieId` → `tmdbId` eşleşmeleri (`data/links.csv` varsayılan).

**Parametrelerin Etkisi**
- `Test edilecek kullanıcı sayısı`: Daha yüksek değer daha uzun ama daha güvenilir sonuç verir.
- `HitRate @`: Gizlenen filmlerin öneri listesinde aranacağı üst sınır (Top-N).
- `Gizlenecek film sayısı`: Her kullanıcı için kaç film gizleneceği (Leave-K-Out).
- `Değerlendirme modu`: `standard` → `recommender_content.recommend_multi`; `profile` → `user_profile.build_user_profile`.
- `Beğeni eşiği` ve `Min. beğenilen film`: Kullanıcının değerlendirmeye alınması için gereken şartlar.
- `Çoklu film yöntemi`: `score_avg` skor ortalaması; `vector_avg` TF-IDF vektör ortalaması (yalnızca `standard` modda anlamlı).
- `Rastgelelik tohumu`: Aynı kullanıcı örneklemesini tekrar üretir.

**Çalışma Adımları**
1. Dosyalar okunur ve MovieLens → TMDB eşleşmeleri hazırlanır.
2. Şartları sağlayan kullanıcılar arasından rastgele seçim yapılır.
3. Her kullanıcı için beğenilen filmlerden **K tanesi rastgele gizlenir**, kalanlarla öneri listesi üretilir.
4. Gizlenen filmlerden Top-N içinde olanlar "hit" sayılır.

**Çıktılar**
- `HitRate`: `toplam_hit / toplam_gizlenen` oranı
- `Avg Recall@N`: Kullanıcı başına gizlenenlerden kaçı Top-N'de (ortalama)
- `Avg Precision@N`: Kullanıcı başına Top-N'den kaçı gizlenenlerden (ortalama)
- `Örnek Kullanıcılar` tablosu: Kullanıcı bazlı hit sayısı ve detaylar

**Nasıl Yorumlanır?**
- Yüksek HitRate/Recall, modelin sevilen filmleri Top-N'de yakalayabildiğini gösterir.
- `n_hidden>1` ile daha robust sonuçlar elde edilir (tek filme bağımlılık azalır).
- Hiç kullanıcı test edilemiyorsa threshold/min_liked değerleri fazla sıkı olabilir.
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


def render_sidebar() -> tuple[BundleSummary, int, str, dict[str, bool]]:
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

        st.markdown("### 🧪 Deneysel Ayarlar")
        manual_filter = st.checkbox(
            "Manuel önerilerde MovieLens filtresi + pop ağırlığı",
            help="Öneri listesini links.csv içindeki filmlerle sınırlar ve popülerlik ağırlığı uygular.",
            key="option_manual_movielens_filter",
        )
        manual_profile = st.checkbox(
            "Manuel önerilerde kullanıcı profil vektörü",
            help="Seçilen filmlerden tek bir kullanıcı profili oluşturur ve cosine benzerliği ile önerir.",
            key="option_manual_profile",
        )
        eval_filter = st.checkbox(
            "HitRate hesaplarında MovieLens filtresi",
            help="Değerlendirme sırasında yalnızca MovieLens kataloğundaki filmler hit olarak kabul edilir.",
            key="option_eval_movielens_filter",
        )

    options = {
        "manual_movielens_filter": bool(manual_filter),
        "manual_profile_backend": bool(manual_profile),
        "eval_movielens_filter": bool(eval_filter),
    }
    return summary, top_n, method, options


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


def render_manual_tab(top_n: int, method: str, options: dict[str, bool]) -> None:
    st.subheader("Manuel Öneri")
    st.caption("i) Film listesinden beğendiğiniz başlıkları arayarak seçin, ardından önerileri çalıştırın.")
    if options.get("manual_movielens_filter"):
        st.info("MovieLens filtresi + pop ağırlığı aktif: Sonuçlar links.csv kataloğuyla sınırlandırılacak.")
    if options.get("manual_profile_backend"):
        st.info("Kullanıcı profil vektörü aktif: Seçilen filmler tek profile dönüştürülerek cosine benzerliği hesaplanacak.")
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
            response = make_recommendations(
                titles,
                top_n=top_n,
                method=method,
                restrict_to_movielens=options.get("manual_movielens_filter", False),
                movielens_links_path=Path(st.session_state.get("links_path", str(DEFAULT_LINKS_PATH))),
                use_profile_backend=options.get("manual_profile_backend", False),
            )
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


def render_evaluation_tab(default_method: str, default_top_n: int, apply_movielens_filter: bool) -> None:
    st.subheader("Değerlendirme Senaryosu")
    st.caption("i) HitRate@N metriği ile gizlenen filmlerin öneri listesinde yer alıp almadığını ölçer.")
    if apply_movielens_filter:
        st.info("MovieLens filtresi aktif: öneri listesinde sadece links.csv kataloğundaki filmler değerlendirilecek.")
    with st.expander("Bu sekme nasıl çalışıyor?", expanded=False):
        st.markdown(EVALUATION_HELP_MD)

    default_ratings = st.session_state.get("ratings_path", str(DEFAULT_RATINGS_PATH))
    default_links = st.session_state.get("links_path", str(DEFAULT_LINKS_PATH))

    with st.form("evaluation-form"):
        ratings_path = st.text_input(
            "ratings.csv yolu",
            value=default_ratings,
            help="Kullanıcı-film puanlamalarını içeren CSV. MovieLens örneği data/ratings.csv."
        )
        links_path = st.text_input(
            "links.csv yolu",
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
        col_minliked, col_nhidden = st.columns(2)
        with col_minliked:
            min_liked = st.number_input(
                "Min. beğenilen film",
                min_value=3,
                max_value=20,
                value=5,
                help="Bir kullanıcının değerlendirilmeye girebilmesi için gereken minimum beğeni adedi."
            )
        with col_nhidden:
            n_hidden = st.number_input(
                "Gizlenecek film sayısı",
                min_value=1,
                max_value=5,
                value=2,
                help="Leave-K-Out: Her kullanıcıdan kaç film gizlenecek. 1=klasik, 2+=çoklu gizleme (daha robust)."
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
                restrict_to_movielens=apply_movielens_filter,
                n_hidden=int(n_hidden),
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
                "n_hidden": int(n_hidden),
            },
            "outputs": {
                "hit_rate": response.hit_rate,
                "hits": response.hits,
                "total_hidden": response.total_hidden,
                "tested": response.tested,
                "avg_recall": response.avg_recall,
                "avg_precision": response.avg_precision,
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

    hit_rate_film = response.hit_rate if response.hit_rate is not None else 0.0
    hit_rate_user = response.hit_rate_user if response.hit_rate_user is not None else 0.0
    users_with_hit = response.users_with_hit if response.users_with_hit is not None else 0
    hits = response.hits if response.hits is not None else 0
    tested = response.tested if response.tested is not None else 0
    n_hidden = response.n_hidden if response.n_hidden is not None else 1
    total_hidden = response.total_hidden if response.total_hidden is not None else hits
    avg_recall = response.avg_recall if response.avg_recall is not None else 0.0
    avg_precision = response.avg_precision if response.avg_precision is not None else 0.0

    # Leave-K-Out modunda farklı metrikler göster
    st.markdown(f"### 🎯 Leave-{n_hidden}-Out Değerlendirmesi")
    
    # İki HitRate metriğini yan yana göster
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            f"📊 Kullanıcı Bazlı HitRate@{top_n}", 
            f"{hit_rate_user:.1%}",
            help=f"En az 1 film bulan kullanıcı oranı: {users_with_hit}/{tested}"
        )
    with col2:
        st.metric(
            f"🎬 Film Bazlı HitRate", 
            f"{hit_rate_film:.1%}",
            help=f"Bulunan film oranı: {hits}/{total_hidden}"
        )
    
    # Ek metrikler
    col3, col4, col5, col6 = st.columns(4)
    col3.metric(f"Avg Recall@{top_n}", f"{avg_recall:.3f}", help="Kullanıcı başına ortalama recall")
    col4.metric("Hit Kullanıcı", f"{users_with_hit}/{tested}")
    col5.metric("Bulunan Film", f"{hits}/{total_hidden}")
    col6.metric("Test Edilen", tested)

    st.progress(hit_rate if hit_rate <= 1 else 1.0)

    samples = response.samples or []
    if samples:
        payload = st.session_state.get("last_eval_payload")
        seed = None
        if payload and "inputs" in payload:
            seed = payload["inputs"].get("seed")
        
        st.markdown("**Örnek Kullanıcılar**")
        
        if n_hidden > 1:
            # Leave-K-Out için detaylı tablo
            display_rows = []
            for sample in samples[:10]:
                user_id = sample.get("userId")
                user_hits = sample.get("hits", 0)
                recall = sample.get("recall", 0)
                hidden_movies = sample.get("hidden_movies", [])
                
                row = {
                    "userId": user_id,
                    "hits": f"{user_hits}/{n_hidden}",
                    "recall": f"{recall:.2f}",
                    "hidden_films": ", ".join([
                        f"{'✅' if hm['hit'] else '❌'}{hm['title'][:25]}" 
                        for hm in hidden_movies
                    ])
                }
                display_rows.append(row)
            
            if display_rows:
                df = pd.DataFrame(display_rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Detaylı görünüm için expander
                with st.expander("Detaylı film bilgileri"):
                    for sample in samples[:5]:
                        user_id = sample.get("userId")
                        hidden_movies = sample.get("hidden_movies", [])
                        st.markdown(f"**Kullanıcı {user_id}:**")
                        for hm in hidden_movies:
                            hit_icon = "✅" if hm["hit"] else "❌"
                            rank = hm.get("rank") or "-"
                            st.markdown(f"  {hit_icon} {hm['title']} (rank: {rank}, rating: {hm['rating']})")
        else:
            # Klasik leave-one-out için eski format
            rng = random.Random(seed)
            
            # Eski format samples için dönüşüm
            display_samples = []
            for s in samples:
                if "hidden_movies" in s and s["hidden_movies"]:
                    hm = s["hidden_movies"][0]
                    display_samples.append({
                        "userId": s["userId"],
                        "hidden_title": hm.get("title", "Unknown"),
                        "hit": "✅" if hm.get("hit") else "❌",
                        "rank": hm.get("rank") or "-",
                        "rating": hm.get("rating", "-"),
                    })
                elif "hidden_title" in s:
                    display_samples.append({
                        "userId": s["userId"],
                        "hidden_title": s.get("hidden_title", "Unknown"),
                        "hit": "✅" if s.get("hit") else "❌",
                        "rank": s.get("rank") or "-",
                        "rating": s.get("hidden_rating", "-"),
                    })
            
            if display_samples:
                df = pd.DataFrame(display_samples)
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


def render_comparison_tab(default_method: str, default_top_n: int) -> None:
    """Farklı benzerlik eşikleri ile karşılaştırmalı değerlendirme sekmesi."""
    st.subheader("📊 Benzerlik Eşiği Karşılaştırması")
    st.caption("Farklı benzerlik eşiklerinin HitRate'e etkisini karşılaştırın.")
    
    with st.expander("Bu sekme nasıl çalışıyor?", expanded=False):
        st.markdown("""
        **Amaç**: Akıllı gizleme (smart hide) özelliğinde kullanılan minimum benzerlik eşiğinin 
        değerlendirme sonuçlarına etkisini analiz etmek.
        
        **Nasıl Çalışır**:
        1. Belirtilen eşik değerleri için ayrı ayrı değerlendirme yapılır
        2. Her eşik için HitRate, test edilen kullanıcı sayısı ve skip edilen kullanıcı sayısı hesaplanır
        3. Sonuçlar tablo ve grafik olarak gösterilir
        
        **Yorumlama**:
        - Düşük eşik → Daha fazla kullanıcı test edilir, ancak benzerlik düşük olduğu için HitRate düşük olabilir
        - Yüksek eşik → Daha az kullanıcı test edilir (çoğu skip), ancak test edilenler için HitRate yüksek olur
        - Optimal eşik, yeterli kullanıcı sayısı ve kabul edilebilir HitRate'i dengeler
        """)
    
    default_ratings = st.session_state.get("ratings_path", str(DEFAULT_RATINGS_PATH))
    default_links = st.session_state.get("links_path", str(DEFAULT_LINKS_PATH))
    
    with st.form("comparison-form"):
        st.markdown("### Veri Dosyaları")
        col1, col2 = st.columns(2)
        with col1:
            ratings_path = st.text_input("ratings.csv yolu", value=default_ratings)
        with col2:
            links_path = st.text_input("links.csv yolu", value=default_links)
        
        st.markdown("### Değerlendirme Parametreleri")
        col1, col2, col3 = st.columns(3)
        with col1:
            n_users = st.slider("Test edilecek kullanıcı", 20, 200, 100, step=10)
        with col2:
            comp_top_n = st.slider("Top-N", 5, 50, default_top_n)
        with col3:
            n_hidden = st.number_input("Gizlenecek film", min_value=1, max_value=3, value=1)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            mode = st.selectbox("Mod", options=["standard", "profile"], index=0)
        with col2:
            method = st.selectbox("Yöntem", options=["score_avg", "vector_avg"], index=0)
        with col3:
            seed = st.number_input("Seed", min_value=0, max_value=9999, value=42)
        
        st.markdown("### Benzerlik Eşikleri")
        st.caption("Karşılaştırmak istediğiniz eşik değerlerini virgülle ayırarak girin (örn: 0.05, 0.10, 0.15, 0.20, 0.30)")
        
        thresholds_input = st.text_input(
            "Eşik değerleri",
            value="0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40",
            help="Virgülle ayrılmış ondalık sayılar"
        )
        
        run_comparison = st.form_submit_button("🚀 Karşılaştırmayı Başlat", use_container_width=True)
    
    if run_comparison:
        # Eşikleri parse et
        try:
            thresholds = [float(t.strip()) for t in thresholds_input.split(",") if t.strip()]
            thresholds = sorted(set(thresholds))  # Sırala ve tekrarları kaldır
        except ValueError:
            st.error("Geçersiz eşik değerleri. Lütfen virgülle ayrılmış sayılar girin.")
            return
        
        if len(thresholds) < 2:
            st.error("En az 2 eşik değeri girilmelidir.")
            return
        
        # Dosya kontrolü
        ratings = Path(ratings_path).expanduser()
        links = Path(links_path).expanduser()
        
        if not ratings.exists():
            st.error(f"Ratings dosyası bulunamadı: {ratings}")
            return
        if not links.exists():
            st.error(f"Links dosyası bulunamadı: {links}")
            return
        
        # Progress bar ile karşılaştırma yap
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results: list[ComparisonResult] = []
        
        for i, threshold in enumerate(thresholds):
            status_text.text(f"Eşik {threshold:.2f} değerlendiriliyor... ({i+1}/{len(thresholds)})")
            progress_bar.progress((i + 1) / len(thresholds))
            
            response = services.evaluate_model(
                ratings_path=ratings,
                links_path=links,
                n_users=n_users,
                top_n=comp_top_n,
                mode=mode,
                rating_threshold=4.0,
                min_liked=5,
                method=method,
                seed=seed,
                n_hidden=n_hidden,
                smart_hide=True,
                min_hide_similarity=threshold,
            )
            
            results.append(ComparisonResult(
                threshold=threshold,
                hit_rate=response.hit_rate or 0.0,
                hits=response.hits or 0,
                tested=response.tested or 0,
                skipped=response.skipped_no_similar or 0,
                avg_hide_similarity=response.avg_hide_similarity or 0.0,
                total_hidden=response.total_hidden or 0,
                avg_recall=response.avg_recall or 0.0,
                error=response.error,
                hit_rate_user=response.hit_rate_user or 0.0,
                users_with_hit=response.users_with_hit or 0,
            ))
        
        progress_bar.empty()
        status_text.empty()
        
        # Sonuçları session'a kaydet
        st.session_state["comparison_results"] = results
        st.session_state["comparison_params"] = {
            "n_users": n_users,
            "top_n": comp_top_n,
            "n_hidden": n_hidden,
            "mode": mode,
            "method": method,
            "seed": seed,
            "rating_threshold": 4.0,
            "min_liked": 5,
            "ratings_path": str(ratings),
            "links_path": str(links),
        }
        
        st.success(f"✅ {len(thresholds)} eşik değeri karşılaştırıldı!")
    
    # Sonuçları göster
    results = st.session_state.get("comparison_results")
    params = st.session_state.get("comparison_params", {})
    
    if results:
        render_comparison_results(results, params)


def render_comparison_results(results: list[ComparisonResult], params: dict) -> None:
    """Karşılaştırma sonuçlarını görselleştir."""
    
    # DataFrame oluştur
    df = pd.DataFrame([
        {
            "Eşik": f"{r.threshold:.2f}",
            "threshold": r.threshold,
            "HitRate (Film)": r.hit_rate,
            "HitRate (Kullanıcı)": r.hit_rate_user or 0.0,
            "Hit Kullanıcı": r.users_with_hit or 0,
            "Hits": r.hits,
            "Test Edilen": r.tested,
            "Skip": r.skipped,
            "Toplam Gizlenen": r.total_hidden,
            "Ort. Benzerlik": r.avg_hide_similarity,
            "Avg Recall": r.avg_recall,
        }
        for r in results if not r.error
    ])
    
    if df.empty:
        st.error("Tüm değerlendirmeler hata ile sonuçlandı.")
        return
    
    # Özet metrikler
    st.markdown("### 📈 Özet")
    
    best_hitrate_user_idx = df["HitRate (Kullanıcı)"].idxmax()
    best_hitrate_film_idx = df["HitRate (Film)"].idxmax()
    best_tested_idx = df["Test Edilen"].idxmax()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "🏆 En Yüksek Kullanıcı HitRate",
            f"{df.loc[best_hitrate_user_idx, 'HitRate (Kullanıcı)']:.1%}",
            f"Eşik: {df.loc[best_hitrate_user_idx, 'Eşik']}"
        )
    with col2:
        st.metric(
            "🎬 En Yüksek Film HitRate",
            f"{df.loc[best_hitrate_film_idx, 'HitRate (Film)']:.1%}",
            f"Eşik: {df.loc[best_hitrate_film_idx, 'Eşik']}"
        )
    with col3:
        st.metric(
            "⚙️ Ayarlar",
            f"Top-{params.get('top_n', 'N/A')}",
            f"{params.get('n_users', 'N/A')} kullanıcı"
        )
    
    # Grafikler
    st.markdown("### 📊 Grafikler")
    
    tab_chart1, tab_chart2, tab_chart3 = st.tabs(["HitRate Karşılaştırması", "Test/Skip Dağılımı", "Detaylı Analiz"])
    
    with tab_chart1:
        # İki HitRate karşılaştırması (Kullanıcı vs Film bazlı)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["Eşik"],
            y=df["HitRate (Kullanıcı)"],
            name="Kullanıcı Bazlı (en az 1 hit)",
            marker_color="blue"
        ))
        fig.add_trace(go.Bar(
            x=df["Eşik"],
            y=df["HitRate (Film)"],
            name="Film Bazlı (hits/total)",
            marker_color="lightblue"
        ))
        fig.update_layout(
            title="İki HitRate Tanımı Karşılaştırması",
            xaxis_title="Benzerlik Eşiği",
            yaxis_title="HitRate",
            yaxis_tickformat=".1%",
            barmode="group",
            height=400,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Line chart - Tüm metrikler
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["threshold"],
            y=df["HitRate (Kullanıcı)"],
            mode="lines+markers",
            name="HitRate (Kullanıcı)",
            line=dict(color="blue", width=3),
            marker=dict(size=10)
        ))
        fig2.add_trace(go.Scatter(
            x=df["threshold"],
            y=df["HitRate (Film)"],
            mode="lines+markers",
            name="HitRate (Film)",
            line=dict(color="lightblue", width=3),
            marker=dict(size=10)
        ))
        fig2.add_trace(go.Scatter(
            x=df["threshold"],
            y=df["Avg Recall"],
            mode="lines+markers",
            name="Avg Recall",
            line=dict(color="green", width=3),
            marker=dict(size=10)
        ))
        fig2.update_layout(
            title="HitRate ve Recall Trendi",
            xaxis_title="Benzerlik Eşiği",
            yaxis_title="Oran",
            yaxis_tickformat=".1%",
            height=400,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab_chart2:
        # Stacked bar chart - Test edilen vs Skip
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["Eşik"],
            y=df["Test Edilen"],
            name="Test Edilen",
            marker_color="green"
        ))
        fig.add_trace(go.Bar(
            x=df["Eşik"],
            y=df["Skip"],
            name="Skip (Benzer Film Yok)",
            marker_color="red"
        ))
        fig.update_layout(
            title="Test Edilen vs Skip Edilen Kullanıcılar",
            xaxis_title="Benzerlik Eşiği",
            yaxis_title="Kullanıcı Sayısı",
            barmode="stack",
            height=400,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Pie chart - Örnek dağılım (en düşük ve en yüksek eşik)
        col1, col2 = st.columns(2)
        
        with col1:
            low_df = df.iloc[0]
            fig_pie1 = px.pie(
                names=["Test Edilen", "Skip"],
                values=[low_df["Test Edilen"], low_df["Skip"]],
                title=f"Eşik: {low_df['Eşik']}",
                color_discrete_sequence=["green", "red"]
            )
            fig_pie1.update_layout(height=300)
            st.plotly_chart(fig_pie1, use_container_width=True)
        
        with col2:
            high_df = df.iloc[-1]
            fig_pie2 = px.pie(
                names=["Test Edilen", "Skip"],
                values=[high_df["Test Edilen"], high_df["Skip"]],
                title=f"Eşik: {high_df['Eşik']}",
                color_discrete_sequence=["green", "red"]
            )
            fig_pie2.update_layout(height=300)
            st.plotly_chart(fig_pie2, use_container_width=True)
    
    with tab_chart3:
        # Scatter plot - HitRate vs Ort. Benzerlik
        fig = px.scatter(
            df,
            x="Ort. Benzerlik",
            y="HitRate (Kullanıcı)",
            size="Test Edilen",
            color="threshold",
            hover_data=["Eşik", "Hits", "Skip", "Hit Kullanıcı"],
            title="Ortalama Gizlenen Film Benzerliği vs Kullanıcı HitRate",
            labels={"Ort. Benzerlik": "Ort. Gizlenen Film Benzerliği"},
            color_continuous_scale="Turbo",
        )
        fig.update_layout(height=400, yaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True)
        
        # Heatmap style table
        st.markdown("#### Eşik-Metrik İlişkisi")
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=[df["HitRate (Kullanıcı)"].values, df["HitRate (Film)"].values, df["Avg Recall"].values, df["Ort. Benzerlik"].values],
            x=df["Eşik"].values,
            y=["HitRate (Kullanıcı)", "HitRate (Film)", "Avg Recall", "Ort. Benzerlik"],
            colorscale="Viridis",
            text=[[f"{v:.1%}" for v in df["HitRate (Kullanıcı)"].values],
                  [f"{v:.1%}" for v in df["HitRate (Film)"].values],
                  [f"{v:.1%}" for v in df["Avg Recall"].values],
                  [f"{v:.3f}" for v in df["Ort. Benzerlik"].values]],
            texttemplate="%{text}",
            textfont={"size": 12},
            hoverongaps=False,
        ))
        fig_heatmap.update_layout(
            title="Metrik Heatmap",
            height=280,
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Tablo
    st.markdown("### 📋 Detaylı Sonuçlar")
    display_df = df.copy()
    display_df["HitRate (Kullanıcı)"] = display_df["HitRate (Kullanıcı)"].apply(lambda x: f"{x:.1%}")
    display_df["HitRate (Film)"] = display_df["HitRate (Film)"].apply(lambda x: f"{x:.1%}")
    display_df["Avg Recall"] = display_df["Avg Recall"].apply(lambda x: f"{x:.1%}")
    display_df["Ort. Benzerlik"] = display_df["Ort. Benzerlik"].apply(lambda x: f"{x:.3f}")
    display_df = display_df.drop(columns=["threshold"])
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # CSV indirme - tüm parametrelerle birlikte
    export_df = df.copy()
    
    # Parametreleri her satıra ekle
    export_df["n_users"] = params.get("n_users", "")
    export_df["top_n"] = params.get("top_n", "")
    export_df["n_hidden"] = params.get("n_hidden", "")
    export_df["mode"] = params.get("mode", "")
    export_df["method"] = params.get("method", "")
    export_df["seed"] = params.get("seed", "")
    export_df["rating_threshold"] = params.get("rating_threshold", 4.0)
    export_df["min_liked"] = params.get("min_liked", 5)
    export_df["ratings_path"] = params.get("ratings_path", "")
    export_df["links_path"] = params.get("links_path", "")
    
    # Kolonları yeniden sırala - önce sonuçlar, sonra parametreler
    param_cols = ["n_users", "top_n", "n_hidden", "mode", "method", "rating_threshold", "min_liked", "seed", "ratings_path", "links_path"]
    result_cols = [c for c in export_df.columns if c not in param_cols]
    export_df = export_df[result_cols + param_cols]
    
    csv = export_df.to_csv(index=False)
    st.download_button(
        "📥 Sonuçları CSV olarak indir (tüm parametrelerle)",
        data=csv.encode("utf-8"),
        file_name="comparison_results.csv",
        mime="text/csv",
        use_container_width=True,
    )
    
    # Yorum ve öneri
    st.markdown("### 💡 Analiz")
    
    # En iyi dengeyi bul
    df_valid = df[df["Test Edilen"] >= 10]  # En az 10 kullanıcı test edilmiş olanlar
    if not df_valid.empty:
        # Basit bir skor hesapla: HitRate * log(Test Edilen + 1)
        import numpy as np
        df_valid = df_valid.copy()
        df_valid["score"] = df_valid["HitRate (Kullanıcı)"] * np.log1p(df_valid["Test Edilen"])
        best_idx = df_valid["score"].idxmax()
        best_threshold = df_valid.loc[best_idx, "Eşik"]
        best_hr = df_valid.loc[best_idx, "HitRate (Kullanıcı)"]
        best_tested = df_valid.loc[best_idx, "Test Edilen"]
        
        st.success(f"""
        **Önerilen Eşik: {best_threshold}**
        
        Bu eşik, Kullanıcı HitRate ({best_hr:.1%}) ve test edilen kullanıcı sayısı ({best_tested}) 
        arasında iyi bir denge sağlıyor.
        """)
    
    st.info("""
    **Yorumlama Kılavuzu:**
    - 🟢 **Düşük eşik (0.05-0.10)**: Geniş kullanıcı havuzu, düşük HitRate
    - 🟡 **Orta eşik (0.15-0.25)**: Dengeli sonuçlar
    - 🔴 **Yüksek eşik (0.30+)**: Yüksek HitRate, dar kullanıcı havuzu
    
    Content-based sistemler için **%15-40 HitRate** normaldir.
    """)


def render_selection_logic_banner() -> None:
    payload = st.session_state.get("last_eval_payload")
    if payload and "inputs" in payload:
        inputs = payload["inputs"]
    else:
        inputs = DEFAULT_EVAL_INPUTS
    
    n_hidden = inputs.get('n_hidden', 1)
    if n_hidden > 1:
        hidden_text = f"**{n_hidden} film gizlenir (Leave-{n_hidden}-Out)**"
    else:
        hidden_text = "bir film gizlenir"
    
    st.info(
        "Kullanıcı seçme akışı: ratings.csv içindeki kullanıcılardan "
        f"`rating >= {inputs['rating_threshold']}` koşulunu sağlayan ve en az "
        f"{inputs['min_liked']} favori filme sahip olanlar filtrelenir. "
        f"Rastgele {inputs['n_users']} kullanıcı seçilip her biri için {hidden_text}; "
        f"gizlenen filmler öneri listesinde Top-{inputs['top_n']} içinde yer alırsa hit sayılır "
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
    if str(st.session_state["ratings_path"]).endswith("ratings_small.csv"):
        st.session_state["ratings_path"] = str(DEFAULT_RATINGS_PATH)
    if str(st.session_state["links_path"]).endswith("links_small.csv"):
        st.session_state["links_path"] = str(DEFAULT_LINKS_PATH)

    summary, top_n, method, feature_flags = render_sidebar()
    render_selection_logic_banner()
    render_global_stats()

    tab_manual, tab_inspect, tab_eval, tab_compare = st.tabs(
        ["Manuel Öneri", "Model İncelemesi", "Değerlendirme Senaryosu", "📊 Eşik Karşılaştırması"]
    )

    with tab_manual:
        render_manual_tab(top_n, method, feature_flags)
    with tab_inspect:
        render_inspection_tab()
    with tab_eval:
        render_evaluation_tab(method, top_n, feature_flags.get("eval_movielens_filter", False))
    with tab_compare:
        render_comparison_tab(method, top_n)

    if not summary.ready:
        st.warning("Artefaktlar hazır olmadan sonuçlar eksik olabilir.")


if __name__ == "__main__":
    main()

