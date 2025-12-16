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
DEFAULT_RATINGS = DATA_DIR / "ratings.csv"
DEFAULT_LINKS = DATA_DIR / "links.csv"

if str(BASE_DIR) not in __import__("sys").path:
    __import__("sys").path.append(str(BASE_DIR))

import recommender_content as rc  # noqa: E402
import user_profile as up  # noqa: E402


def load_ratings(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"ratings verisi bulunamadı: {path}")
    df = pd.read_csv(path)
    expected = {"userId", "movieId", "rating"}
    if not expected.issubset(df.columns):
        raise ValueError("ratings.csv beklenen kolonlara sahip değil.")
    return df


def load_links(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"links verisi bulunamadı: {path}")
    df = pd.read_csv(path)
    if "movieId" not in df.columns or "tmdbId" not in df.columns:
        raise ValueError("links.csv içinde movieId/tmdbId kolonları yok.")
    df["tmdbId"] = pd.to_numeric(df["tmdbId"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["tmdbId"])
    df["tmdbId"] = df["tmdbId"].astype(int)
    return df


def build_movieid_to_tmdb(links_df: pd.DataFrame) -> dict[int, int]:
    return links_df.drop_duplicates(subset="movieId").set_index("movieId")["tmdbId"].to_dict()


def _compute_batch_similarity(
    bundle: rc.ArtifactBundle,
    tmdb_ids: list[int],
) -> dict[tuple[int, int], float]:
    """
    Verilen film listesi için tüm çiftlerin benzerliğini tek seferde hesapla.
    Çok daha hızlı! O(n) matrix lookup + O(n²) memory ama tek batch cosine.
    """
    indices = []
    valid_ids = []
    for tid in tmdb_ids:
        idx = bundle.id_to_index.get(tid)
        if idx is not None:
            indices.append(idx)
            valid_ids.append(tid)
    
    if len(indices) < 2:
        return {}
    
    # Tek seferde tüm benzerlik matrisini hesapla
    subset_matrix = bundle.matrix[indices]
    sim_matrix = cosine_similarity(subset_matrix)
    
    # Dict olarak döndür
    result = {}
    for i, id1 in enumerate(valid_ids):
        for j, id2 in enumerate(valid_ids):
            if i != j:
                result[(id1, id2)] = float(sim_matrix[i, j])
    
    return result


def _find_similar_movie_to_hide_fast(
    sim_dict: dict[tuple[int, int], float],
    tmdb_ids: list[int],
    min_similarity: float,
    rng: random.Random,
    already_hidden: set[int] | None = None,
) -> tuple[int, float] | None:
    """
    Hızlı versiyon: Önceden hesaplanmış benzerlik dict'i kullanır.
    
    Returns: (hidden_tmdb_id, max_similarity) veya None
    """
    if already_hidden is None:
        already_hidden = set()
    
    available = [tid for tid in tmdb_ids if tid not in already_hidden]
    
    if len(available) < 2:
        return None
    
    candidates = []
    
    for candidate_id in available:
        # Bu film gizlenirse, kalanlarla max benzerlik
        remaining = [tid for tid in available if tid != candidate_id]
        
        max_sim = 0.0
        for other_id in remaining:
            key = (candidate_id, other_id)
            sim = sim_dict.get(key, 0.0)
            if sim > max_sim:
                max_sim = sim
        
        if max_sim >= min_similarity:
            candidates.append((candidate_id, max_sim))
    
    if not candidates:
        return None
    
    # Rastgele bir aday seç
    rng.shuffle(candidates)
    return candidates[0]


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
    restrict_to_links: bool = False,
    n_hidden: int = 1,
    smart_hide: bool = True,
    min_hide_similarity: float = 0.05,
) -> dict:
    """
    Content-Based model değerlendirmesi.
    
    Leave-K-Out yaklaşımı:
    - n_hidden=1: Klasik leave-one-out (tek film gizle)
    - n_hidden>1: Birden fazla film gizle, kaç tanesi yakalandığına bak
    
    Smart Hide (Akıllı Gizleme):
    - smart_hide=True: Gizlenen film, kalan filmlerle belirli bir benzerliğin üzerinde olmalı
    - min_hide_similarity: Minimum benzerlik eşiği (varsayılan: 0.05)
    - Bu sayede "içerik olarak benzemeyen" filmler gizlenmez, değerlendirme daha adil olur
    
    Metrikler:
    - hit_rate: Toplam hit sayısı / Toplam gizlenen film sayısı
    - recall@n: Her kullanıcı için gizlenenlerden kaçı Top-N'de
    - precision@n: Her kullanıcı için Top-N'den kaçı gizlenenlerden
    """
    ratings_df = load_ratings(ratings_path)
    links_df = load_links(links_path)
    movie_map = build_movieid_to_tmdb(links_df)
    allowed_tmdb_ids: set[int] | None = None
    if restrict_to_links:
        allowed_tmdb_ids = set(links_df["tmdbId"].astype(int).tolist())
    bundle = rc.load_artifacts()

    rng = random.Random(seed)
    user_ids = ratings_df["userId"].unique().tolist()
    rng.shuffle(user_ids)

    # Toplam istatistikler
    total_hits = 0
    total_hidden = 0
    tested_users = 0
    skipped_no_similar = 0
    users_with_hit = 0  # En az 1 hit alan kullanıcı sayısı
    
    # Kullanıcı bazlı recall/precision
    user_recalls: list[float] = []
    user_precisions: list[float] = []
    avg_hide_similarities: list[float] = []
    
    samples: list[dict] = []
    title_lookup = (
        bundle.metadata.drop_duplicates(subset="tmdb_id")
        .set_index("tmdb_id")["title"]
        .to_dict()
    )

    # min_liked, en az n_hidden + 1 film gerektirir (gizlenecek + kalan)
    effective_min_liked = max(min_liked, n_hidden + 2)

    for user_id in user_ids:
        user_ratings = ratings_df[ratings_df["userId"] == user_id]
        liked = user_ratings[user_ratings["rating"] >= rating_threshold]
        if len(liked) < effective_min_liked:
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

        # En az n_hidden + 1 film olmalı (gizlenecekler + en az 1 kalan)
        if len(tmdb_ids) < n_hidden + 1:
            continue

        # Film gizleme stratejisi
        hidden_movies = []
        hidden_ratings_list = []
        hidden_similarities = []
        
        if smart_hide:
            # Akıllı gizleme: Benzer filmleri gizle (HIZLI VERSİYON)
            # Önce tüm benzerlik matrisini tek seferde hesapla
            sim_dict = _compute_batch_similarity(bundle, tmdb_ids)
            
            already_hidden: set[int] = set()
            for _ in range(n_hidden):
                result = _find_similar_movie_to_hide_fast(
                    sim_dict, tmdb_ids, min_hide_similarity, rng, already_hidden
                )
                
                if result is None:
                    break
                
                hidden_id, sim = result
                hidden_idx = tmdb_ids.index(hidden_id)
                
                hidden_movies.append(hidden_id)
                hidden_ratings_list.append(tmdb_ratings[hidden_idx])
                hidden_similarities.append(sim)
                already_hidden.add(hidden_id)
            
            if len(hidden_movies) < n_hidden:
                skipped_no_similar += 1
                continue
        else:
            # Klasik rastgele gizleme
            all_indices = list(range(len(tmdb_ids)))
            rng.shuffle(all_indices)
            hidden_indices = sorted(all_indices[:n_hidden], reverse=True)
            
            for idx in hidden_indices:
                hidden_movies.append(tmdb_ids[idx])
                hidden_ratings_list.append(tmdb_ratings[idx])
        
        # Kalan filmler
        hidden_set = set(hidden_movies)
        remaining_ids = [tid for tid in tmdb_ids if tid not in hidden_set]
        remaining_ratings = [
            tmdb_ratings[i] for i, tid in enumerate(tmdb_ids) if tid not in hidden_set
        ]

        if len(remaining_ids) < 1:
            continue

        # Öneri üret
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

        if allowed_tmdb_ids is not None:
            recs = recs[recs["tmdb_id"].isin(allowed_tmdb_ids)]
            if recs.empty:
                continue

        # Öneri listesindeki film ID'leri
        rec_ids = set(recs["tmdb_id"].tolist())
        
        # Her gizlenen film için hit kontrolü
        user_hits = 0
        hit_details = []
        for i, (hidden_movie, hidden_rating) in enumerate(zip(hidden_movies, hidden_ratings_list)):
            try:
                rank = recs["tmdb_id"].tolist().index(hidden_movie) + 1
                hit = rank <= top_n
            except ValueError:
                rank = None
                hit = False
            
            if hit:
                user_hits += 1
                total_hits += 1
            
            detail = {
                "tmdb_id": hidden_movie,
                "title": title_lookup.get(hidden_movie, "Unknown"),
                "rating": hidden_rating,
                "hit": hit,
                "rank": rank,
            }
            if hidden_similarities:
                detail["similarity_to_remaining"] = round(hidden_similarities[i], 3)
            hit_details.append(detail)
        
        total_hidden += len(hidden_movies)
        tested_users += 1
        
        # Kullanıcı en az 1 film buldu mu?
        if user_hits > 0:
            users_with_hit += 1
        
        if hidden_similarities:
            avg_hide_similarities.append(sum(hidden_similarities) / len(hidden_similarities))
        
        # Kullanıcı bazlı Recall@N: gizlenenlerden kaçı Top-N'de
        user_recall = user_hits / len(hidden_movies)
        user_recalls.append(user_recall)
        
        # Kullanıcı bazlı Precision@N: Top-N'den kaçı gizlenenlerden
        precision_hits = len(hidden_set & rec_ids)
        user_precision = precision_hits / min(top_n, len(recs)) if len(recs) > 0 else 0.0
        user_precisions.append(user_precision)
        
        # Örnek kaydet
        if len(samples) < 15:
            samples.append({
                "userId": int(user_id),
                "n_hidden": len(hidden_movies),
                "hits": user_hits,
                "recall": round(user_recall, 3),
                "hidden_movies": hit_details,
            })

        if tested_users >= n_users:
            break

    # Ortalama metrikler
    hit_rate_film = total_hits / total_hidden if total_hidden > 0 else 0.0  # Film bazlı
    hit_rate_user = users_with_hit / tested_users if tested_users > 0 else 0.0  # Kullanıcı bazlı (klasik)
    avg_recall = sum(user_recalls) / len(user_recalls) if user_recalls else 0.0
    avg_precision = sum(user_precisions) / len(user_precisions) if user_precisions else 0.0
    avg_hide_sim = sum(avg_hide_similarities) / len(avg_hide_similarities) if avg_hide_similarities else 0.0
    
    return {
        "hit_rate": hit_rate_film,  # Eski uyumluluk için (film bazlı)
        "hit_rate_user": hit_rate_user,  # Kullanıcı bazlı (klasik)
        "users_with_hit": users_with_hit,  # En az 1 hit alan kullanıcı
        "hits": total_hits,
        "total_hidden": total_hidden,
        "tested": tested_users,
        "n_hidden": n_hidden,
        "avg_recall": avg_recall,
        "avg_precision": avg_precision,
        "smart_hide": smart_hide,
        "min_hide_similarity": min_hide_similarity,
        "avg_hide_similarity": avg_hide_sim,
        "skipped_no_similar": skipped_no_similar,
        "samples": samples,
    }


# Eski API uyumluluğu için wrapper (n_hidden=1 varsayılan)
def evaluate_legacy(
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
    restrict_to_links: bool = False,
) -> dict:
    """Eski API uyumluluğu için leave-one-out değerlendirmesi."""
    result = evaluate(
        ratings_path,
        links_path,
        n_users=n_users,
        top_n=top_n,
        mode=mode,
        rating_threshold=rating_threshold,
        min_liked=min_liked,
        method=method,
        seed=seed,
        restrict_to_links=restrict_to_links,
        n_hidden=1,
    )
    
    # Eski format için samples'ı dönüştür
    old_samples = []
    for sample in result.get("samples", []):
        if sample.get("hidden_movies"):
            hm = sample["hidden_movies"][0]
            old_samples.append({
                "userId": sample["userId"],
                "hidden_tmdb": hm["tmdb_id"],
                "hidden_title": hm["title"],
                "hit": hm["hit"],
                "rank": hm["rank"],
                "hidden_rating": hm["rating"],
            })
    
    return {
        "hit_rate": result["hit_rate"],
        "hits": result["hits"],
        "tested": result["tested"],
        "samples": old_samples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Content-Based HitRate@N değerlendirmesi")
    parser.add_argument("--ratings", type=Path, default=DEFAULT_RATINGS, help="ratings.csv yolu")
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS, help="links.csv yolu")
    parser.add_argument("--n-users", type=int, default=50, help="Kaç kullanıcı test edilecek")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--mode", choices=("standard", "profile"), default="standard")
    parser.add_argument("--rating-threshold", type=float, default=4.0)
    parser.add_argument("--min-liked", type=int, default=5, help="Min. beğenilen film (n_hidden için yeterli olmalı)")
    parser.add_argument(
        "--method",
        choices=("score_avg", "vector_avg"),
        default="score_avg",
        help="Standart mod için çoklu film yöntemi",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--restrict-to-links",
        action="store_true",
        help="Önerileri links_small.csv içindeki TMDB kimlikleriyle sınırlar.",
    )
    parser.add_argument(
        "--n-hidden",
        type=int,
        default=1,
        help="Kaç film gizlenecek (Leave-K-Out). 1=klasik, 2+=çoklu gizleme",
    )
    parser.add_argument(
        "--no-smart-hide",
        action="store_true",
        help="Akıllı gizlemeyi kapat (rastgele gizle)",
    )
    parser.add_argument(
        "--min-hide-sim",
        type=float,
        default=0.05,
        help="Akıllı gizleme için minimum benzerlik eşiği (varsayılan: 0.05)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    smart_hide = not args.no_smart_hide
    
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
        restrict_to_links=args.restrict_to_links,
        n_hidden=args.n_hidden,
        smart_hide=smart_hide,
        min_hide_similarity=args.min_hide_sim,
    )
    
    n_hidden = result.get("n_hidden", 1)
    total_hidden = result.get("total_hidden", result["hits"])
    
    print("\n" + "=" * 60)
    print("📊 CONTENT-BASED MODEL DEĞERLENDİRME SONUÇLARI")
    print("=" * 60)
    
    if result.get("smart_hide"):
        print(f"\n🧠 Akıllı Gizleme AÇIK (min_similarity={result.get('min_hide_similarity', 0.05):.2f})")
        print(f"   • Ortalama gizlenen film benzerliği: {result.get('avg_hide_similarity', 0):.3f}")
        if result.get("skipped_no_similar", 0) > 0:
            print(f"   • Benzer film bulunamayan kullanıcı: {result['skipped_no_similar']}")
    
    if n_hidden == 1:
        print(f"\n🎯 HitRate@{args.top_n}: {result['hit_rate']:.3f} ({result['hits']}/{result['tested']} kullanıcı)")
    else:
        print(f"\n🎯 Leave-{n_hidden}-Out Değerlendirmesi")
        print(f"   • Gizlenen film sayısı (per user): {n_hidden}")
        print(f"   • Toplam gizlenen film: {total_hidden}")
        print(f"   • Toplam hit: {result['hits']}")
        print(f"   • Test edilen kullanıcı: {result['tested']}")
        print(f"\n📈 Metrikler:")
        print(f"   • HitRate (hits/total_hidden): {result['hit_rate']:.3f} ({result['hit_rate']*100:.1f}%)")
        print(f"   • Avg Recall@{args.top_n}: {result.get('avg_recall', 0):.3f} ({result.get('avg_recall', 0)*100:.1f}%)")
        print(f"   • Avg Precision@{args.top_n}: {result.get('avg_precision', 0):.3f}")
    
    print(f"\n⚙️  Parametreler:")
    print(f"   • mode: {args.mode}")
    print(f"   • method: {args.method}")
    print(f"   • rating_threshold: {args.rating_threshold}")
    print(f"   • min_liked: {args.min_liked}")
    print(f"   • smart_hide: {smart_hide}")
    
    if result.get("samples"):
        print(f"\n👥 Örnek Kullanıcılar ({len(result['samples'])} adet):")
        print("-" * 60)
        
        for sample in result["samples"][:10]:
            user_id = sample["userId"]
            n_hid = sample.get("n_hidden", 1)
            hits = sample.get("hits", 0)
            recall = sample.get("recall", 0)
            
            if n_hidden == 1 and sample.get("hidden_movies"):
                # Tek film gizleme
                hm = sample["hidden_movies"][0]
                hit_flag = "✅" if hm["hit"] else "❌"
                rank = hm["rank"] if hm["rank"] is not None else "-"
                sim_info = f" (sim={hm.get('similarity_to_remaining', '?')})" if result.get("smart_hide") else ""
                print(f" {hit_flag} user={user_id:5d} | '{hm['title'][:28]:<28}' | rank={rank}{sim_info}")
            else:
                # Çoklu film gizleme
                hit_flag = "✅" if hits > 0 else "❌"
                print(f" {hit_flag} user={user_id:5d} | hits={hits}/{n_hid} | recall={recall:.2f}")
                if sample.get("hidden_movies"):
                    for hm in sample["hidden_movies"]:
                        sub_flag = "  ✓" if hm["hit"] else "  ✗"
                        rank = hm["rank"] if hm["rank"] is not None else "-"
                        sim_info = f" sim={hm.get('similarity_to_remaining', '?')}" if result.get("smart_hide") else ""
                        print(f"    {sub_flag} '{hm['title'][:32]:<32}' rank={rank}{sim_info}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

