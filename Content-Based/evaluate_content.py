from __future__ import annotations

import argparse
import random
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
from typing import Sequence

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_RATINGS = DATA_DIR / "ratings_small.csv"
DEFAULT_LINKS = DATA_DIR / "links_small.csv"

if str(BASE_DIR) not in __import__("sys").path:
    __import__("sys").path.append(str(BASE_DIR))

import recommender_content as rc  # noqa: E402
import user_profile as up  # noqa: E402


def load_ratings(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"ratings_small.csv bulunamadı: {path}")
    df = pd.read_csv(path)
    expected = {"userId", "movieId", "rating"}
    if not expected.issubset(df.columns):
        raise ValueError("ratings_small.csv beklenen kolonlara sahip değil.")
    return df


def load_links(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"links_small.csv bulunamadı: {path}")
    df = pd.read_csv(path)
    if "movieId" not in df.columns or "tmdbId" not in df.columns:
        raise ValueError("links_small.csv içinde movieId/tmdbId kolonları yok.")
    df["tmdbId"] = pd.to_numeric(df["tmdbId"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["tmdbId"])
    df["tmdbId"] = df["tmdbId"].astype(int)
    return df


def build_movieid_to_tmdb(links_df: pd.DataFrame) -> dict[int, int]:
    return links_df.drop_duplicates(subset="movieId").set_index("movieId")["tmdbId"].to_dict()


def evaluate(
    ratings_path: Path,
    links_path: Path,
    *,
    n_users: int,
    top_n: int,
    mode: str,
    rating_threshold: float,
    min_liked: int,
    method: str,
    seed: int,
) -> dict:
    ratings_df = load_ratings(ratings_path)
    links_df = load_links(links_path)
    movie_map = build_movieid_to_tmdb(links_df)
    bundle = rc.load_artifacts()

    rng = random.Random(seed)
    user_ids = ratings_df["userId"].unique().tolist()
    rng.shuffle(user_ids)

    hits = 0
    tested = 0
    samples: list[dict] = []
    title_lookup = (
        bundle.metadata.drop_duplicates(subset="tmdb_id")
        .set_index("tmdb_id")["title"]
        .to_dict()
    )

    for user_id in user_ids:
        user_ratings = ratings_df[ratings_df["userId"] == user_id]
        liked = user_ratings[user_ratings["rating"] >= rating_threshold]
        if len(liked) < min_liked:
            continue

        tmdb_ids = []
        tmdb_ratings = []
        for _, row in liked.iterrows():
            tmdb_id = movie_map.get(int(row["movieId"]))
            if tmdb_id is None:
                continue
            if tmdb_id not in bundle.id_to_index:
                continue
            tmdb_ids.append(tmdb_id)
            tmdb_ratings.append(float(row["rating"]))

        if len(tmdb_ids) < 2:
            continue

        hidden_idx = rng.randrange(len(tmdb_ids))
        hidden_movie = tmdb_ids[hidden_idx]
        hidden_rating = tmdb_ratings[hidden_idx]

        remaining_ids = tmdb_ids[:hidden_idx] + tmdb_ids[hidden_idx + 1 :]
        remaining_ratings = tmdb_ratings[:hidden_idx] + tmdb_ratings[hidden_idx + 1 :]

        if mode == "profile":
            profile = up.build_user_profile(remaining_ids, ratings=remaining_ratings)
            scores = cosine_similarity(profile.reshape(1, -1), bundle.matrix).ravel()
            recs = rc.scores_to_dataframe(scores, bundle, exclude_ids=remaining_ids, top_n=top_n)
        else:
            recs = rc.recommend_multi(
                remaining_ids,
                top_n=top_n,
                method=method,
            )

        if recs.empty:
            continue

        try:
            rank = recs["tmdb_id"].tolist().index(hidden_movie) + 1
            hit = rank <= top_n
        except ValueError:
            rank = None
            hit = False

        hits += int(hit)
        tested += 1
        samples.append(
            {
                "userId": int(user_id),
                "hidden_tmdb": int(hidden_movie),
                "hidden_title": title_lookup.get(hidden_movie, "Unknown"),
                "hit": bool(hit),
                "rank": rank,
                "hidden_rating": hidden_rating,
            }
        )

        if tested >= n_users:
            break

    hit_rate = hits / tested if tested else 0.0
    return {
        "hit_rate": hit_rate,
        "hits": hits,
        "tested": tested,
        "samples": samples[:10],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Content-Based HitRate@N değerlendirmesi")
    parser.add_argument("--ratings", type=Path, default=DEFAULT_RATINGS, help="ratings_small.csv yolu")
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS, help="links_small.csv yolu")
    parser.add_argument("--n-users", type=int, default=50, help="Kaç kullanıcı test edilecek")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--mode", choices=("standard", "profile"), default="standard")
    parser.add_argument("--rating-threshold", type=float, default=4.0)
    parser.add_argument("--min-liked", type=int, default=3)
    parser.add_argument(
        "--method",
        choices=("score_avg", "vector_avg"),
        default="score_avg",
        help="Standart mod için çoklu film yöntemi",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = evaluate(
        args.ratings,
        args.links,
        n_users=args.n_users,
        top_n=args.top_n,
        mode=args.mode,
        rating_threshold=args.rating_threshold,
        min_liked=args.min_liked,
        method=args.method,
        seed=args.seed,
    )
    print(f"HitRate@{args.top_n}: {result['hit_rate']:.3f} ({result['hits']}/{result['tested']})")
    if result["samples"]:
        print("Örnek kullanıcılar:")
        for sample in result["samples"]:
            hit_flag = "✅" if sample["hit"] else "❌"
            rank = sample["rank"] if sample["rank"] is not None else "-"
            print(
                f" {hit_flag} user={sample['userId']} hidden='{sample['hidden_title']}' rank={rank}"
            )


if __name__ == "__main__":
    main()

