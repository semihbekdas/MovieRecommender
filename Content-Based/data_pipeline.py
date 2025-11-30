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
        default=12000,
        help="TF-IDF için maksimum feature sayısı",
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


def prepare_metadata(
    df: pd.DataFrame,
    *,
    min_content_chars: int,
    to_lower: bool,
) -> pd.DataFrame:
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
    work["genres_str"] = work["genres_list"].apply(lambda xs: " ".join(xs))

    if to_lower:
        work["overview"] = work["overview"].str.lower()
        work["genres_str"] = work["genres_str"].str.lower()

    work["content"] = (work["genres_str"] + " " + work["overview"]).str.strip()
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
    print("📂 Metadata yükleniyor...")
    raw_df = load_raw_metadata(args.source)
    print(f"   → {len(raw_df):,} satır okundu")

    print("🧹 Veri temizleniyor...")
    prepared = prepare_metadata(
        raw_df,
        min_content_chars=args.min_content_chars,
        to_lower=args.to_lower,
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

