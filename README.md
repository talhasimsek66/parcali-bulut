# 🎓 Acıbadem Üniversitesi AI Chatbot (Semantic RAG & Local LLM)

Bu proje, Acıbadem Üniversitesi web sitelerindeki (statik ve dinamik) verileri toplayarak, bu veriler üzerinden öğrencilere ve adaylara anlamsal (semantic) doğruluğu yüksek bilgiler sunan **Yerel Yapay Zeka (Local LLM) destekli, Vektör tabanlı bir RAG (Retrieval-Augmented Generation)** uygulamasıdır.

Proje tamamen **Docker** mimarisi üzerinde çalışmakta olup, hiçbir veriyi dışarı sızdırmadan kendi içindeki çift modelli (Dual-Model) Ollama sunucusu ile cevap üretir.

## 🚀 Öne Çıkan Özellikler (Mühendislik Mimarisi)

* **Vektörel Anlamsal Arama (Semantic Search):** Klasik kelime eşleştirme (Keyword Search) yerine `pgvector` ve *Kosinüs Benzerliği (Cosine Similarity)* kullanılarak, kullanıcının cümlelerindeki "anlam" aranır. Soruda geçmeyen eşanlamlı kelimeler bile başarıyla yakalanır.
* **Akıllı Metin Parçalama (Overlapping Chunking):** Devasa web sayfaları tek bir vektöre sıkıştırılıp anlam seyrelmesine (Vector Dilution) uğratılmaz. Metinler 800 karakterlik parçalara (chunk) bölünür ve anlam kopukluğunu önlemek için her parça birbiriyle 200 karakter örtüşür (overlap).
* **Çift Yerel Dil Modeli (Dual Local LLM):** Sohbet ve sentezleme için `Qwen 2.5 (3B)`, metinleri matematiksel vektör uzayına çevirmek için `nomic-embed-text` modeli eşzamanlı olarak kullanılır.
* **Top-K Optimizasyonlu Dinamik Bağlam:** En alakalı ilk 8 metin parçası (Top-8) seçilerek yapay zekaya beslenir; böylece sayfaların derinliklerindeki detaylar bile kaçırılmaz.
* **Sohbet Belleği (Coreference & Context):** Asistan önceki konuşmaları hatırlar ve peş peşe gelen zamirli soruları ("Peki onun ilgi alanları neler?") bağlamdan kopmadan başarıyla yanıtlar.
* **İleri Düzey Web Scraping (Bypass):** Güvenlik duvarlı ve dinamik (iframe/cookie) OBS/Bologna sistemleri için arkaplanda `Selenium (Headless Chromium)` otomasyonu kullanılır.

## 🛠️ Kullanılan Teknolojiler

* **Backend:** Python 3.11, Django 5.x
* **Vektör Veritabanı:** PostgreSQL 15 + `pgvector` eklentisi
* **Yapay Zeka (Ollama):** Qwen 2.5 (3B) *(Sohbet)*, Nomic-Embed-Text *(Vektörleme)*
* **Veri Madenciliği:** Selenium WebDriver, BeautifulSoup4, Requests
* **Altyapı:** Tam Konteynerize Docker & Docker Compose

---

## ⚙️ Kurulum ve Çalıştırma

Projenin çalışabilmesi için bilgisayarınızda **Docker** ve **Docker Compose** kurulu olmalıdır.

### 1. Projeyi Klonlayın
```bash
git clone <sizin-repo-linkiniz>
cd parcali-bulut
```

### 2. Çevresel Değişkenleri (.env) Ayarlayın
Ana dizinde bulunan `.env .example` dosyasının adını `.env` olarak değiştirin ve içini doldurun:
```env
SECRET_KEY=kendi_gizli_anahtarinizi_buraya_yazin
DEBUG=True
DB_NAME=acibadem_db
DB_USER=acu_user
DB_PASSWORD=cok_guclu_bir_sifre_belirleyin
```

### 3. Docker Konteynerlerini Başlatın
```bash
docker compose up -d --build
```

### 4. Yapay Zeka Modellerini İndirin
*Hem sohbet hem de vektörleme işlemi için iki ayrı modeli yerel sunucumuza kuruyoruz:*
```bash
docker compose exec llm ollama pull qwen2.5:3b
docker compose exec llm ollama pull nomic-embed-text
```

### 5. Veritabanında Vektör Eklentisini Aktifleştirin
*Django tabloları oluşturmadan önce veritabanına gidip `pgvector` eklentisini açıyoruz. (Aşağıdaki komutta `-U` ve `-d` kısımlarına `.env` dosyanızdaki kullanıcı adı ve veritabanı adını yazın):*
```bash
docker compose exec db psql -U acu_user -d acibadem_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 6. Veritabanını Hazırlayın ve Yönetici Ekleyin
```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### 7. Verileri Çekin, Parçalayın ve Vektörleyin
Üniversite sisteminden verileri çekmek, 800 karakterlik parçalara (chunk) bölmek ve matematiksel vektörlerini veritabanına kaydetmek için botu çalıştırın:
```bash
docker compose exec web python manage.py veri_cek
```

---

## 🎯 Kullanım

Tüm işlemler tamamlandıktan sonra:

* **Sohbet Arayüzü:** `http://localhost:8000` 
* **Yönetim Paneli:** `http://localhost:8000/admin` *(Buradan çekilen verilerin parçalanmış (chunk) hallerini ve 768 boyutlu vektör (embedding) dizilerini inceleyebilirsiniz.)*

## 📌 Geliştirici Notları ve Mimari Kararlar
Bu projede doğrudan klasik bir metin araması kullanmak yerine RAG mimarisi tercih edilmiştir. Geleneksel RAG sistemlerindeki *"Vector Dilution (Anlam Seyrelmesi)"* problemini aşmak için sayfalar bütün olarak kaydedilmemiş, **Overlapping Chunking** metoduyla parçalanmıştır. Kullanıcının sorusu `nomic-embed-text` ile vektörel uzaya taşınır ve `CosineDistance` hesaplamasıyla en alakalı 8 parça bulunarak `Qwen 2.5` modeline Context (Bağlam) olarak beslenir.