from __future__ import annotations

import argparse
import ast
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle


BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

DEFAULT_SOURCE = BASE_DIR / "movies_metadata.csv"
DATA_DIR = BASE_DIR.parent / "data"
KEYWORDS_PATH = DATA_DIR / "keywords.csv"
CREDITS_PATH = DATA_DIR / "credits.csv"

DEFAULT_METADATA_PATH = MODELS_DIR / "metadata.parquet"
VECTORIZER_PATH = MODELS_DIR / "tfidf_vectorizer.pkl"
MATRIX_PATH = MODELS_DIR / "tfidf_matrix.npz"
META_JSON_PATH = MODELS_DIR / "content_meta.json"
ARTIFACT_PATHS = (
    VECTORIZER_PATH,
    MATRIX_PATH,
    DEFAULT_METADATA_PATH,
    META_JSON_PATH,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Content-Based TF-IDF artefakt pipeline"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="movies_metadata.csv dosya yolu (varsayılan: Content-Based klasörü)",
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=15000,
        help="TF-IDF için maksimum feature sayısı (varsayılan: 15000)",
    )
    parser.add_argument(
        "--ngram-min",
        type=int,
        default=1,
        help="TF-IDF ngram alt sınırı",
    )
    parser.add_argument(
        "--ngram-max",
        type=int,
        default=2,
        help="TF-IDF ngram üst sınırı",
    )
    parser.add_argument(
        "--min-content-chars",
        type=int,
        default=20,
        help="Content metni için minimum karakter sayısı",
    )
    parser.add_argument(
        "--to-lower",
        action="store_true",
        help="Content metnini lower() yap",
    )
    parser.add_argument(
        "--no-keywords",
        action="store_true",
        help="Keywords.csv'yi kullanma",
    )
    parser.add_argument(
        "--no-credits",
        action="store_true",
        help="Credits.csv'yi kullanma (cast/crew)",
    )
    parser.add_argument(
        "--genre-weight",
        type=int,
        default=3,
        help="Genre'ların tekrar sayısı (ağırlık). Varsayılan: 3",
    )
    parser.add_argument(
        "--rebuild",
        "--overwrite",
        dest="rebuild",
        action="store_true",
        help="Mevcut artefaktları yeniden oluştur",
    )
    return parser.parse_args()


def ensure_paths() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def artifacts_exist() -> bool:
    return any(path.exists() for path in ARTIFACT_PATHS)


def load_raw_metadata(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Metadata dosyası bulunamadı: {csv_path}")
    return pd.read_csv(csv_path, low_memory=False)


def parse_genres(value: str) -> list[str]:
    if not isinstance(value, str):
        return []
    try:
        items = ast.literal_eval(value)
        if isinstance(items, list):
            genres = [
                item.get("name", "").strip()
                for item in items
                if isinstance(item, dict) and item.get("name")
            ]
            return [g for g in genres if g]
    except (ValueError, SyntaxError, TypeError):
        return []
    return []


def parse_keywords(value: str) -> list[str]:
    """Keywords alanını parse et."""
    if not isinstance(value, str):
        return []
    try:
        items = ast.literal_eval(value)
        if isinstance(items, list):
            keywords = [
                item.get("name", "").strip().replace(" ", "_")
                for item in items
                if isinstance(item, dict) and item.get("name")
            ]
            return [k for k in keywords if k][:10]  # Max 10 keyword
    except (ValueError, SyntaxError, TypeError):
        return []
    return []


def parse_cast(value: str, top_n: int = 5) -> list[str]:
    """Cast alanından ilk N oyuncuyu al."""
    if not isinstance(value, str):
        return []
    try:
        items = ast.literal_eval(value)
        if isinstance(items, list):
            cast = [
                item.get("name", "").strip().replace(" ", "_")
                for item in items  # ← TÜM listeyi işle
                if isinstance(item, dict) and item.get("name")
            ]
            return [c for c in cast if c][:top_n]  # ← ÖNCE filtrele, SONRA slice
    except (ValueError, SyntaxError, TypeError):
        return []
    return []


def parse_crew(value: str) -> list[str]:
    """Crew'dan yönetmeni al."""
    if not isinstance(value, str):
        return []
    try:
        items = ast.literal_eval(value)
        if isinstance(items, list):
            directors = [
                item.get("name", "").strip().replace(" ", "_")
                for item in items
                if isinstance(item, dict) and item.get("job") == "Director"
            ]
            return directors[:2]  # Max 2 yönetmen
    except (ValueError, SyntaxError, TypeError):
        return []
    return []


def load_keywords() -> pd.DataFrame | None:
    """Keywords dosyasını yükle."""
    if not KEYWORDS_PATH.exists():
        print(f"   ⚠️ Keywords dosyası bulunamadı: {KEYWORDS_PATH}")
        return None
    df = pd.read_csv(KEYWORDS_PATH)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["id"])
    return df


def load_credits() -> pd.DataFrame | None:
    """Credits dosyasını yükle."""
    if not CREDITS_PATH.exists():
        print(f"   ⚠️ Credits dosyası bulunamadı: {CREDITS_PATH}")
        return None
    df = pd.read_csv(CREDITS_PATH)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["id"])
    return df


def prepare_metadata(
    df: pd.DataFrame,
    *,
    min_content_chars: int,
    to_lower: bool,
    use_keywords: bool = True,
    use_credits: bool = True,
    genre_weight: int = 3,
) -> pd.DataFrame:
    """
    Metadata'yı hazırla ve zenginleştirilmiş content string oluştur.
    
    Args:
        genre_weight: Genre'ların kaç kez tekrarlanacağı (ağırlıklandırma için)
        use_keywords: Keywords.csv'den anahtar kelimeler ekle
        use_credits: Credits.csv'den oyuncu/yönetmen ekle
    """
    work = df.copy()
    work["id"] = pd.to_numeric(work.get("id"), errors="coerce").astype("Int64")
    work = work.dropna(subset=["id"])

    keep_cols = [
        "id",
        "title",
        "genres",
        "overview",
        "vote_average",
        "vote_count",
    ]
    for col in keep_cols:
        if col not in work.columns:
            work[col] = pd.NA
    work = work[keep_cols]

    work["title"] = work["title"].fillna("Untitled").astype(str)
    work["overview"] = work["overview"].fillna("").astype(str)
    work["genres_list"] = work["genres"].apply(parse_genres)
    
    # Genre'ları ağırlıklandır (tekrarla)
    work["genres_str"] = work["genres_list"].apply(
        lambda xs: " ".join(xs * genre_weight) if xs else ""
    )

    # Keywords ekle
    work["keywords_str"] = ""
    if use_keywords:
        keywords_df = load_keywords()
        if keywords_df is not None:
            keywords_df["keywords_list"] = keywords_df["keywords"].apply(parse_keywords)
            keywords_df["keywords_str"] = keywords_df["keywords_list"].apply(
                lambda xs: " ".join(xs * 2) if xs else ""  # Keywords 2x tekrar
            )
            keywords_map = keywords_df.set_index("id")["keywords_str"].to_dict()
            work["keywords_str"] = work["id"].map(keywords_map).fillna("")
            print(f"   ✅ Keywords eklendi: {len(keywords_map):,} film")

    # Cast/Crew ekle
    work["cast_str"] = ""
    work["director_str"] = ""
    if use_credits:
        credits_df = load_credits()
        if credits_df is not None:
            credits_df["cast_list"] = credits_df["cast"].apply(parse_cast)
            credits_df["cast_str"] = credits_df["cast_list"].apply(
                lambda xs: " ".join(xs * 2) if xs else ""  # Cast 2x tekrar
            )
            credits_df["director_list"] = credits_df["crew"].apply(parse_crew)
            credits_df["director_str"] = credits_df["director_list"].apply(
                lambda xs: " ".join(xs * 3) if xs else ""  # Yönetmen 3x tekrar
            )
            cast_map = credits_df.set_index("id")["cast_str"].to_dict()
            director_map = credits_df.set_index("id")["director_str"].to_dict()
            work["cast_str"] = work["id"].map(cast_map).fillna("")
            work["director_str"] = work["id"].map(director_map).fillna("")
            print(f"   ✅ Cast/Crew eklendi: {len(cast_map):,} film")

    if to_lower:
        work["overview"] = work["overview"].str.lower()
        work["genres_str"] = work["genres_str"].str.lower()
        work["keywords_str"] = work["keywords_str"].str.lower()
        work["cast_str"] = work["cast_str"].str.lower()
        work["director_str"] = work["director_str"].str.lower()

    # Zenginleştirilmiş content string
    # Format: GENRES (3x) + DIRECTOR (3x) + CAST (2x) + KEYWORDS (2x) + OVERVIEW
    work["content"] = (
        work["genres_str"] + " " +
        work["director_str"] + " " +
        work["cast_str"] + " " +
        work["keywords_str"] + " " +
        work["overview"]
    ).str.strip()
    
    work = work[work["content"].str.len() >= min_content_chars]
    work = work.drop_duplicates(subset=["id"]).reset_index(drop=True)

    work["vote_average"] = pd.to_numeric(work["vote_average"], errors="coerce")
    work["vote_count"] = pd.to_numeric(work["vote_count"], errors="coerce").fillna(0).astype(int)

    return work


def build_tfidf(
    texts: Iterable[str],
    *,
    max_features: int,
    ngram_range: Tuple[int, int],
) -> tuple[TfidfVectorizer, sparse.csr_matrix]:
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=max_features,
        ngram_range=ngram_range,
    )
    matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix


def save_sparse_matrix(path: Path, matrix: sparse.csr_matrix) -> None:
    sparse.save_npz(path, matrix.astype("float32"))


def save_pickle(obj, path: Path) -> None:
    with path.open("wb") as f:
        pickle.dump(obj, f)


def save_metadata(df: pd.DataFrame, path: Path) -> Path:
    try:
        df.to_parquet(path, index=False)
        return path
    except Exception:
        fallback = path.with_suffix(".pkl")
        df.to_pickle(fallback)
        return fallback


def save_meta_json(meta: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def run_pipeline(args: argparse.Namespace) -> None:
    ensure_paths()
    if artifacts_exist() and not args.rebuild:
        existing = [path.name for path in ARTIFACT_PATHS if path.exists()]
        raise SystemExit(
            "Artefaktlar zaten mevcut: "
            f"{', '.join(existing)}. Yeniden üretmek için --rebuild kullanın."
        )
    
    print("=" * 60)
    print("🎬 CONTENT-BASED MODEL OLUŞTURMA")
    print("=" * 60)
    
    print("\n📂 Metadata yükleniyor...")
    raw_df = load_raw_metadata(args.source)
    print(f"   → {len(raw_df):,} satır okundu")

    print("\n🧹 Veri zenginleştiriliyor...")
    use_keywords = not args.no_keywords
    use_credits = not args.no_credits
    
    print(f"   • Keywords kullanımı: {'✅ Evet' if use_keywords else '❌ Hayır'}")
    print(f"   • Cast/Crew kullanımı: {'✅ Evet' if use_credits else '❌ Hayır'}")
    print(f"   • Genre ağırlığı: {args.genre_weight}x")
    
    prepared = prepare_metadata(
        raw_df,
        min_content_chars=args.min_content_chars,
        to_lower=args.to_lower,
        use_keywords=use_keywords,
        use_credits=use_credits,
        genre_weight=args.genre_weight,
    )
    if prepared.empty:
        raise RuntimeError("Temizlenen metadata boş kaldı!")
    print(f"   → {len(prepared):,} film kaldı")

    print("🧠 TF-IDF vektörleri hesaplanıyor...")
    vectorizer, matrix = build_tfidf(
        prepared["content"].tolist(),
        max_features=args.max_features,
        ngram_range=(args.ngram_min, args.ngram_max),
    )
    print(f"   → Matris boyutu: {matrix.shape[0]:,} film × {matrix.shape[1]:,} feature")

    prepared = prepared.assign(matrix_index=range(len(prepared)))
    metadata_to_save = prepared[
        [
            "id",
            "title",
            "genres_str",
            "overview",
            "vote_average",
            "vote_count",
            "matrix_index",
        ]
    ].rename(
        columns={
            "id": "tmdb_id",
            "genres_str": "genres",
        }
    )

    print("💾 Artefaktlar kaydediliyor...")
    save_pickle(vectorizer, VECTORIZER_PATH)
    save_sparse_matrix(MATRIX_PATH, matrix)
    metadata_path = save_metadata(metadata_to_save, DEFAULT_METADATA_PATH)

    meta_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": str(args.source),
        "record_count": int(matrix.shape[0]),
        "feature_count": int(matrix.shape[1]),
        "tfidf_max_features": args.max_features,
        "tfidf_ngram_range": [args.ngram_min, args.ngram_max],
        "min_content_chars": args.min_content_chars,
        "lowercased": bool(args.to_lower),
        "use_keywords": use_keywords,
        "use_credits": use_credits,
        "genre_weight": args.genre_weight,
        "metadata_path": str(metadata_path),
        "vectorizer_path": str(VECTORIZER_PATH),
        "matrix_path": str(MATRIX_PATH),
    }
    save_meta_json(meta_payload, META_JSON_PATH)

    print("✅ Pipeline tamamlandı!")
    print(f"   • Vectorizer: {VECTORIZER_PATH}")
    print(f"   • TF-IDF matrix: {MATRIX_PATH}")
    print(f"   • Metadata: {metadata_path}")
    print(f"   • Meta JSON: {META_JSON_PATH}")


if __name__ == "__main__":
    CLI_ARGS = parse_args()
    run_pipeline(CLI_ARGS)

