# MovieMind 🎬

MovieMind, modern bir React ön yüzü, güçlü bir Node.js arka yüzü ve gelişmiş Python tabanlı yapay zeka modellerini birleştiren, kişiselleştirilmiş film önerileri sunan kapsamlı bir film öneri sistemidir.

## 🚀 Özellikler

- **Çoklu Model Önerileri**:
  - **Model 1: Birliktelik Kuralları (Association Rules - Apriori):** Kullanıcıların birlikte beğendiği filmleri analiz ederek "X filmini seven Y filmini de sever" kuralları çıkarır.
  - **Model 2: İçerik Tabanlı Filtreleme (Content-Based Filtering):** Film türleri ve açıklamalarına göre benzer içerikli filmler önerir.
  - **Model 3: Öğe Tabanlı İşbirlikçi Filtreleme (Item-Based Collaborative Filtering):** Rating benzerliğine dayalı öneriler sunar.
- **Kullanıcı Profilleri**: İzleme listeleri, favoriler ve arkadaş sistemleri.
- **Sosyal Özellikler**: Arkadaş ekleme ve listelerini görüntüleme.
- **Gerçek Zamanlı Veri**: Güncel puanlar ve posterler için TMDB entegrasyonu.
- **Modern Arayüz**: Tailwind CSS ile oluşturulmuş karanlık temalı (dark mode), duyarlı tasarım.

## 🛠️ Teknolojiler

- **Frontend**: React, Vite, TypeScript, Tailwind CSS
- **Backend**: Node.js, Express, SQLite, Sequelize
- **Yapay Zeka (AI/ML)**: Python, Flask, Pandas, Scikit-learn, Mlxtend

## 📦 Kurulum

1. **Depoyu Klonlayın**
   ```bash
   git clone https://github.com/semihbekdas/MovieRecommender.git
   cd MovieRecommender
   ```

2. **Bağımlılıkları Yükleyin**
   Ana dizinde şu komutu çalıştırarak hem kök dizin, hem backend hem de frontend bağımlılıklarını yükleyebilirsiniz:
   ```bash
   npm run install:all
   ```

3. **Python Kurulumu**
   Python'un yüklü olduğundan emin olun. Gerekli Python paketlerini yükleyin:
   ```bash
   cd ai-models/MovieRecommender
   pip install -r requirements.txt
   cd ../..
   ```

## 🏃‍♂️ Uygulamayı Çalıştırma

Tüm servisleri (Frontend, Backend, AI Sunucusu) ana dizinden tek bir komutla başlatabilirsiniz:

```bash
npm start
```

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:3000
- **AI Sunucusu**: http://localhost:9001

## 🤖 Öneri Algoritmaları Detayları

Bu proje, Kaggle'daki "The Movies Dataset" üzerinde çalışan farklı makine öğrenmesi tekniklerini kullanır.

### 1. Association Rules (Birliktelik Kuralları)
**Nasıl Çalışır:**
1. Kullanıcıların beğendiği filmleri (puan ≥ 4.0) belirler.
2. Apriori algoritması ile sık film setlerini bulur.
3. "X → Y" kuralları çıkarır (Support, Confidence ve Lift metriklerine göre).

### 2. Content-Based Filtering (İçerik Tabanlı)
**Nasıl Çalışır:**
1. Film türleri (genres) ve açıklamalarını (overview) birleştirir.
2. TF-IDF vektörleştirme ile sayısal temsil oluşturur.
3. Cosine Similarity ile film benzerliklerini hesaplar.
4. Soğuk başlangıç (cold-start) problemi olmadan, sadece içeriğe bakarak öneri yapar.

### 3. Item-Based Collaborative Filtering (Öğe Tabanlı İşbirlikçi Filtreleme)
**Nasıl Çalışır:**
1. Kullanıcıların filmlere verdiği puanları (ratings) kullanır.
2. User-Item matrisi oluşturur.
3. Filmler arasındaki benzerliği Cosine Similarity ile hesaplar (Bu filmi beğenenler, şu filmi de beğendi mantığı).
4. Kullanıcının geçmişte yüksek puan verdiği filmlere matematiksel olarak en yakın (benzer) filmleri önerir.

## 📂 Proje Yapısı

- `/frontend`: React uygulaması kaynak kodları.
- `/backend`: Express API ve veritabanı mantığı.
- `/ai-models`: Öneri algoritmalarını barındıran Python Flask sunucusu.
- `/dataset`: Modelleri eğitmek için kullanılan ham CSV verileri.
