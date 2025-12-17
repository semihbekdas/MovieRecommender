from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import pandas as pd
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent

# Add Content-Based folder to path
CONTENT_BASED_DIR = PROJECT_DIR / "Content-Based"
sys.path.append(str(CONTENT_BASED_DIR))

# Import Content-Based
try:
    import recommender_content
    print("[OK] Content-Based recommender module imported.")
except ImportError as e:
    print(f"[ERROR] Error importing Content-Based recommender: {e}")
    recommender_content = None

# Import Item-Based CF
try:
    from src import recommender_itemcf
    print("[OK] Item-Based CF recommender module imported.")
except ImportError as e:
    print(f"[ERROR] Error importing Item-Based CF recommender: {e}")
    recommender_itemcf = None

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# ==============================================
# 📁 Load Models
# ==============================================

MODELS_DIR = PROJECT_DIR / "models"
MAPPING_PATH = MODELS_DIR / "movie_mapping.pkl"
RULES_PATH = MODELS_DIR / "association_rules.pkl"

print(f"[INFO] Loading models from {MODELS_DIR}...")
try:
    if not MAPPING_PATH.exists():
        print(f"[ERROR] Error: {MAPPING_PATH} not found!")
    if not RULES_PATH.exists():
        print(f"[ERROR] Error: {RULES_PATH} not found!")

    with open(MAPPING_PATH, "rb") as f:
        movie_mapping = pickle.load(f)
    print(f"   [OK] movie_mapping.pkl loaded: {len(movie_mapping)} movies")
    print(f"   [INFO] Sample movie titles in model: {movie_mapping['title'].head(5).tolist()}")

    with open(RULES_PATH, "rb") as f:
        rules = pickle.load(f)
    print(f"   [OK] association_rules.pkl loaded: {len(rules)} rules")
except Exception as e:
    print(f"[ERROR] Error loading models: {e}")
    movie_mapping = None
    rules = None

# ==============================================
# 🧠 Recommendation Logic
# ==============================================

def title_to_movie_id(movie_mapping, title):
    """Find movieId from title (case-insensitive, fuzzy match)."""
    title = title.strip()
    title_lower = title.lower()
    
    # 1. Exact match (case-insensitive)
    match = movie_mapping[movie_mapping["title"].str.lower() == title_lower]
    if not match.empty:
        return int(match.iloc[0]["movieId"])
    
    # 2. Try removing year if present in input (e.g. "Movie (2020)" -> "Movie")
    # Or adding year wildcard? No, usually model has years.
    
    # 3. Try contains (if input is "Matrix", find "The Matrix")
    # Be careful with short words.
    if len(title) > 3:
        partial = movie_mapping[movie_mapping["title"].str.lower().str.contains(title_lower, regex=False)]
        if not partial.empty:
            # Return the shortest match (likely the most exact one)
            # e.g. "Batman" -> matches "Batman", "Batman Returns". We want "Batman".
            best_match = partial.loc[partial["title"].str.len().idxmin()]
            print(f"   [MATCH] Fuzzy match: '{title}' -> '{best_match['title']}'")
            return int(best_match["movieId"])

    return None

def get_recommendations(movie_mapping, rules, liked_titles, top_n=10):
    """Generate recommendations based on liked movies."""
    if movie_mapping is None or rules is None:
        print("[WARN] Models are not loaded.")
        return []

    liked_ids = []
    missing_titles = []
    for title in liked_titles:
        movie_id = title_to_movie_id(movie_mapping, title)
        if movie_id:
            liked_ids.append(movie_id)
        else:
            missing_titles.append(title)
    
    if missing_titles:
        print(f"[WARN] Could not find IDs for: {missing_titles}")

    if not liked_ids:
        print("[WARN] No valid movie IDs found from input list.")
        return []
    
    liked_set = set(liked_ids)
    print(f"[INFO] Finding rules for movie IDs: {liked_set}")
    
    # Find rules where antecedents are a subset of liked movies
    matching_rules = rules[
        rules["antecedents"].apply(lambda x: bool(x) and x.issubset(liked_set))
    ]
    
    if matching_rules.empty:
        print("[WARN] No matching association rules found for these movies.")
        return []
    
    suggestions = {}
    for _, row in matching_rules.iterrows():
        for movie_id in row["consequents"]:
            if movie_id in liked_set:
                continue
            
            # Score = confidence * lift
            score = row.get("score", row["confidence"] * row["lift"])
            
            if score > suggestions.get(movie_id, {}).get("score", 0):
                suggestions[movie_id] = {
                    "movieId": movie_id,
                    "score": score,
                    "confidence": row["confidence"],
                    "lift": row["lift"]
                }
    
    # Sort by score
    sorted_suggestions = sorted(
        suggestions.values(), 
        key=lambda x: x["score"], 
        reverse=True
    )[:top_n]
    
    # Add titles
    id_to_title = dict(zip(movie_mapping["movieId"], movie_mapping["title"]))
    for s in sorted_suggestions:
        s["title"] = id_to_title.get(s["movieId"], f"Movie #{s['movieId']}")
    
    return sorted_suggestions

# ==============================================
# 🌐 API Routes
# ==============================================

@app.route('/recommend', methods=['POST'])
def recommend():
    print("\n[REQ] [Model 1] Received recommendation request")
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    liked_movies = data.get("liked_movies", [])
    top_n = data.get("top_n", 10)
    
    print(f"   Input movies: {liked_movies}")
    
    if not isinstance(liked_movies, list):
        return jsonify({"error": "'liked_movies' must be a list"}), 400

    try:
        recommendations = get_recommendations(movie_mapping, rules, liked_movies, top_n)
        print(f"   [OK] Generated {len(recommendations)} recommendations")
        
        return jsonify({
            "success": True,
            "model": "association_rules",
            "recommendations": recommendations
        })
    except Exception as e:
        print(f"[ERROR] Error processing request: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/recommend/content', methods=['POST'])
def recommend_content():
    print("\n[REQ] [Model 2] Received Content-Based recommendation request")
    if not recommender_content:
        return jsonify({"success": False, "error": "Content-Based model not loaded"}), 503

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    liked_movies = data.get("liked_movies", [])
    top_n = data.get("top_n", 10)
    
    print(f"   Input movies: {liked_movies}")

    try:
        # 1. Load artifacts
        bundle = recommender_content.load_artifacts()
        
        # 2. Convert titles to IDs
        liked_ids, missing = recommender_content.titles_to_ids(liked_movies, bundle)
        
        if missing:
            print(f"   [WARN] Missing titles in Content-Based model: {missing}")
        
        if not liked_ids:
            return jsonify({
                "success": True,
                "model": "content_based",
                "recommendations": [],
                "warning": "No valid movies found in input"
            })

        # 3. Get recommendations
        df_recs = recommender_content.recommend_multi(liked_ids, top_n=top_n)
        
        # 4. Convert to list of dicts
        recommendations = df_recs.to_dict(orient="records")
        print(f"   [OK] Generated {len(recommendations)} recommendations")

        return jsonify({
            "success": True,
            "model": "content_based",
            "recommendations": recommendations
        })

    except Exception as e:
        print(f"[ERROR] Error processing Content-Based request: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/recommend/itemcf', methods=['POST'])
def recommend_itemcf():
    print("\n[REQ] [Model 3] Received Item-Based CF recommendation request")
    if not recommender_itemcf:
        return jsonify({"success": False, "error": "Item-Based CF model not loaded"}), 503

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    liked_movies = data.get("liked_movies", [])
    top_n = data.get("top_n", 10)
    
    print(f"   Input movies: {liked_movies}")

    try:
        # Call the recommender function
        # It returns (DataFrame, missing_titles_list)
        df_recs, missing = recommender_itemcf.recommend_item_based(liked_movies, top_n=top_n)
        
        if missing:
            print(f"   [WARN] Missing titles in Item-Based model: {missing}")
        
        if df_recs.empty:
             return jsonify({
                "success": True,
                "model": "item_based_cf",
                "recommendations": [],
                "warning": "No recommendations found (insufficient data or no matching movies)"
            })

        # Convert DataFrame to list of dicts
        recommendations = df_recs.to_dict(orient="records")
        print(f"   [OK] Generated {len(recommendations)} recommendations")

        return jsonify({
            "success": True,
            "model": "item_based_cf",
            "recommendations": recommendations
        })

    except Exception as e:
        print(f"[ERROR] Error processing Item-Based CF request: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "models_loaded": movie_mapping is not None})

if __name__ == '__main__':
    print("[START] Starting Python AI Server on port 9001...")
    app.run(host='0.0.0.0', port=9001, debug=True)
