from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import recommender_content as rc  # noqa: E402


def build_user_profile(
    movie_ids: Sequence[int],
    *,
    ratings: Sequence[float] | None = None,
) -> np.ndarray:
    bundle = rc.load_artifacts()
    indices: list[int] = []
    weights: list[float] = []

    for idx, movie_id in enumerate(movie_ids):
        matrix_index = bundle.id_to_index.get(movie_id)
        if matrix_index is None:
            continue
        indices.append(matrix_index)
        weight = 1.0
        if ratings and idx < len(ratings):
            try:
                weight = float(ratings[idx])
            except ValueError:
                weight = 1.0
        weights.append(max(weight, 1e-6))

    if not indices:
        raise ValueError("Seçilen filmler metadata içinde bulunamadı.")

    subset = bundle.matrix[indices].toarray()
    weight_arr = np.array(weights, dtype=float)
    weight_arr = weight_arr / weight_arr.sum()
    weighted = subset * weight_arr[:, np.newaxis]
    profile = weighted.sum(axis=0)
    profile = np.asarray(profile, dtype=np.float32)

    with np.errstate(all="ignore"):
        norm = np.linalg.norm(profile)
    if not np.isfinite(norm) or norm == 0.0:
        raise ValueError("Profil vektörü sıfır oldu; farklı filmler deneyin.")
    return profile / norm


def recommend_with_profile(
    titles: Sequence[str],
    *,
    ratings: Sequence[float] | None = None,
    top_n: int = rc.DEFAULT_TOP_N,
) -> tuple[pd.DataFrame, list[str]]:
    bundle = rc.load_artifacts()
    movie_ids, missing = rc.titles_to_ids(titles, bundle)
    if not movie_ids:
        return rc.get_popular_fallback(top_n=top_n), missing

    profile = build_user_profile(movie_ids, ratings=ratings)
    scores = cosine_similarity(profile.reshape(1, -1), bundle.matrix).ravel()
    df = rc.scores_to_dataframe(scores, bundle, exclude_ids=movie_ids, top_n=top_n)
    if df.empty:
        return rc.get_popular_fallback(top_n=top_n), missing
    return df, missing


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="User profile tabanlı öneri aracı")
    parser.add_argument("--titles", type=str, required=True, help="Virgülle ayrılmış film listesi")
    parser.add_argument(
        "--ratings",
        type=str,
        default="",
        help="Seçilen filmler için virgüllü rating listesi (örn: 5,4.5,3)",
    )
    parser.add_argument("--top-n", type=int, default=rc.DEFAULT_TOP_N)
    return parser.parse_args()


def parse_ratings(text: str) -> list[float]:
    if not text:
        return []
    values: list[float] = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(float(item))
        except ValueError:
            continue
    return values


def main() -> None:
    args = parse_cli_args()
    titles = [t.strip() for t in args.titles.split(",") if t.strip()]
    ratings = parse_ratings(args.ratings)
    df, missing = recommend_with_profile(titles, ratings=ratings, top_n=args.top_n)
    if missing:
        print(f"⚠️ Bulunamayan filmler: {', '.join(missing)}")
    if df.empty:
        print("Öneri bulunamadı.")
        return
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()

