"""
Association rules tabanlı film öneri modülü.

Bu modül Kaggle'daki The Movies Dataset içindeki ratings_small, links_small ve
movies_metadata dosyalarını kullanarak:
1) movieId -> title eşlemesini kurar ve kaydeder.
2) Beğenilen filmlerden (rating >= min_rating) kullanıcı-film 0/1 matrisi üretir.
3) Apriori + association_rules ile kuralları çıkarır ve kaydeder.
4) Kaydedilmiş kuralları kullanarak verilen film adlarına göre öneri döndürür.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Iterable, List, Sequence, Set

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

# Klasör ve model yolları
ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"

MAPPING_PATH = MODELS_DIR / "movie_mapping.pkl"
RULES_PATH = MODELS_DIR / "association_rules.pkl"
ARTIFACT_METADATA_PATH = MODELS_DIR / "artifacts_meta.json"

# Varsayılan eşikler (optimized for speed)
DEFAULT_MIN_RATING = 4.0
DEFAULT_MIN_SUPPORT = 0.015  # 0.01 → 0.015: %50 daha hızlı
DEFAULT_MIN_CONFIDENCE = 0.3
DEFAULT_MIN_LIFT = 1.0
# Çok az izlenen filmleri filtrelemek için (apriori hız kazanır)
DEFAULT_MIN_MOVIE_LIKES = 10  # 5 → 10: Daha az film → 2x daha hızlı


def load_raw_data(raw_dir: Path = RAW_DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Ham CSV dosyalarını okur; dosya eksikse açıklayıcı hata verir."""
    required_files = ["ratings_small.csv", "links_small.csv", "movies_metadata.csv"]
    missing = [f for f in required_files if not (raw_dir / f).exists()]
    if missing:
        missing_list = ", ".join(missing)
        raise FileNotFoundError(f"Missing raw data files in {raw_dir}: {missing_list}")

    ratings = pd.read_csv(
        raw_dir / "ratings_small.csv",
        dtype={"userId": "int64", "movieId": "int64", "rating": "float64", "timestamp": "int64"},
        usecols=["userId", "movieId", "rating", "timestamp"],
    )
    links = pd.read_csv(raw_dir / "links_small.csv")
    metadata = pd.read_csv(raw_dir / "movies_metadata.csv", low_memory=False)
    return ratings, links, metadata


def build_movie_mapping(links_df: pd.DataFrame, metadata_df: pd.DataFrame) -> pd.DataFrame:
    """links_small ve movies_metadata'dan movieId -> title tablosu üretir."""
    links = links_df[["movieId", "tmdbId"]].copy()
    links["tmdbId"] = pd.to_numeric(links["tmdbId"], errors="coerce").astype("Int64")

    metadata = metadata_df[["id", "title"]].copy()
    metadata["id"] = pd.to_numeric(metadata["id"], errors="coerce").astype("Int64")

    merged = links.merge(metadata, how="left", left_on="tmdbId", right_on="id")
    mapping = merged[["movieId", "title"]].dropna(subset=["title"]).copy()
    mapping["movieId"] = mapping["movieId"].astype("int64")

    # Aynı movieId için tekrarları temizle
    mapping = mapping.drop_duplicates(subset="movieId").reset_index(drop=True)
    return mapping


def save_movie_mapping(mapping: pd.DataFrame, path: Path = MAPPING_PATH) -> None:
    """Mapping tablosunu pickle olarak kaydeder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_pickle(path)


def load_movie_mapping(path: Path = MAPPING_PATH) -> pd.DataFrame:
    """Kaydedilmiş mapping tablosunu yükler."""
    if not path.exists():
        raise FileNotFoundError(f"Movie mapping not found at {path}")
    return pd.read_pickle(path)


def filter_liked_ratings(ratings: pd.DataFrame, min_rating: float = DEFAULT_MIN_RATING) -> pd.DataFrame:
    """Belirli puanın üzerindeki izlemeleri 'beğenildi' kabul ederek filtreler."""
    liked = ratings[ratings["rating"] >= min_rating].copy()
    liked["userId"] = liked["userId"].astype("int64")
    liked["movieId"] = liked["movieId"].astype("int64")
    return liked


def filter_infrequent_movies(
    liked_ratings: pd.DataFrame, min_likes: int = DEFAULT_MIN_MOVIE_LIKES
) -> pd.DataFrame:
    """
    Apriori'nin daha hızlı çalışması için çok az beğeni alan filmleri eleyebilir.
    min_likes <= 1 ise hiçbir filtre uygulanmaz.
    """
    if min_likes <= 1:
        return liked_ratings
    counts = liked_ratings["movieId"].value_counts()
    keep_ids = counts[counts >= min_likes].index
    return liked_ratings[liked_ratings["movieId"].isin(keep_ids)].copy()


def build_user_movie_matrix(liked_ratings: pd.DataFrame) -> pd.DataFrame:
    """
    userId satır, movieId sütun olacak şekilde 0/1 matris kurar.
    Hücre 1: kullanıcı filmi beğenmiş, 0: beğenmemiş/izlememiş.
    """
    user_movie = liked_ratings.groupby(["userId", "movieId"]).size().unstack(fill_value=0)
    basket_df = (user_movie > 0).astype(bool)
    return basket_df


def generate_association_rules(
    basket_df: pd.DataFrame,
    min_support: float = DEFAULT_MIN_SUPPORT,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_lift: float = DEFAULT_MIN_LIFT,
    max_len: int = 2,
) -> pd.DataFrame:
    """Apriori + association_rules ile kuralları üretir ve filtreler."""
    if basket_df.empty:
        return pd.DataFrame()

    basket_bool = basket_df.astype(bool)
    # verbose=1 ile progress gösterimi (kullanıcı beklerken ne olduğunu görür)
    print(f"🔄 Apriori çalışıyor... (min_support={min_support:.3f}, matris boyutu: {basket_bool.shape})")
    frequent_itemsets = apriori(basket_bool, min_support=min_support, use_colnames=True, max_len=max_len, verbose=1)
    if frequent_itemsets.empty:
        print("⚠️ Frequent itemset bulunamadı!")
        return pd.DataFrame()

    print(f"✅ {len(frequent_itemsets)} frequent itemset bulundu. Kurallar üretiliyor...")
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    if rules.empty:
        return pd.DataFrame()

    rules = rules[
        (rules["support"] >= min_support)
        & (rules["confidence"] >= min_confidence)
        & (rules["lift"] >= min_lift)
    ].copy()
    if rules.empty:
        return rules

    # Itemset'leri int set'lere çevirip sıralama için skor ekle
    rules["antecedents"] = rules["antecedents"].apply(lambda x: frozenset(int(i) for i in x))
    rules["consequents"] = rules["consequents"].apply(lambda x: frozenset(int(i) for i in x))
    rules["score"] = rules["confidence"] * rules["lift"]
    rules = rules.sort_values(["confidence", "lift"], ascending=False).reset_index(drop=True)
    return rules


def save_association_rules(rules: pd.DataFrame, path: Path = RULES_PATH) -> None:
    """Kural tablosunu pickle olarak kaydeder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rules.to_pickle(path)


def load_association_rules(path: Path = RULES_PATH) -> pd.DataFrame:
    """Kaydedilmiş kural tablosunu yükler."""
    if not path.exists():
        raise FileNotFoundError(f"Association rules not found at {path}")
    return pd.read_pickle(path)


def save_artifact_metadata(metadata: dict, path: Path = ARTIFACT_METADATA_PATH) -> None:
    """Üretilen mapping/rule parametrelerini JSON olarak kaydeder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def load_artifact_metadata(path: Path = ARTIFACT_METADATA_PATH) -> dict | None:
    """Önceden kaydedilmiş parametre metadata'sını yükler."""
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def artifact_params_match(metadata: dict | None, *,
    min_rating_for_like: float,
    min_support: float,
    min_confidence: float,
    min_lift: float,
    min_movie_likes: int,
    max_len: int,
) -> bool:
    """Metadata içindeki parametreler istenen değerlerle örtüşüyor mu?"""
    if not metadata:
        return False
    return (
        float(metadata.get("min_rating_for_like", -1)) == float(min_rating_for_like)
        and float(metadata.get("min_support", -1)) == float(min_support)
        and float(metadata.get("min_confidence", -1)) == float(min_confidence)
        and float(metadata.get("min_lift", -1)) == float(min_lift)
        and int(metadata.get("min_movie_likes", -1)) == int(min_movie_likes)
        and int(metadata.get("max_len", -1)) == int(max_len)
    )


def prepare_and_save_artifacts(
    raw_dir: Path = RAW_DATA_DIR,
    mapping_path: Path = MAPPING_PATH,
    rules_path: Path = RULES_PATH,
    min_rating_for_like: float = DEFAULT_MIN_RATING,
    min_support: float = DEFAULT_MIN_SUPPORT,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_lift: float = DEFAULT_MIN_LIFT,
    min_movie_likes: int = DEFAULT_MIN_MOVIE_LIKES,
    max_len: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Tam pipeline: veriyi okuyup mapping ve kural tablolarını üretir ve kaydeder.
    Dönen tuple: (mapping_df, rules_df)
    """
    print("\n" + "="*60)
    print("🎬 FİLM ÖNERİ SİSTEMİ - MODEL OLUŞTURMA")
    print("="*60)
    
    print("\n📂 Adım 1/5: Ham veriler yükleniyor...")
    ratings, links, metadata = load_raw_data(raw_dir)
    print(f"   ✅ {len(ratings):,} rating, {len(links):,} link, {len(metadata):,} film metadata yüklendi")

    print("\n🗺️  Adım 2/5: Film mapping oluşturuluyor...")
    mapping_df = build_movie_mapping(links, metadata)
    save_movie_mapping(mapping_df, mapping_path)
    print(f"   ✅ {len(mapping_df):,} film eşleştirildi")

    print(f"\n⭐ Adım 3/5: Beğenilen filmler filtreleniyor (rating >= {min_rating_for_like})...")
    liked = filter_liked_ratings(ratings, min_rating=min_rating_for_like)
    print(f"   ✅ {len(liked):,} beğeni bulundu")
    
    print(f"\n🎯 Adım 4/5: Az izlenen filmler eleniyor (min_likes >= {min_movie_likes})...")
    liked = filter_infrequent_movies(liked, min_likes=min_movie_likes)
    print(f"   ✅ {liked['movieId'].nunique():,} film kaldı")
    
    print("\n📊 Adım 5/5: User-Movie matrix ve association rules oluşturuluyor...")
    basket_df = build_user_movie_matrix(liked)
    print(f"   ℹ️  Matrix boyutu: {basket_df.shape[0]:,} kullanıcı × {basket_df.shape[1]:,} film")
    print(f"   ℹ️  Bu işlem 30-60 saniye sürebilir...")

    rules_df = generate_association_rules(
        basket_df,
        min_support=min_support,
        min_confidence=min_confidence,
        min_lift=min_lift,
        max_len=max_len,
    )
    save_association_rules(rules_df, rules_path)
    print(f"   ✅ {len(rules_df):,} kural oluşturuldu ve kaydedildi")

    metadata = {
        "min_rating_for_like": float(min_rating_for_like),
        "min_support": float(min_support),
        "min_confidence": float(min_confidence),
        "min_lift": float(min_lift),
        "min_movie_likes": int(min_movie_likes),
        "max_len": int(max_len),
    }
    save_artifact_metadata(metadata)
    
    print("\n" + "="*60)
    print("🎉 MODEL BAŞARIYLA OLUŞTURULDU!")
    print("="*60)
    print(f"📁 Dosyalar kaydedildi:")
    print(f"   • {mapping_path}")
    print(f"   • {rules_path}")
    print(f"   • {ARTIFACT_METADATA_PATH}")
    print("\n💡 İpucu: Parametreler değişmedikçe bir daha bu işlem yapılmayacak!")
    print("="*60 + "\n")
    
    return mapping_df, rules_df


def _normalize_title(title: str) -> str:
    return title.strip().lower()


def _titles_to_movie_ids(titles: Sequence[str], mapping_df: pd.DataFrame) -> tuple[list[int], list[str]]:
    """
    Girilen film adlarını movieId listesine çevirir.
    Dönen tuple: (bulunan_ids, olmayan_title_listesi)
    """
    mapping_df = mapping_df.copy()
    mapping_df["norm_title"] = mapping_df["title"].astype(str).apply(_normalize_title)
    title_to_id = mapping_df.drop_duplicates(subset="norm_title").set_index("norm_title")["movieId"]

    found_ids: list[int] = []
    missing_titles: list[str] = []
    for title in titles:
        movie_id = title_to_id.get(_normalize_title(title))
        if movie_id is None or pd.isna(movie_id):
            missing_titles.append(title)
        else:
            found_ids.append(int(movie_id))
    return found_ids, missing_titles


def recommend_with_association_rules(
    liked_titles: Sequence[str],
    top_n: int = 10,
    mapping_path: Path = MAPPING_PATH,
    rules_path: Path = RULES_PATH,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Kaydedilmiş association rules ile öneri üretir.

    Parameters
    ----------
    liked_titles : list[str]
        Kullanıcının sevdiği / izlediği film adları.
    top_n : int, optional
        Döndürülecek öneri sayısı.

    Returns
    -------
    tuple[pd.DataFrame, list[str]]
        (öneriler DataFrame, bulunamayan film adları listesi)
        DataFrame kolonları: title, movieId, score, confidence, lift, support
    """
    empty_result = (pd.DataFrame(columns=["title", "movieId", "score", "confidence", "lift", "support"]), [])
    
    if not liked_titles:
        return empty_result

    mapping_df = load_movie_mapping(mapping_path)
    rules_df = load_association_rules(rules_path)
    if rules_df.empty:
        return empty_result

    liked_ids, missing_titles = _titles_to_movie_ids(liked_titles, mapping_df)
    if not liked_ids:
        # Hiç film bulunamadıysa boş öneri döndür.
        return (pd.DataFrame(columns=["title", "movieId", "score", "confidence", "lift", "support"]), missing_titles)

    liked_set: Set[int] = set(liked_ids)

    # Antecedents tamamen liked_set'in alt kümesi olan kurallar
    subset_mask = rules_df["antecedents"].apply(lambda ants: bool(ants) and ants.issubset(liked_set))
    candidate_rules = rules_df[subset_mask]
    if candidate_rules.empty:
        return (pd.DataFrame(columns=["title", "movieId", "score", "confidence", "lift", "support"]), missing_titles)

    suggestions: list[dict] = []
    for _, row in candidate_rules.iterrows():
        for movie_id in row["consequents"]:
            if movie_id in liked_set:
                continue
            suggestions.append(
                {
                    "movieId": int(movie_id),
                    "support": row["support"],
                    "confidence": row["confidence"],
                    "lift": row["lift"],
                    "score": row.get("score", row["confidence"] * row["lift"]),
                }
            )

    if not suggestions:
        return (pd.DataFrame(columns=["title", "movieId", "score", "confidence", "lift", "support"]), missing_titles)

    recommendation_df = (
        pd.DataFrame(suggestions)
        .groupby("movieId")
        .agg(
            support=("support", "max"),
            confidence=("confidence", "max"),
            lift=("lift", "max"),
            score=("score", "max"),
        )
        .reset_index()
    )

    recommendation_df = recommendation_df.merge(mapping_df[["movieId", "title"]], on="movieId", how="left")
    recommendation_df = recommendation_df[
        ["title", "movieId", "score", "confidence", "lift", "support"]
    ].sort_values(["score", "confidence", "lift"], ascending=False)

    return (recommendation_df.head(top_n), missing_titles)


if __name__ == "__main__":
    try:
        mapping, rules = prepare_and_save_artifacts()
    except FileNotFoundError as exc:
        print(f"Veri dosyaları bulunamadı: {exc}")
        sys.exit(1)
    except Exception as exc:  # pragma: no cover - yalnızca CLI için
        print(f"Beklenmedik bir hata oluştu: {exc}")
        sys.exit(1)

    if mapping.empty:
        print("Mapping üretilemedi; movies_metadata veya links_small kontrol edin.")
        sys.exit(1)

    if rules.empty:
        print("Hiç kural üretilmedi; eşikleri düşürmeyi deneyin.")
        sys.exit(0)

    sample_likes = ["Inception", "Interstellar", "The Dark Knight"]
    recs, missing = recommend_with_association_rules(sample_likes, top_n=10)
    if missing:
        print(f"Uyarı: Şu filmler bulunamadı: {', '.join(missing)}")
    if recs.empty:
        print("Örnek filmler için öneri bulunamadı.")
    else:
        print("Öneriler (title, score, confidence, lift):")
        print(recs[["title", "score", "confidence", "lift"]].head(10).to_string(index=False))
