#!/usr/bin/env python3
"""
🎬 Film Öneri Sistemi - Demo Script

Bu script, eğitilmiş Association Rules modelini kullanarak
film önerileri nasıl alınır gösterir.

Kullanım:
    python demo_recommendation.py              # Normal demo
    python demo_recommendation.py --interactive  # İnteraktif mod
    python demo_recommendation.py --json        # JSON API örneği
"""

import json

import pickle
from pathlib import Path


# ==============================================
# 📁 Model Dosyalarını Yükle
# ==============================================

# Proje klasörü
PROJECT_DIR = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_DIR / "models"

# Modellerin yolları
MAPPING_PATH = MODELS_DIR / "movie_mapping.pkl"
RULES_PATH = MODELS_DIR / "association_rules.pkl"


def load_models():
    """Kaydedilmiş modelleri yükler."""
    print("📂 Modeller yükleniyor...")
    
    # Film mapping yükle (movieId -> title eşlemesi)
    with open(MAPPING_PATH, "rb") as f:
        movie_mapping = pickle.load(f)
    print(f"   ✅ movie_mapping.pkl yüklendi: {len(movie_mapping)} film")
    
    # Association rules yükle
    with open(RULES_PATH, "rb") as f:
        rules = pickle.load(f)
    print(f"   ✅ association_rules.pkl yüklendi: {len(rules)} kural")
    
    return movie_mapping, rules


def search_movie(movie_mapping, query):
    """Film adı arar, benzer sonuçları döndürür."""
    query = query.lower().strip()
    matches = movie_mapping[
        movie_mapping["title"].str.lower().str.contains(query, na=False)
    ]
    return matches[["movieId", "title"]].head(10)


def title_to_movie_id(movie_mapping, title):
    """Film adından movieId bulur (case-insensitive)."""
    title_lower = title.lower().strip()
    match = movie_mapping[movie_mapping["title"].str.lower() == title_lower]
    if match.empty:
        return None
    return int(match.iloc[0]["movieId"])


def get_recommendations(movie_mapping, rules, liked_titles, top_n=10):
    """
    Verilen film listesine göre öneri üretir.
    
    Parameters
    ----------
    movie_mapping : pd.DataFrame
        Film ID -> isim eşlemesi
    rules : pd.DataFrame
        Association rules tablosu
    liked_titles : list[str]
        Beğenilen film adları
    top_n : int
        Döndürülecek öneri sayısı
        
    Returns
    -------
    list[dict]
        Öneri listesi (title, score, confidence, lift)
    """
    # Film adlarını ID'lere çevir
    liked_ids = []
    missing_titles = []
    
    for title in liked_titles:
        movie_id = title_to_movie_id(movie_mapping, title)
        if movie_id:
            liked_ids.append(movie_id)
        else:
            missing_titles.append(title)
    
    if missing_titles:
        print(f"⚠️  Bulunamayan filmler: {', '.join(missing_titles)}")
    
    if not liked_ids:
        print("❌ Hiç film bulunamadı!")
        return []
    
    liked_set = set(liked_ids)
    
    # Antecedents'ı liked_set'in alt kümesi olan kuralları bul
    matching_rules = rules[
        rules["antecedents"].apply(lambda x: bool(x) and x.issubset(liked_set))
    ]
    
    if matching_rules.empty:
        print("❌ Bu filmler için kural bulunamadı. Başka filmler deneyin.")
        return []
    
    # Önerileri topla
    suggestions = {}
    for _, row in matching_rules.iterrows():
        for movie_id in row["consequents"]:
            if movie_id in liked_set:
                continue  # Zaten beğenilen filmleri atla
            
            # En iyi skoru tut
            current = suggestions.get(movie_id, {})
            score = row.get("score", row["confidence"] * row["lift"])
            
            if score > current.get("score", 0):
                suggestions[movie_id] = {
                    "movieId": movie_id,
                    "score": score,
                    "confidence": row["confidence"],
                    "lift": row["lift"],
                    "support": row["support"],
                }
    
    # Skorlara göre sırala
    sorted_suggestions = sorted(
        suggestions.values(), 
        key=lambda x: (x["score"], x["confidence"], x["lift"]), 
        reverse=True
    )[:top_n]
    
    # Film adlarını ekle
    id_to_title = dict(zip(movie_mapping["movieId"], movie_mapping["title"]))
    for s in sorted_suggestions:
        s["title"] = id_to_title.get(s["movieId"], f"Film #{s['movieId']}")
    
    return sorted_suggestions


def get_recommendations_json(movie_mapping, rules, request_json):
    """
    JSON formatında öneri üretir - WEB API için örnek.
    
    Input JSON:
        {"liked_movies": ["Inception", "Matrix"], "top_n": 10}
    
    Output JSON:
        {"success": true, "recommendations": [...], ...}
    """
    # JSON parse (string ise)
    if isinstance(request_json, str):
        request_data = json.loads(request_json)
    else:
        request_data = request_json
    
    liked_movies = request_data.get("liked_movies", [])
    top_n = request_data.get("top_n", 10)
    
    # Öneri al
    recs = get_recommendations(movie_mapping, rules, liked_movies, top_n)
    
    # Missing filmleri bul
    missing = []
    for title in liked_movies:
        if not title_to_movie_id(movie_mapping, title):
            missing.append(title)
    
    # Response JSON oluştur
    response = {
        "success": True,
        "model": "association_rules",
        "input": {
            "liked_movies": liked_movies,
            "top_n": top_n
        },
        "recommendations": recs,
        "missing_movies": missing,
        "recommendation_count": len(recs)
    }
    
    return response


def json_api_demo(movie_mapping, rules):
    """JSON API kullanım örneklerini gösterir."""
    print("\n" + "="*60)
    print("🌐 JSON API DEMO - Web Geliştiricisi için")
    print("="*60)
    
    # Örnek 1: Tek film
    print("\n📤 ÖRNEK 1: Tek Film ile İstek")
    print("-"*40)
    
    request1 = {
        "liked_movies": ["Inception"],
        "top_n": 5
    }
    print("REQUEST JSON:")
    print(json.dumps(request1, indent=2, ensure_ascii=False))
    
    response1 = get_recommendations_json(movie_mapping, rules, request1)
    print("\nRESPONSE JSON:")
    print(json.dumps(response1, indent=2, ensure_ascii=False))
    
    # Örnek 2: Çoklu film
    print("\n\n" + "-"*60)
    print("\n📤 ÖRNEK 2: Birden Fazla Film ile İstek")
    print("-"*40)
    
    request2 = {
        "liked_movies": ["The Matrix", "Blade Runner", "Alien"],
        "top_n": 5
    }
    print("REQUEST JSON:")
    print(json.dumps(request2, indent=2, ensure_ascii=False))
    
    response2 = get_recommendations_json(movie_mapping, rules, request2)
    print("\nRESPONSE JSON:")
    print(json.dumps(response2, indent=2, ensure_ascii=False))
    
    # Örnek 3: Bulunamayan film ile
    print("\n\n" + "-"*60)
    print("\n📤 ÖRNEK 3: Bulunamayan Film ile İstek")
    print("-"*40)
    
    request3 = {
        "liked_movies": ["Inception", "BuFilmYok123"],
        "top_n": 3
    }
    print("REQUEST JSON:")
    print(json.dumps(request3, indent=2, ensure_ascii=False))
    
    response3 = get_recommendations_json(movie_mapping, rules, request3)
    print("\nRESPONSE JSON:")
    print(json.dumps(response3, indent=2, ensure_ascii=False))
    
    # Kullanım kodu örneği
    print("\n\n" + "="*60)
    print("💻 PYTHON KULLANIM ÖRNEĞİ")
    print("="*60)
    print('''
# Flask/FastAPI endpoint örneği:

@app.post("/api/recommend/arl")
def recommend_arl(request: dict):
    response = get_recommendations_json(
        movie_mapping, 
        rules, 
        request
    )
    return response

# Frontend'den çağırma (JavaScript):

fetch('/api/recommend/arl', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        liked_movies: ["Inception", "The Matrix"],
        top_n: 10
    })
})
.then(res => res.json())
.then(data => console.log(data.recommendations));
''')
    print("="*60 + "\n")
    
    # İnteraktif JSON girişi
    print("\n" + "="*60)
    print("🎯 KENDİ JSON'UNUZU GİRİN")
    print("="*60)
    print("Örnek format: {\"liked_movies\": [\"Inception\", \"Matrix\"], \"top_n\": 5}")
    print("Çıkmak için 'q' yazın\n")
    
    while True:
        try:
            user_input = input("📝 JSON girin: ").strip()
        except EOFError:
            break
        
        if not user_input or user_input.lower() == 'q':
            print("👋 Çıkış!")
            break
        
        try:
            response = get_recommendations_json(movie_mapping, rules, user_input)
            print("\n📥 RESPONSE:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            print()
        except json.JSONDecodeError as e:
            print(f"❌ JSON hatası: {e}")
        except Exception as e:
            print(f"❌ Hata: {e}")


def print_recommendations(recommendations):
    """Önerileri güzel formatta yazdırır."""
    if not recommendations:
        return
    
    print("\n" + "="*60)
    print("🎬 ÖNERİLEN FİLMLER")
    print("="*60)
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   📊 Skor: {rec['score']:.3f}")
        print(f"   🎯 Güven: {rec['confidence']:.1%}")
        print(f"   📈 Lift: {rec['lift']:.2f}")


def interactive_mode(movie_mapping, rules):
    """Interaktif öneri modu."""
    print("\n" + "="*60)
    print("🎬 İNTERAKTİF FİLM ÖNERİ SİSTEMİ")
    print("="*60)
    print("Film adı yazın ve öneriler alın!")
    print("Komutlar:")
    print("  - 'ara:film adı' → Film arar")
    print("  - 'çık' → Çıkış")
    print("="*60)
    
    liked_films = []
    
    while True:
        try:
            user_input = input("\n🎥 Film adı girin (veya 'öneri' yazın): ").strip()
        except EOFError:
            break
            
        if not user_input:
            continue
            
        if user_input.lower() == "çık":
            print("👋 Görüşmek üzere!")
            break
        
        if user_input.lower().startswith("ara:"):
            query = user_input[4:].strip()
            results = search_movie(movie_mapping, query)
            if results.empty:
                print("❌ Film bulunamadı.")
            else:
                print("\n📋 Bulunan filmler:")
                for _, row in results.iterrows():
                    print(f"   • {row['title']}")
            continue
        
        if user_input.lower() == "öneri":
            if not liked_films:
                print("⚠️  Önce en az bir film ekleyin!")
                continue
            
            print(f"\n🎬 Seçtiğiniz filmler: {', '.join(liked_films)}")
            recs = get_recommendations(movie_mapping, rules, liked_films, top_n=10)
            print_recommendations(recs)
            continue
        
        if user_input.lower() == "sıfırla":
            liked_films = []
            print("✅ Film listesi sıfırlandı.")
            continue
        
        # Film ekleme
        movie_id = title_to_movie_id(movie_mapping, user_input)
        if movie_id:
            liked_films.append(user_input)
            print(f"✅ '{user_input}' eklendi. Toplam: {len(liked_films)} film")
            print(f"   📝 Liste: {', '.join(liked_films)}")
        else:
            # Benzer filmleri öner
            results = search_movie(movie_mapping, user_input)
            if results.empty:
                print("❌ Film bulunamadı.")
            else:
                print("❌ Tam eşleşme bulunamadı. Şunları mı demek istediniz?")
                for _, row in results.head(5).iterrows():
                    print(f"   • {row['title']}")


def main():
    """Ana demo fonksiyonu."""
    import sys
    
    print("\n" + "="*60)
    print("🎬 ASSOCIATION RULES FİLM ÖNERİ SİSTEMİ")
    print("="*60 + "\n")
    
    # Modelleri yükle
    movie_mapping, rules = load_models()
    
    # Mode kontrolü
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            interactive_mode(movie_mapping, rules)
            return
        elif sys.argv[1] == "--json":
            json_api_demo(movie_mapping, rules)
            return
    
    # ========================================
    # 🎯 DEMO: Örnek Öneri Al
    # ========================================
    
    print("\n" + "-"*60)
    print("📽️  DEMO: Film Önerileri")
    print("-"*60)
    
    # Örnek 1: Christopher Nolan filmleri
    print("\n🎬 Örnek 1: Christopher Nolan Filmleri")
    liked = ["Inception", "Interstellar", "The Dark Knight"]
    print(f"   Beğenilen: {', '.join(liked)}")
    
    recs = get_recommendations(movie_mapping, rules, liked, top_n=5)
    print_recommendations(recs)
    
    # Örnek 2: Sci-Fi filmleri
    print("\n\n" + "-"*60)
    print("\n🎬 Örnek 2: Sci-Fi Klasikleri")
    liked = ["The Matrix", "Blade Runner"]
    print(f"   Beğenilen: {', '.join(liked)}")
    
    recs = get_recommendations(movie_mapping, rules, liked, top_n=5)
    print_recommendations(recs)
    
    # Örnek 3: Tek film
    print("\n\n" + "-"*60)
    print("\n🎬 Örnek 3: Tek Film ile Öneri")
    liked = ["Pulp Fiction"]
    print(f"   Beğenilen: {', '.join(liked)}")
    
    recs = get_recommendations(movie_mapping, rules, liked, top_n=5)
    print_recommendations(recs)
    
    print("\n" + "="*60)
    print("🎉 Demo tamamlandı!")
    print("💡 İpucu: --interactive ile interaktif mod kullanabilirsiniz")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
