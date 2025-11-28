# Content-Based Test Web

Content-Based modellerini hızlıca doğrulamak ve değerlendirmek için hazırlanan Streamlit arayüzü. Arayüz, artefaktların durumunu kontrol etmenizi, manuel film girişleriyle öneri çalıştırmanızı ve `evaluate_content.py` içindeki HitRate senaryolarını tetiklemenizi sağlar.

## Ön Koşullar

- Python 3.10+ (sistemdeki `python3` ile uyumlu olmalıdır)
- `Content-Based/models` klasöründe TF-IDF artefaktlarının hazır olması:
  - `tfidf_vectorizer.pkl`
  - `tfidf_matrix.npz`
  - `metadata.parquet` (veya eşdeğer pickle)
- `data/ratings_small.csv` ve `data/links_small.csv` dosyaları (`evaluate_content.py` için)

## Kurulum

Depo kök dizininden aşağıdaki adımları izleyin:

```bash
cd /Users/omerfarukaltinova/Git_Projects/MovieRecommender
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r test-web/requirements.txt
```

## Çalıştırma

```bash
cd /Users/omerfarukaltinova/Git_Projects/MovieRecommender/test-web
streamlit run app.py
```

Arayüz tarayıcıda açıldıktan sonra üç ana sekme göreceksiniz:

### 1. Manuel Öneri
- Virgül veya satır sonu ile ayrılmış film adlarını girip `recommender_content.py` çıktısını tablo ve grafik halinde inceleyebilirsiniz.
- Eksik başlıklar ve fallback durumları Türkçe uyarılarla bildirilir.

### 2. Model İncelemesi
- Son öneri sonuçlarından bir film seçip tür, overview ve skor metriklerini inceleyin.
- Artefaktlardan gelen metadata çerçevesini küçük bir tablo halinde görüntüleyin.

### 3. Değerlendirme Senaryosu
- `evaluate_content.evaluate` fonksiyonunu tetikleyerek HitRate@N metriğini çalıştırın.
- `ratings_small.csv` ve `links_small.csv` yollarını güncelleyerek farklı veri kümelerini test edin.
- Örnek kullanıcı sonuçları tablo halinde listelenir.
- Formun altında yer alan **İnput/Output Paylaşımı** bölümünden, kullandığınız parametreleri ve çıkan sonuçları JSON olarak indirip paylaşabilirsiniz.
- Sekmelerin üzerinde yer alan **Veri Özeti** paneli metadata ve ratings dosyalarındaki toplam film/kullanıcı sayılarını sürekli gösterir. Hemen altındaki bilgi kutusu ise kullanıcı seçim mantığını (rating eşiği, minimum beğeni, örneklenen kullanıcı sayısı vb.) özetler.

## Sorun Giderme

- **Artefakt eksik uyarısı:** Sidebar’daki tabloyu kontrol edin; eksik dosyaları `Content-Based/models` klasörüne yerleştirip `Artefaktları Yeniden Yükle` butonuna basın.
- **Değerlendirme dosya hatası:** Formdaki yolların gerçekten var olduğundan emin olun (mutlaka mutlak yol kullanın).
- **Streamlit yeniden yüklenmesi:** Büyük modeller yüklenirken zaman alabilir; `st.cache_resource` sayesinde aynı oturumda yeniden yükleme yapılmaz, ancak manuel olarak düğmeye bastığınızda artefaktlar tazelenir.

