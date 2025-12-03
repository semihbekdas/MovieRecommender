"""
HitRate düşük olmasının nedenlerini analiz eden diagnostik script.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

import recommender_content as rc
import evaluate_content as ec


def diagnose():
    print("=" * 70)
    print("🔍 HIT RATE DİAGNOSTİK ANALİZİ")
    print("=" * 70)
    
    # 1. Veri yükleme
    print("\n📂 1. VERİ YÜKLEME")
    print("-" * 50)
    
    ratings_df = ec.load_ratings(DATA_DIR / "ratings.csv")
    links_df = ec.load_links(DATA_DIR / "links.csv")
    bundle = rc.load_artifacts()
    
    print(f"   • Ratings satır sayısı: {len(ratings_df):,}")
    print(f"   • Benzersiz kullanıcı: {ratings_df['userId'].nunique():,}")
    print(f"   • Benzersiz movieId: {ratings_df['movieId'].nunique():,}")
    print(f"   • Links satır sayısı: {len(links_df):,}")
    print(f"   • Content-Based model film sayısı: {len(bundle.metadata):,}")
    
    # 2. ID eşleşme analizi
    print("\n🔗 2. ID EŞLEŞMESİ ANALİZİ")
    print("-" * 50)
    
    movie_map = ec.build_movieid_to_tmdb(links_df)
    ratings_movie_ids = set(ratings_df['movieId'].unique())
    links_movie_ids = set(links_df['movieId'].unique())
    tmdb_ids_in_model = set(bundle.metadata['tmdb_id'].unique())
    
    # MovieLens ID'lerinden kaçı links'te var?
    matched_to_links = ratings_movie_ids & links_movie_ids
    print(f"   • Ratings'teki movieId sayısı: {len(ratings_movie_ids):,}")
    print(f"   • Links'te eşleşen movieId: {len(matched_to_links):,} ({len(matched_to_links)/len(ratings_movie_ids)*100:.1f}%)")
    
    # Links'teki tmdb_id'lerden kaçı modelde var?
    tmdb_ids_in_links = set(links_df['tmdbId'].dropna().astype(int).unique())
    matched_to_model = tmdb_ids_in_links & tmdb_ids_in_model
    print(f"   • Links'teki tmdbId sayısı: {len(tmdb_ids_in_links):,}")
    print(f"   • Content-Based modelde olan: {len(matched_to_model):,} ({len(matched_to_model)/len(tmdb_ids_in_links)*100:.1f}%)")
    
    # 3. Kullanıcı bazlı analiz
    print("\n👥 3. KULLANICI BAZLI ANALİZ")
    print("-" * 50)
    
    rating_threshold = 4.0
    liked_ratings = ratings_df[ratings_df['rating'] >= rating_threshold]
    
    # Her kullanıcının kaç beğenisi modelde var?
    users_with_model_coverage = []
    
    for user_id in liked_ratings['userId'].unique()[:500]:  # İlk 500 kullanıcı
        user_likes = liked_ratings[liked_ratings['userId'] == user_id]
        
        model_matched = 0
        for _, row in user_likes.iterrows():
            tmdb_id = movie_map.get(int(row['movieId']))
            if tmdb_id and tmdb_id in bundle.id_to_index:
                model_matched += 1
        
        if len(user_likes) > 0:
            coverage = model_matched / len(user_likes)
            users_with_model_coverage.append({
                'userId': user_id,
                'total_likes': len(user_likes),
                'in_model': model_matched,
                'coverage': coverage
            })
    
    coverage_df = pd.DataFrame(users_with_model_coverage)
    print(f"   • Ortalama kullanıcı kapsamı (coverage): {coverage_df['coverage'].mean()*100:.1f}%")
    print(f"   • Medyan kullanıcı kapsamı: {coverage_df['coverage'].median()*100:.1f}%")
    print(f"   • Min kapsamı: {coverage_df['coverage'].min()*100:.1f}%")
    print(f"   • Max kapsamı: {coverage_df['coverage'].max()*100:.1f}%")
    
    # Kapsamı düşük kullanıcılar
    low_coverage = coverage_df[coverage_df['coverage'] < 0.3]
    print(f"   • Kapsamı %30'un altında olan kullanıcı: {len(low_coverage)} ({len(low_coverage)/len(coverage_df)*100:.1f}%)")
    
    # 4. Content-Based benzerlik analizi
    print("\n📊 4. CONTENT-BASED BENZERLİK ANALİZİ")
    print("-" * 50)
    
    # Rastgele bir kullanıcının beğendiği filmler arasındaki benzerlik
    sample_user = coverage_df[coverage_df['in_model'] >= 5].iloc[0]['userId']
    user_likes = liked_ratings[liked_ratings['userId'] == sample_user]
    
    user_tmdb_ids = []
    for _, row in user_likes.iterrows():
        tmdb_id = movie_map.get(int(row['movieId']))
        if tmdb_id and tmdb_id in bundle.id_to_index:
            user_tmdb_ids.append(tmdb_id)
    
    if len(user_tmdb_ids) >= 3:
        # Film çiftleri arasındaki benzerliği hesapla
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarities = []
        for i, id1 in enumerate(user_tmdb_ids[:10]):
            for id2 in user_tmdb_ids[i+1:10]:
                idx1 = bundle.id_to_index.get(id1)
                idx2 = bundle.id_to_index.get(id2)
                if idx1 is not None and idx2 is not None:
                    sim = cosine_similarity(
                        bundle.matrix[idx1], 
                        bundle.matrix[idx2]
                    )[0][0]
                    similarities.append(sim)
        
        if similarities:
            print(f"   • Örnek kullanıcı #{sample_user} ({len(user_tmdb_ids)} film)")
            print(f"   • Beğenilen filmler arası ortalama benzerlik: {np.mean(similarities):.3f}")
            print(f"   • Beğenilen filmler arası max benzerlik: {np.max(similarities):.3f}")
            print(f"   • Beğenilen filmler arası min benzerlik: {np.min(similarities):.3f}")
            
            if np.mean(similarities) < 0.2:
                print("   ⚠️  DÜŞÜK BENZERLİK: Kullanıcının beğendiği filmler birbirine benzemiyor!")
                print("      Bu, content-based sistemin doğal sınırlamasıdır.")
    
    # 5. Temel problem tespiti
    print("\n🎯 5. TEMEL PROBLEM TESPİTİ")
    print("-" * 50)
    
    problems = []
    
    # Problem 1: Düşük katalog örtüşmesi
    model_coverage = len(matched_to_model) / len(tmdb_ids_in_links) * 100
    if model_coverage < 80:
        problems.append(f"❌ Katalog örtüşmesi düşük ({model_coverage:.1f}%)")
    else:
        print(f"   ✅ Katalog örtüşmesi iyi ({model_coverage:.1f}%)")
    
    # Problem 2: Düşük kullanıcı kapsamı
    avg_coverage = coverage_df['coverage'].mean() * 100
    if avg_coverage < 50:
        problems.append(f"❌ Kullanıcı film kapsamı düşük ({avg_coverage:.1f}%)")
    else:
        print(f"   ✅ Kullanıcı film kapsamı yeterli ({avg_coverage:.1f}%)")
    
    # Problem 3: Content-based sınırlaması
    if similarities and np.mean(similarities) < 0.15:
        problems.append("❌ Content-based benzerlik çok düşük (filmler içerik olarak farklı)")
    
    if problems:
        print("\n   🚨 TESPİT EDİLEN PROBLEMLER:")
        for p in problems:
            print(f"      {p}")
    
    # 6. Öneriler
    print("\n💡 6. İYİLEŞTİRME ÖNERİLERİ")
    print("-" * 50)
    
    print("""
   1. DAHA GENIŞ TOP-N KULLANIN:
      • top_n=10 yerine top_n=20 veya 30 deneyin
      • Content-based sistemler için %20-30 hit rate normaldir
   
   2. RESTRICT_TO_LINKS'İ KAPATIN:
      • MovieLens filtresi aktifse, öneri havuzu daralır
      • Bu filtreyi kapatmak hit rate'i artırabilir
   
   3. METHOD DEĞİŞTİRİN:
      • "score_avg" yerine "vector_avg" deneyin
      • Veya "profile" modunu kullanın
   
   4. RATING THRESHOLD'U DÜŞÜRÜn:
      • 4.0 yerine 3.5 deneyin
      • Daha fazla film = daha iyi profil
   
   5. BU NORMALDİR:
      • Content-based sistemler collaborative filtering kadar
        yüksek hit rate vermez
      • %15-30 arası hit rate content-based için kabul edilebilir
      • Çünkü kullanıcılar her zaman "benzer içerikli" filmler sevmez
    """)
    
    print("=" * 70)


if __name__ == "__main__":
    diagnose()

