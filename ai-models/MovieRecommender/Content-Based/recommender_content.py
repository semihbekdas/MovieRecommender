from __future__ import annotations

import argparse
import pickle
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

VECTORIZER_PATH = MODELS_DIR / "tfidf_vectorizer.pkl"
MATRIX_PATH = MODELS_DIR / "tfidf_matrix.npz"
METADATA_PARQUET = MODELS_DIR / "metadata.parquet"
METADATA_PICKLE = MODELS_DIR / "metadata.parquet.pkl"

DEFAULT_TOP_N = 10


@dataclass(frozen=True)
class ArtifactBundle:
    vectorizer: object
    matrix: sparse.csr_matrix
    metadata: pd.DataFrame
    title_to_id: dict[str, int]
    id_to_index: dict[int, int]


_CACHE: ArtifactBundle | None = None


def _load_pickle(path: Path):
    with path.open("rb") as f:
        return pickle.load(f)


def load_metadata_frame() -> pd.DataFrame:
    if METADATA_PARQUET.exists():
        return pd.read_parquet(METADATA_PARQUET)
    if METADATA_PICKLE.exists():
        return pd.read_pickle(METADATA_PICKLE)
    raise FileNotFoundError("Metadata dosyası bulunamadı (parquet/pkl).")


def load_artifacts(force_reload: bool = False) -> ArtifactBundle:
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE

    if not VECTORIZER_PATH.exists() or not MATRIX_PATH.exists():
        raise FileNotFoundError(
            "TF-IDF artefaktları bulunamadı. Önce data_pipeline.py çalıştırın."
        )

    vectorizer = _load_pickle(VECTORIZER_PATH)
    matrix = sparse.load_npz(MATRIX_PATH)
    metadata = load_metadata_frame()

    metadata = metadata.copy()
    metadata["title"] = metadata["title"].astype(str)
    metadata["normalized_title"] = metadata["title"].str.strip().str.casefold()
    metadata["genres"] = metadata["genres"].fillna("")
    metadata["overview"] = metadata["overview"].fillna("")

    title_to_id = (
        metadata.drop_duplicates(subset="normalized_title")
        .set_index("normalized_title")["tmdb_id"]
        .to_dict()
    )
    id_to_index = metadata.set_index("tmdb_id")["matrix_index"].to_dict()

    _CACHE = ArtifactBundle(
        vectorizer=vectorizer,
        matrix=matrix,
        metadata=metadata,
        title_to_id=title_to_id,
        id_to_index=id_to_index,
    )
    return _CACHE


def normalize_title(title: str) -> str:
    return title.strip().casefold()


def titles_to_ids(titles: Sequence[str], bundle: ArtifactBundle) -> tuple[list[int], list[str]]:
    found: list[int] = []
    missing: list[str] = []
    for title in titles:
        norm = normalize_title(title)
        movie_id = bundle.title_to_id.get(norm)
        if movie_id is None:
            missing.append(title)
        else:
            found.append(int(movie_id))
    return found, missing


def _format_overview(text: str, limit: int = 160) -> str:
    text = text.strip()
    if not text:
        return ""
    return textwrap.shorten(text, width=limit, placeholder="…")


def scores_to_dataframe(
    scores: np.ndarray,
    bundle: ArtifactBundle,
    *,
    exclude_ids: Iterable[int],
    top_n: int,
) -> pd.DataFrame:
    metadata = bundle.metadata
    exclude_set = set(exclude_ids)

    metadata = metadata.assign(similarity=scores)
    metadata = metadata[~metadata["tmdb_id"].isin(exclude_set)]
    metadata = metadata.sort_values("similarity", ascending=False).head(top_n)
    metadata = metadata.copy()
    metadata["overview_snippet"] = metadata["overview"].apply(_format_overview)
    metadata["genres"] = metadata["genres"].replace("", "N/A")
    metadata["vote_average"] = metadata["vote_average"].fillna(0.0)
    metadata["vote_count"] = metadata["vote_count"].fillna(0)
    return metadata[
        [
            "title",
            "tmdb_id",
            "similarity",
            "genres",
            "overview_snippet",
            "vote_average",
            "vote_count",
        ]
    ]


def _compute_similarity_for_indices(
    indices: Sequence[int],
    bundle: ArtifactBundle,
    *,
    method: str = "score_avg",
) -> np.ndarray:
    matrix = bundle.matrix
    if not indices:
        return np.zeros(matrix.shape[0], dtype=float)

    if method == "score_avg":
        sims = []
        for idx in indices:
            vec = cosine_similarity(matrix[idx], matrix).ravel()
            sims.append(vec)
        scores = np.vstack(sims).mean(axis=0)
        return scores

    if method == "vector_avg":
        subset = matrix[indices]
        profile = subset.mean(axis=0)
        scores = cosine_similarity(profile, matrix).ravel()
        return scores

    raise ValueError(f"Bilinmeyen method: {method}")


def recommend_single(movie_id: int, top_n: int = DEFAULT_TOP_N, method: str = "score_avg") -> pd.DataFrame:
    bundle = load_artifacts()
    index = bundle.id_to_index.get(movie_id)
    if index is None:
        raise ValueError(f"TMDB id {movie_id} metadata'da bulunamadı.")
    scores = _compute_similarity_for_indices([index], bundle, method=method)
    return scores_to_dataframe(scores, bundle, exclude_ids=[movie_id], top_n=top_n)


def recommend_multi(
    movie_ids: Sequence[int],
    *,
    top_n: int = DEFAULT_TOP_N,
    method: str = "score_avg",
) -> pd.DataFrame:
    bundle = load_artifacts()
    indices = []
    for movie_id in movie_ids:
        idx = bundle.id_to_index.get(movie_id)
        if idx is not None:
            indices.append(idx)
    if not indices:
        return pd.DataFrame()
    scores = _compute_similarity_for_indices(indices, bundle, method=method)
    return scores_to_dataframe(scores, bundle, exclude_ids=movie_ids, top_n=top_n)


def get_popular_fallback(top_n: int = DEFAULT_TOP_N) -> pd.DataFrame:
    bundle = load_artifacts()
    metadata = bundle.metadata.copy()
    metadata["vote_average"] = metadata["vote_average"].fillna(0.0)
    metadata["vote_count"] = metadata["vote_count"].fillna(0)
    metadata = metadata.sort_values(
        ["vote_count", "vote_average"], ascending=[False, False]
    ).head(top_n)
    metadata["similarity"] = np.nan
    metadata["overview_snippet"] = metadata["overview"].apply(_format_overview)
    return metadata[
        [
            "title",
            "tmdb_id",
            "similarity",
            "genres",
            "overview_snippet",
            "vote_average",
            "vote_count",
        ]
    ]


def cli_recommend(titles: Sequence[str], top_n: int, method: str) -> pd.DataFrame:
    bundle = load_artifacts()
    movie_ids, missing = titles_to_ids(titles, bundle)
    if missing:
        print(f"⚠️ Bulunamayan başlıklar: {', '.join(missing)}")
    if not movie_ids:
        print("Hiç film eşleşmedi, popüler fallback dönüyor.")
        return get_popular_fallback(top_n=top_n)
    if len(movie_ids) == 1:
        result = recommend_single(movie_ids[0], top_n=top_n, method=method)
    else:
        result = recommend_multi(movie_ids, top_n=top_n, method=method)
    if result.empty:
        print("Öneri üretilemedi, popüler fallback dönüyor.")
        return get_popular_fallback(top_n=top_n)
    return result


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Content-Based öneri aracı")
    parser.add_argument(
        "--titles",
        type=str,
        required=True,
        help="Virgülle ayrılmış film adları",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help="Kaç öneri gösterilecek",
    )
    parser.add_argument(
        "--method",
        choices=("score_avg", "vector_avg"),
        default="score_avg",
        help="Çoklu filmde kullanılacak yöntem",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_cli_args()
    titles = [t.strip() for t in args.titles.split(",") if t.strip()]
    if not titles:
        raise SystemExit("En az bir film adı belirtmelisiniz.")
    df = cli_recommend(titles, top_n=args.top_n, method=args.method)
    if df.empty:
        print("Öneri bulunamadı.")
        return
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()

