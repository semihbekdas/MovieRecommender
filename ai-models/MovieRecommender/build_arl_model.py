#!/usr/bin/env python3
"""
ARL Model Builder - CLI Tool
Büyük veya küçük dataset ile model oluşturmak için kullanılır.

Kullanım:
    python build_arl_model.py --dataset small
    python build_arl_model.py --dataset full --min-support 0.005 --min-lift 2.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Import from existing recommender_arl module
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import recommender_arl as arl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ARL Model Builder - Film öneri modeli oluşturucu",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["small", "full"],
        default="small",
        help="Kullanılacak dataset (small=ratings_small.csv, full=ratings.csv)"
    )
    
    parser.add_argument(
        "--min-rating",
        type=float,
        default=4.0,
        help="Minimum beğeni puanı (4.0 önerilir)"
    )
    
    parser.add_argument(
        "--min-support",
        type=float,
        default=None,
        help="Minimum support (None=otomatik seçim: small=0.015, full=0.005)"
    )
    
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help="Minimum confidence (None=otomatik: small=0.3, full=0.4)"
    )
    
    parser.add_argument(
        "--min-lift",
        type=float,
        default=None,
        help="Minimum lift (None=otomatik: small=1.0, full=2.0)"
    )
    
    parser.add_argument(
        "--min-movie-likes",
        type=int,
        default=None,
        help="Minimum film beğeni sayısı (None=otomatik: small=10, full=100)"
    )
    
    parser.add_argument(
        "--max-len",
        type=int,
        default=2,
        help="Maximum itemset uzunluğu (2 önerilir)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Model dosyalarının kaydedileceği klasör (None=models/)"
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Dataset seçimi
    if args.dataset == "small":
        csv_file = "ratings_small.csv"
        # Small dataset için optimize edilmiş parametreler
        min_support = args.min_support or 0.015
        min_confidence = args.min_confidence or 0.3
        min_lift = args.min_lift or 1.0
        min_movie_likes = args.min_movie_likes or 10
    else:  # full
        csv_file = "ratings.csv"
        # Full dataset için agresif filtreleme
        min_support = args.min_support or 0.005
        min_confidence = args.min_confidence or 0.4
        min_lift = args.min_lift or 2.0
        min_movie_likes = args.min_movie_likes or 100
    
    print(f"\n{'='*70}")
    print(f"📊 DATASET: {args.dataset.upper()} ({csv_file})")
    print(f"{'='*70}")
    print(f"Parametreler:")
    print(f"  • min_rating: {args.min_rating}")
    print(f"  • min_support: {min_support}")
    print(f"  • min_confidence: {min_confidence}")
    print(f"  • min_lift: {min_lift}")
    print(f"  • min_movie_likes: {min_movie_likes}")
    print(f"  • max_len: {args.max_len}")
    print(f"{'='*70}\n")
    
    # RAW_DATA_DIR'i modifiye etme (geçici override)
    original_raw_dir = arl.RAW_DATA_DIR
    
    # Output directory ayarla
    if args.output_dir:
        output_models_dir = args.output_dir
        output_models_dir.mkdir(parents=True, exist_ok=True)
        mapping_path = output_models_dir / "movie_mapping.pkl"
        rules_path = output_models_dir / "association_rules.pkl"
        meta_path = output_models_dir / "artifacts_meta.json"
    else:
        mapping_path = arl.MAPPING_PATH
        rules_path = arl.RULES_PATH
        meta_path = arl.ARTIFACT_METADATA_PATH
    
    try:
        # CSV dosyasını ratings.csv veya ratings_small.csv'ye yönlendir
        # Bunu yapmak için load_raw_data'nın içindeki dosya ismini değiştirmemiz gerekiyor
        # Ama daha kolay yolu: ratings_small.csv'yi geçici olarak ratings.csv'ye symlink yapmak
        # Ya da daha iyisi: recommender_arl.py'daki load_raw_data'yı değiştirmeden kullanmak
        
        # En temiz yol: Doğrudan parametrelerle çağırmak
        # Ama load_raw_data içinde hardcoded "ratings_small.csv" var
        # O yüzden geçici bir çözüm: dosyayı oku, sonra prepare_and_save_artifacts'e ver
        
        print("⚠️ DİKKAT: Büyük dataset ile çalışıyorsanız, bu işlem 1-2 saat sürebilir!\n")
        
        # Veriyi yükle
        print(f"📂 Veri yükleniyor: {csv_file}...")
        import pandas as pd
        ratings_path = arl.RAW_DATA_DIR / csv_file
        
        if not ratings_path.exists():
            print(f"❌ HATA: {ratings_path} dosyası bulunamadı!")
            sys.exit(1)
        
        # Custom load fonksiyonu
        ratings = pd.read_csv(
            ratings_path,
            dtype={"userId": "int64", "movieId": "int64", "rating": "float64", "timestamp": "int64"},
            usecols=["userId", "movieId", "rating", "timestamp"],
        )
        print(f"✅ {len(ratings):,} rating yüklendi\n")
        
        # Links ve metadata normal şekilde yükle
        links, metadata = arl.load_raw_data(original_raw_dir)[1:]
        
        # Mapping oluştur
        print("🗺️  Film mapping oluşturuluyor...")
        mapping_df = arl.build_movie_mapping(links, metadata)
        arl.save_movie_mapping(mapping_df, mapping_path)
        print(f"✅ {len(mapping_df):,} film eşleştirildi\n")
        
        # Like filtreleme
        print(f"⭐ Beğenilen filmler filtreleniyor (rating >= {args.min_rating})...")
        liked = arl.filter_liked_ratings(ratings, min_rating=args.min_rating)
        print(f"✅ {len(liked):,} beğeni bulundu\n")
        
        # Nadir filmleri eleme
        print(f"🎯 Az izlenen filmler eleniyor (min_likes >= {min_movie_likes})...")
        liked = arl.filter_infrequent_movies(liked, min_likes=min_movie_likes)
        print(f"✅ {liked['movieId'].nunique():,} film kaldı\n")
        
        # Matrix ve kurallar
        print("📊 User-Movie matrix ve association rules oluşturuluyor...")
        basket_df = arl.build_user_movie_matrix(liked)
        print(f"ℹ️  Matrix boyutu: {basket_df.shape[0]:,} kullanıcı × {basket_df.shape[1]:,} film")
        
        if args.dataset == "full":
            print(f"⏱️  Bu işlem 1-2 saat sürebilir, lütfen bekleyin...\n")
        
        rules_df = arl.generate_association_rules(
            basket_df,
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            max_len=args.max_len,
        )
        
        if rules_df.empty:
            print("⚠️ Hiç kural üretilemedi! Parametreleri düşürün.")
            sys.exit(1)
        
        arl.save_association_rules(rules_df, rules_path)
        print(f"✅ {len(rules_df):,} kural oluşturuldu ve kaydedildi\n")
        
        # Metadata kaydet
        metadata_dict = {
            "dataset": args.dataset,
            "csv_file": csv_file,
            "min_rating_for_like": float(args.min_rating),
            "min_support": float(min_support),
            "min_confidence": float(min_confidence),
            "min_lift": float(min_lift),
            "min_movie_likes": int(min_movie_likes),
            "max_len": int(args.max_len),
        }
        arl.save_artifact_metadata(metadata_dict, meta_path)
        
        print(f"\n{'='*70}")
        print("🎉 MODEL BAŞARIYLA OLUŞTURULDU!")
        print(f"{'='*70}")
        print(f"📁 Dosyalar:")
        print(f"  • {mapping_path}")
        print(f"  • {rules_path}")
        print(f"  • {meta_path}")
        print(f"{'='*70}\n")
        
        # Test önerisi
        print("🧪 Test önerisi yapılıyor...")
        sample_likes = ["Inception", "Interstellar", "The Dark Knight"]
        recs, missing = arl.recommend_with_association_rules(
            sample_likes, top_n=10,
            mapping_path=mapping_path,
            rules_path=rules_path
        )
        
        if missing:
            print(f"⚠️  Bulunamayan filmler: {', '.join(missing)}")
        
        if not recs.empty:
            print("\n📋 Top 10 Öneriler:")
            print(recs[["title", "score", "confidence", "lift"]].to_string(index=False))
        else:
            print("⚠️ Öneri bulunamadı")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ İşlem kullanıcı tarafından iptal edildi!")
        sys.exit(130)
    except Exception as exc:
        print(f"\n❌ HATA: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
