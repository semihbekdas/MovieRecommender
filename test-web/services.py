from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
import inspect
from pathlib import Path
from typing import Literal, Sequence

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTENT_BASED_DIR = PROJECT_ROOT / "Content-Based"

if str(CONTENT_BASED_DIR) not in sys.path:
    sys.path.append(str(CONTENT_BASED_DIR))

import evaluate_content as ec  # type: ignore  # noqa: E402  (lazy path injection)
import recommender_content as rc  # type: ignore  # noqa: E402
import user_profile as up  # type: ignore  # noqa: E402

DEFAULT_RATINGS_PATH = ec.DEFAULT_RATINGS
DEFAULT_LINKS_PATH = ec.DEFAULT_LINKS
_EVAL_HAS_RESTRICT = "restrict_to_links" in inspect.signature(ec.evaluate).parameters


MethodLiteral = Literal["score_avg", "vector_avg"]
EvalModeLiteral = Literal["standard", "profile"]


@dataclass
class FileStatus:
    label: str
    path: Path
    exists: bool
    size_mb: float | None = None
    modified_at: datetime | None = None


@dataclass
class BundleSummary:
    ready: bool
    message: str
    files: list[FileStatus]


@dataclass
class RecommendationResponse:
    dataframe: pd.DataFrame | None
    missing_titles: list[str]
    used_fallback: bool
    movie_ids: list[int]
    error: str | None = None


@dataclass
class EvaluationResponse:
    hit_rate: float | None  # Film bazlı: hits / total_hidden
    hits: int | None
    tested: int | None
    samples: list[dict] | None
    error: str | None = None
    # Leave-K-Out için ek alanlar
    n_hidden: int | None = None
    total_hidden: int | None = None
    avg_recall: float | None = None
    avg_precision: float | None = None
    # Smart hide için ek alanlar
    smart_hide: bool | None = None
    min_hide_similarity: float | None = None
    avg_hide_similarity: float | None = None
    skipped_no_similar: int | None = None
    # Kullanıcı bazlı metrikler (yeni)
    hit_rate_user: float | None = None  # Kullanıcı bazlı: users_with_hit / tested
    users_with_hit: int | None = None  # En az 1 hit alan kullanıcı sayısı


@dataclass
class ComparisonResult:
    """Farklı benzerlik eşikleri için karşılaştırma sonucu."""
    threshold: float
    hit_rate: float  # Film bazlı
    hits: int
    tested: int
    skipped: int
    avg_hide_similarity: float
    total_hidden: int
    avg_recall: float
    error: str | None = None
    # Kullanıcı bazlı metrikler (yeni)
    hit_rate_user: float | None = None
    users_with_hit: int | None = None


@dataclass(frozen=True)
class TitleOption:
    label: str
    title: str
    tmdb_id: int
    vote_count: int | None = None
    year: str | None = None


@dataclass
class MetadataStats:
    total_titles: int
    non_empty_overview: int
    distinct_genres: int


@dataclass
class RatingStats:
    path: Path
    total_rows: int
    unique_users: int
    unique_movies: int
    avg_ratings_per_user: float


def _describe_file(label: str, path: Path) -> FileStatus:
    if not path.exists():
        return FileStatus(label=label, path=path, exists=False)
    stat = path.stat()
    size_mb = round(stat.st_size / (1024 * 1024), 2)
    modified_at = datetime.fromtimestamp(stat.st_mtime)
    return FileStatus(
        label=label,
        path=path,
        exists=True,
        size_mb=size_mb,
        modified_at=modified_at,
    )


def _artifact_status_list() -> list[FileStatus]:
    statuses = [
        _describe_file("TF-IDF Vektörizer", rc.VECTORIZER_PATH),
        _describe_file("TF-IDF Matris", rc.MATRIX_PATH),
        _describe_file("Metadata (parquet)", rc.METADATA_PARQUET),
    ]

    alt_pickle = rc.MODELS_DIR / "metadata.pkl"
    pickle_path = rc.METADATA_PICKLE if rc.METADATA_PICKLE.exists() else alt_pickle
    statuses.append(_describe_file("Metadata (pickle)", pickle_path))
    return statuses


def get_bundle_summary(*, force_reload: bool = False) -> BundleSummary:
    statuses = _artifact_status_list()
    missing = [s for s in statuses if not s.exists]

    if missing:
        missing_names = ", ".join(s.label for s in missing)
        return BundleSummary(
            ready=False,
            message=f"Eksik artefaktlar: {missing_names}",
            files=statuses,
        )

    try:
        rc.load_artifacts(force_reload=force_reload)
    except Exception as exc:  # pragma: no cover - sadece diagnostik
        return BundleSummary(
            ready=False,
            message=f"Artefaktlar yüklenirken hata: {exc}",
            files=statuses,
        )

    return BundleSummary(
        ready=True,
        message="Artefaktlar yüklendi.",
        files=statuses,
    )


def load_bundle(force_reload: bool = False) -> rc.ArtifactBundle:
    return rc.load_artifacts(force_reload=force_reload)


@lru_cache(maxsize=4)
def get_movielens_tmdb_ids(path: str) -> set[int]:
    links = ec.load_links(Path(path))
    return set(links["tmdbId"].astype(int).tolist())


def _apply_movielens_postprocessing(
    df: pd.DataFrame | None,
    allowed_ids: set[int] | None,
) -> pd.DataFrame | None:
    if df is None or df.empty:
        return df
    result = df
    if allowed_ids:
        tmdb_series = pd.to_numeric(result["tmdb_id"], errors="coerce").astype("Int64")
        mask = tmdb_series.isin(list(allowed_ids))
        result = result[mask]
        if result.empty:
            return result
    if "similarity" in result.columns and "vote_count" in result.columns:
        vote_counts = result["vote_count"].fillna(0).astype(float)
        similarity = result["similarity"].fillna(0).astype(float)
        result = result.copy()
        result["pop_weighted_score"] = similarity * (1.0 + np.log1p(vote_counts))
        result = result.sort_values(
            ["pop_weighted_score", "similarity"], ascending=False
        ).drop(columns=["pop_weighted_score"])
    return result


def make_recommendations(
    titles: Sequence[str],
    *,
    top_n: int = rc.DEFAULT_TOP_N,
    method: MethodLiteral = "score_avg",
    restrict_to_movielens: bool = False,
    movielens_links_path: Path | None = None,
    use_profile_backend: bool = False,
) -> RecommendationResponse:
    cleaned_titles = [t.strip() for t in titles if t.strip()]
    if not cleaned_titles:
        return RecommendationResponse(
            dataframe=None,
            missing_titles=[],
            used_fallback=False,
            movie_ids=[],
            error="En az bir film adı girilmelidir.",
        )

    try:
        bundle = load_bundle()
    except Exception as exc:
        return RecommendationResponse(
            dataframe=None,
            missing_titles=[],
            used_fallback=False,
            movie_ids=[],
            error=str(exc),
        )

    movie_ids, missing = rc.titles_to_ids(cleaned_titles, bundle)
    used_fallback = False
    dataframe: pd.DataFrame | None = None

    if use_profile_backend:
        profile_df, missing_profile = up.recommend_with_profile(
            cleaned_titles,
            top_n=top_n,
        )
        missing = missing_profile
        dataframe = profile_df
        if not movie_ids or dataframe is None or dataframe.empty:
            used_fallback = True
    else:
        if not movie_ids:
            used_fallback = True
            dataframe = rc.get_popular_fallback(top_n=top_n)
        elif len(movie_ids) == 1:
            dataframe = rc.recommend_single(movie_ids[0], top_n=top_n, method=method)
        else:
            dataframe = rc.recommend_multi(movie_ids, top_n=top_n, method=method)
            if dataframe.empty:
                used_fallback = True
                dataframe = rc.get_popular_fallback(top_n=top_n)

    if restrict_to_movielens:
        links_path = movielens_links_path or DEFAULT_LINKS_PATH
        allowed_ids = get_movielens_tmdb_ids(str(links_path))
        dataframe = _apply_movielens_postprocessing(dataframe, allowed_ids)
        if dataframe is None or dataframe.empty:
            used_fallback = True
            fallback = rc.get_popular_fallback(top_n=top_n)
            dataframe = _apply_movielens_postprocessing(fallback, allowed_ids)

    return RecommendationResponse(
        dataframe=dataframe,
        missing_titles=missing,
        used_fallback=used_fallback,
        movie_ids=movie_ids,
    )


def get_metadata_preview(limit: int = 20) -> pd.DataFrame | None:
    try:
        bundle = load_bundle()
    except Exception:
        return None
    columns = [
        "title",
        "tmdb_id",
        "genres",
        "vote_average",
        "vote_count",
        "matrix_index",
    ]
    available_cols = [c for c in columns if c in bundle.metadata.columns]
    return bundle.metadata[available_cols].head(limit)


def get_metadata_stats() -> MetadataStats:
    bundle = load_bundle()
    metadata = bundle.metadata
    total_titles = len(metadata)
    overview_series = metadata["overview"] if "overview" in metadata else pd.Series(dtype=str)
    non_empty_overview = overview_series.fillna("").astype(str).str.strip().ne("").sum()
    genres_series = metadata["genres"] if "genres" in metadata else pd.Series(dtype=str)
    genres_col = genres_series.dropna().astype(str)
    distinct_genres = (
        genres_col.str.split(",").explode().str.strip().replace("", pd.NA).dropna().nunique()
    )
    return MetadataStats(
        total_titles=int(total_titles),
        non_empty_overview=int(non_empty_overview),
        distinct_genres=int(distinct_genres),
    )


@lru_cache(maxsize=2)
def get_rating_stats(path: str) -> RatingStats:
    ratings_path = Path(path)
    df = ec.load_ratings(ratings_path)
    unique_users = df["userId"].nunique()
    unique_movies = df["movieId"].nunique()
    total_rows = len(df)
    avg = total_rows / unique_users if unique_users else 0.0
    return RatingStats(
        path=ratings_path,
        total_rows=int(total_rows),
        unique_users=int(unique_users),
        unique_movies=int(unique_movies),
        avg_ratings_per_user=float(avg),
    )


def evaluate_model(
    *,
    ratings_path: Path,
    links_path: Path,
    n_users: int,
    top_n: int,
    mode: EvalModeLiteral,
    rating_threshold: float,
    min_liked: int,
    method: MethodLiteral,
    seed: int,
    restrict_to_movielens: bool = False,
    n_hidden: int = 1,
    smart_hide: bool = True,
    min_hide_similarity: float = 0.05,
) -> EvaluationResponse:
    eval_kwargs = dict(
        ratings_path=ratings_path,
        links_path=links_path,
        n_users=n_users,
        top_n=top_n,
        mode=mode,
        rating_threshold=rating_threshold,
        min_liked=min_liked,
        method=method,
        seed=seed,
        n_hidden=n_hidden,
        smart_hide=smart_hide,
        min_hide_similarity=min_hide_similarity,
    )
    if restrict_to_movielens and _EVAL_HAS_RESTRICT:
        eval_kwargs["restrict_to_links"] = True

    try:
        result = ec.evaluate(**eval_kwargs)
    except Exception as exc:
        if (
            restrict_to_movielens
            and not _EVAL_HAS_RESTRICT
            and isinstance(exc, TypeError)
            and "restrict_to_links" in str(exc)
        ):
            eval_kwargs.pop("restrict_to_links", None)
            result = ec.evaluate(**eval_kwargs)
        else:
            return EvaluationResponse(
                hit_rate=None,
                hits=None,
                tested=None,
                samples=None,
                error=str(exc),
            )

    return EvaluationResponse(
        hit_rate=result["hit_rate"],
        hits=result["hits"],
        tested=result["tested"],
        samples=result.get("samples", []),
        error=None,
        n_hidden=result.get("n_hidden", 1),
        total_hidden=result.get("total_hidden"),
        avg_recall=result.get("avg_recall"),
        avg_precision=result.get("avg_precision"),
        smart_hide=result.get("smart_hide"),
        min_hide_similarity=result.get("min_hide_similarity"),
        avg_hide_similarity=result.get("avg_hide_similarity"),
        skipped_no_similar=result.get("skipped_no_similar"),
        # Kullanıcı bazlı metrikler (yeni)
        hit_rate_user=result.get("hit_rate_user"),
        users_with_hit=result.get("users_with_hit"),
    )


def evaluate_multiple_thresholds(
    *,
    ratings_path: Path,
    links_path: Path,
    n_users: int,
    top_n: int,
    mode: EvalModeLiteral,
    rating_threshold: float,
    min_liked: int,
    method: MethodLiteral,
    seed: int,
    thresholds: list[float],
    n_hidden: int = 1,
    restrict_to_movielens: bool = False,
) -> list[ComparisonResult]:
    """
    Farklı benzerlik eşikleri ile karşılaştırmalı değerlendirme yap.
    
    Args:
        thresholds: Test edilecek benzerlik eşikleri listesi (örn: [0.10, 0.20, 0.30, 0.40])
    
    Returns:
        Her eşik için ComparisonResult listesi
    """
    results = []
    
    for threshold in thresholds:
        try:
            response = evaluate_model(
                ratings_path=ratings_path,
                links_path=links_path,
                n_users=n_users,
                top_n=top_n,
                mode=mode,
                rating_threshold=rating_threshold,
                min_liked=min_liked,
                method=method,
                seed=seed,
                restrict_to_movielens=restrict_to_movielens,
                n_hidden=n_hidden,
                smart_hide=True,
                min_hide_similarity=threshold,
            )
            
            if response.error:
                results.append(ComparisonResult(
                    threshold=threshold,
                    hit_rate=0.0,
                    hits=0,
                    tested=0,
                    skipped=0,
                    avg_hide_similarity=0.0,
                    total_hidden=0,
                    avg_recall=0.0,
                    error=response.error,
                    hit_rate_user=0.0,
                    users_with_hit=0,
                ))
            else:
                results.append(ComparisonResult(
                    threshold=threshold,
                    hit_rate=response.hit_rate or 0.0,
                    hits=response.hits or 0,
                    tested=response.tested or 0,
                    skipped=response.skipped_no_similar or 0,
                    avg_hide_similarity=response.avg_hide_similarity or 0.0,
                    total_hidden=response.total_hidden or 0,
                    avg_recall=response.avg_recall or 0.0,
                    error=None,
                    hit_rate_user=response.hit_rate_user or 0.0,
                    users_with_hit=response.users_with_hit or 0,
                ))
        except Exception as exc:
            results.append(ComparisonResult(
                threshold=threshold,
                hit_rate=0.0,
                hits=0,
                tested=0,
                skipped=0,
                avg_hide_similarity=0.0,
                total_hidden=0,
                avg_recall=0.0,
                error=str(exc),
                hit_rate_user=0.0,
                users_with_hit=0,
            ))
    
    return results


def _extract_year(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value:
        return value[:4]
    return None


@lru_cache(maxsize=4)
def get_title_options(limit: int = 5000, min_vote_count: int = 20) -> tuple[TitleOption, ...]:
    bundle = load_bundle()
    metadata = bundle.metadata.copy()
    if "vote_count" in metadata.columns:
        metadata["vote_count"] = metadata["vote_count"].fillna(0).astype(int)
    else:
        metadata["vote_count"] = 0
    if "release_date" in metadata.columns:
        metadata["year"] = metadata["release_date"].apply(_extract_year)
    else:
        metadata["year"] = None

    subset = (
        metadata[["title", "tmdb_id", "vote_count", "year"]]
        .dropna(subset=["title", "tmdb_id"])
        .astype({"tmdb_id": int})
    )
    subset = subset[subset["vote_count"] >= min_vote_count]
    subset = subset.sort_values("vote_count", ascending=False).head(limit)

    options: list[TitleOption] = []
    for _, row in subset.iterrows():
        year = row.get("year")
        year_part = f" ({year})" if isinstance(year, str) and year else ""
        label = f"{row['title']}{year_part} · TMDB:{row['tmdb_id']}"
        options.append(
            TitleOption(
                label=label,
                title=str(row["title"]),
                tmdb_id=int(row["tmdb_id"]),
                vote_count=int(row.get("vote_count", 0)),
                year=year if isinstance(year, str) else None,
            )
        )
    return tuple(options)

