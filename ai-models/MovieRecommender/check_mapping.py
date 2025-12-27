import pickle
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_DIR / "models"
MAPPING_PATH = MODELS_DIR / "movie_mapping.pkl"

with open(MAPPING_PATH, "rb") as f:
    movie_mapping = pickle.load(f)

print("Columns:", movie_mapping.columns)
print(movie_mapping.head())
