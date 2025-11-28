<!-- feb2b079-2853-4029-9939-0731b1b20a59 74916e23-5b39-42a6-b13d-6f61c85ed044 -->
# Content-Based Model Geliştirme Planı

Bu plan yalnızca `Content-Based/` klasörü altında yer alacak içerik tabanlı öneri sistemiyle ilgilidir; diğer modeller kapsam dışıdır.

## 1. Artefakt Üretimi ve Veri Hazırlığı

- `Content-Based/data_pipeline.py` içinde baştan sona pipeline kur.
- Kaynak: `Content-Based/movies_metadata.csv` (gerekirse CLI argümanıyla farklı path desteklenir).
- Adımlar:

  1. Gerekli kolonları (tmdb `id`, `title`, `genres`, `overview`, opsiyonel `vote_average`, `vote_count`) seç ve tip dönüşümlerini yap.
  2. Genres JSON’unu parse et, overview ile birleştirerek `content` metni üret; boş içerikleri ele.
  3. `TfidfVectorizer` (stop_words="english", ayarlanabilir `max_features`, `ngram_range`) ile sparse matris oluştur.
  4. Film id → matris index eşlemesini ve temel metadata’yı `metadata.parquet` benzeri bir dosyada sakla.
  5. Artefaktları `Content-Based/models/` altında kaydet: `tfidf_vectorizer.pkl`, `tfidf_matrix.npz`, `metadata.parquet`, `content_meta.json` (parametre ve tarih bilgisi).
  6. CLI: `python Content-Based/data_pipeline.py --rebuild` çıktıları günceller, loglama sağlar.

## 2. Öneri Motoru (Standart + Çoklu Film)

- `Content-Based/recommender_content.py` ana modülü oluştur.
- Fonksiyonlar:
  - `load_artifacts()` → TF-IDF nesneleri ve metadata’yı cache’leyerek döndürür.
  - `titles_to_ids(titles)` → başlıkları tmdb id / matrix index’e çevirir, bulunamayanları raporlar.
  - `recommend_single(movie_id, top_n)` → tek film için cosine similarity hesaplar.
  - `recommend_multi(movie_ids, method="score_avg", top_n)` → çoklu film desteği (similarity ortalaması veya TF-IDF vektörlerinin birleşimi).
  - Fallback: hi̇ç film bulunamazsa metadata’daki popülerlik (`vote_count`) veya rastgele tür bazlı öneri döndür.
- Çıktı DataFrame kolonları: `title`, `tmdb_id`, `similarity`, `genres`, `overview_snippet`, isteğe bağlı `vote_average`.
- CLI testi: `python Content-Based/recommender_content.py --titles "Inception,Interstellar" --top-n 5` gibi, stdout’a tablo basar.

## 3. User Profile Yaklaşımı (Opsiyonel Ama Planlı)

- Aynı dosyada veya `Content-Based/user_profile.py` içinde:
  - `build_user_profile(movie_ids, weights=None)` → TF-IDF vektörlerinin (rating) ağırlıklı ortalamasını döndürür.
  - `recommend_with_profile(profile_vector, exclude_ids, top_n)` → profile göre cosine similarity hesaplar.
  - API kullanıcıdan rating listesi gelmezse eşit ağırlık kullanır; rating sağlanırsa ağırlıklı ortalama.
  - Bu fonksiyonlar Streamlit’te "profil bazlı" toggle’ı için hazır tutulacak, ancak mevcut app’e entegrasyon bu planda yok.

## 4. Değerlendirme Aracı

- `Content-Based/evaluate_content.py` dosyası:
  - Girdi: `data/raw/ratings_small.csv` (veya kullanıcı başka path verirse argüman).
  - Leave-one-out testi (`YOL_HARITASI.md` Bölüm 8’deki Hit Rate@N):

    1. Rastgele kullanıcı seç.
    2. Kullanıcının sevdiği filmlerden birini gizle (rating ≥ 4 varsayımı).
    3. Kalan filmlerle standart veya user profile modu çalıştır.
    4. Gizlenen film top-N listesinde mi? Hit say.

  - Çıktılar: `HitRate@5`, `HitRate@10`, test kullanıcı sayısı, örnek başarı/başarısız kullanıcı listesi, isteğe bağlı CSV log.
  - CLI: `python Content-Based/evaluate_content.py --n-users 100 --top-n 10 --mode profile`.

## 5. Dokümantasyon & Entegrasyon Notları

- `Content-Based/YOL_HARITASI.md` zaten kavramsal rehber; teknik mimariyi destekleyecek kısa bir "API referansı" bölümü eklenebilir (fonksiyon imzaları, beklenen dönüşler).
- Geliştirilen modüller Streamlit’e entegre edilmeden önce JSON/dict tabanlı bir arayüz döndürerek test edilecek; ana uygulama dosyalarına dokunulmayacak.

## 6. Dosya/Klasör Yapısı

```
Content-Based/
├── YOL_HARITASI.md
├── movies_metadata.csv
├── data_pipeline.py
├── recommender_content.py
├── user_profile.py (opsiyonel)
├── evaluate_content.py
└── models/
    ├── tfidf_vectorizer.pkl
    ├── tfidf_matrix.npz
    ├── metadata.parquet
    └── content_meta.json
```

## 7. Uygulama Sırası

1. **prep-data** – Veri temizliği & TF-IDF artefaktları (`data_pipeline.py`).
2. **implement-recommender** – Tek/çoklu film öneri fonksiyonları + CLI testi.
3. **user-profile** – Profil oluşturma ve profile göre öneri.
4. **evaluate-model** – Hit Rate@N testi ile doğrulama.
5. **docs-touchup** – API referansı ve entegrasyon notları (yalnızca Content-Based klasörü içinde).