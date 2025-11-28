from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal, Sequence

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTENT_BASED_DIR = PROJECT_ROOT / "Content-Based"

if str(CONTENT_BASED_DIR) not in sys.path:
    sys.path.append(str(CONTENT_BASED_DIR))

import evaluate_content as ec  # type: ignore  # noqa: E402  (lazy path injection)
import recommender_content as rc  # type: ignore  # noqa: E402

DEFAULT_RATINGS_PATH = ec.DEFAULT_RATINGS
DEFAULT_LINKS_PATH = ec.DEFAULT_LINKS


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
    hit_rate: float | None
    hits: int | None
    tested: int | None
    samples: list[dict] | None
    error: str | None = None


@dataclass(frozen=True)
class TitleOption:
    label: str
    title: str
    tmdb_id: int
    vote_count: int | None = None
    year: str | None = None


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


def make_recommendations(
    titles: Sequence[str],
    *,
    top_n: int = rc.DEFAULT_TOP_N,
    method: MethodLiteral = "score_avg",
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
) -> EvaluationResponse:
    try:
        result = ec.evaluate(
            ratings_path,
            links_path,
            n_users=n_users,
            top_n=top_n,
            mode=mode,
            rating_threshold=rating_threshold,
            min_liked=min_liked,
            method=method,
            seed=seed,
        )
    except Exception as exc:
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
    )


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

