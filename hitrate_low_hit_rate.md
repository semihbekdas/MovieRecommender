# Content-Based Hit Rate Analizi

Bu doküman `test-web` değerlendirme sekmesinde görülen düşük HitRate@10 değerinin kök sebebini ve önerilen aksiyonları özetler.

## Çalışma Ortamı

- Komut: `python3 Content-Based/evaluate_content.py --n-users 50 --top-n 10` (ayrıca `--mode profile`, `--min-liked 5` varyasyonları)
- Veri: `data/ratings.csv` ve `data/links.csv`
- İçerik model artefaktları: `Content-Based/models/metadata.parquet`, `tfidf_matrix.npz`, `tfidf_vectorizer.pkl`

Bu komutlar Streamlit değerlendirme sekmesiyle aynı fonksiyonu (`evaluate_content.evaluate`) tetikliyor; yani ölçülen oran UI kaynaklı değil, model davranışına ait.

## Bulgular

1. **Hit oranı istikrarlı biçimde %2 civarında**  
   - Standard, profile ve farklı `min_liked` değerleriyle her koşulda `HitRate@10 = 0.02 (1/50)` üretildi.
2. **Değerlendirme akışı sorunsuz çalışıyor**  
   - Script gizlenen filmi doğru şekilde seçip `Content-Based/recommender_content.py` içindeki `recommend_multi` fonksiyonuna yönlendiriyor; kodda mantık hatasına rastlanmadı.
3. **Model önerileri MovieLens alanına uzak**  
   - TF-IDF yalnızca genre + overview metinlerinden besleniyor, popülerlik veya kullanıcı davranışı sinyali yok.  
   - Belirli kullanıcı beğenileriyle (`Sabrina`, `The American President`, `Sense and Sensibility`) yapılan manuel testte ilk öneriler MovieLens’te yer almayan niş yapımlar.
4. **Gizlenen filmler çoğunlukla listeye hiç giremiyor**  
   - 80 kullanıcıda Top-500 sonuçlar incelendi: 77 kullanıcı için gizlenen film öneri listesine hiç girmedi, sadece 3 kullanıcıda bulundu (rank ortalaması 42). Film Top-500’e girmiyorsa Top-10 hit’e dönüşmesi mümkün değil.
5. **Veri eşleşmesi ve artefaktlar sağlam**  
   - `links_small.csv` → metadata TMDB kapsaması %99.5.  
   - `bundle.id_to_index` anahtar tipleri doğru (`numpy.int64`).  
   - Değerlendirmeye giren kullanıcı sayısı 666 ve ortalama 77 beğeniye sahipler; yetersiz veri problemi yok.

## Kök Sebep

Model, MovieLens kullanıcı davranışlarını temsil eden hiçbir sinyali içermiyor; yalnızca içerik benzerliklerine bakarak koca katalog (44 520 film) içinde niş ama semantik olarak benzer filmler döndürüyor. Gizlenen film genellikle popüler, yüksek oy almış yapımlar olduğundan, salt TF-IDF benzerliğiyle Top-10’a girmesi düşük ihtimal.

## Öneriler

1. **Öneri uzayını daralt**  
   - Model skorlarını üretirken sonuçları MovieLens’te gerçekten rating almış filmlerle (`links_small.csv` seti veya `vote_count` ≥ belirli eşik) filtrele. Böylece gizlenen filmin listede yer alma ihtimali artar.
2. **Popülerlik/oy ağırlıklı yeniden sıralama ekle**  
   - TF-IDF skorunu `vote_count` veya `vote_average` ile harmanlayarak kullanıcıların aşina olduğu filmleri yukarı taşı. Basit bir `score = α·similarity + β·pop_score` yaklaşımı bile HitRate’i iyileştirir.
3. **Kullanıcı profilini varsayılanlaştır veya ağırlıkları ekle**  
   - `user_profile.build_user_profile` çıktısını standart modda da kullanarak tek bir temsil vektörü üzerinden cosine benzerlik hesapla; beğeni skorlarını ağırlık olarak dahil et.
4. **Öznitelikleri zenginleştir**  
   - İçerik metnine oyuncu, yönetmen, anahtar kelime gibi alanları ekle (MovieLens `credits.csv`, `keywords.csv`). Bu, “The Godfather” gibi filmlerin gerçekten benzer yapımlarla eşleşmesini kolaylaştırır.
5. **Collaborative filtering veya popülerlik fallback’i**  
   - Uzun vadede TF-IDF önerilerini ALS/implicit CF skorlarıyla harmanlamak veya en azından MovieLens popüler listesi ile re-rank etmek geri çağırmayı artıracaktır.

Bu adımlar uygulandığında değerlendirme sekmesindeki HitRate metriğinin anlamlı şekilde yükseleceği öngörülmektedir.

