import csv
import json
import ast
import os

# Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, '../../../dataset/credits.csv')
json_path = os.path.join(base_dir, 'credits_clean.json')

print(f"Reading {csv_path}...")

credits_data = {}

try:
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                movie_id = int(row['id'])
                
                # Parse cast
                cast_list = ast.literal_eval(row['cast'])
                actors = []
                for member in cast_list[:5]: # Top 5
                    actors.append(member['name'])
                
                # Parse crew
                crew_list = ast.literal_eval(row['crew'])
                director = ""
                for member in crew_list:
                    if member['job'] == 'Director':
                        director = member['name']
                        break
                
                credits_data[movie_id] = {
                    'actors': ", ".join(actors),
                    'director': director
                }
                
            except Exception as e:
                # print(f"Error parsing row {row.get('id')}: {e}")
                continue

    print(f"Processed {len(credits_data)} movies.")

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(credits_data, f)

    print(f"Saved to {json_path}")

except Exception as e:
    print(f"Fatal error: {e}")
