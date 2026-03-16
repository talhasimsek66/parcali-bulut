# 🎓 Acıbadem Üniversitesi AI Chatbot (RAG & Local LLM)

Bu proje, Acıbadem Üniversitesi web sitelerindeki (statik ve dinamik) verileri toplayarak, bu veriler üzerinden öğrencilere ve adaylara doğru bilgiler sunan **Yerel Yapay Zeka (Local LLM) destekli bir RAG (Retrieval-Augmented Generation)** uygulamasıdır.

Proje tamamen **Docker** mimarisi üzerinde çalışmakta olup, dışarıdan hiçbir ücretli API'ye (OpenAI vb.) ihtiyaç duymadan kendi içindeki Ollama sunucusu ile cevap üretir.

## Öne Çıkan Özellikler

* **Yerel Dil Modeli (Local LLM):** Uygulama içine entegre edilmiş Ollama ve `Qwen 2.5 (3B)` modeli sayesinde veriler dışarı çıkmaz, tamamen yerelde çalışır.
* **Akıllı Bağlam Arama (RAG):** Kullanıcının sorusu analiz edilir ve veritabanındaki binlerce satır veri arasından sadece soruyla ilgili (Context) kısımlar yapay zekaya beslenir.
* **Sohbet Belleği (Chat Memory):** Asistan, önceki konuşmaları hatırlar. "Peki bu bölümün başkanı kim?" gibi bağlama dayalı ardışık soruları sorunsuz cevaplar.
* **Gelişmiş Web Scraping:** * Normal sayfalar için yüksek hızlı `requests` ve `BeautifulSoup`.
  * *OBS* gibi güvenlik duvarlı, dinamik, çerez (cookie) gerektiren ve **iframe** içine gizlenmiş karmaşık sayfalar için arkaplanda çalışan `Selenium (Headless Chromium)` otomasyonu.
* **Tam Konteynerizasyon:** Tüm sistem (Web, Veritabanı, Yapay Zeka ve Tarayıcı) tek bir `docker-compose` komutu ile ayağa kalkar.
* **Güvenli Mimari:** Tüm hassas veriler ve veritabanı şifreleri `.env` dosyası üzerinden güvenle yönetilir.

## Kullanılan Teknolojiler

* **Backend:** Python 3.11, Django 5.x
* **Veritabanı:** PostgreSQL 15
* **Yapay Zeka:** Ollama (Qwen 2.5)
* **Veri Madenciliği:** Selenium WebDriver, BeautifulSoup4, Requests
* **Altyapı:** Docker & Docker Compose

---

## Kurulum ve Çalıştırma

Projenin bilgisayarınızda çalışabilmesi için **Docker** ve **Docker Compose** kurulu olmalıdır.

### 1. Projeyi Klonlayın
```bash
git clone <sizin-repo-linkiniz>
cd parcali-bulut

```

### 2. Çevresel Değişkenleri (.env) Ayarlayın

Projenin çalışması için gizli anahtarların ve veritabanı şifrelerinin tanımlanması gerekir. Ana dizinde bulunan `.env .example` dosyasının adını `.env` olarak değiştirin veya yeni bir `.env` dosyası oluşturup içini şu şekilde doldurun:

```env
SECRET_KEY=kendi_gizli_anahtarinizi_yazin
DEBUG=True
DB_NAME=ornek_veritabani_adi
DB_USER=ornek_kullanici_adi
DB_PASSWORD=cok_guclu_bir_sifre_belirleyin

```

### 3. Docker Konteynerlerini Başlatın

```bash
docker compose up -d --build

```

### 4. Yapay Zeka Modelini İndirin

*(Bu işlem internet hızınıza bağlı olarak birkaç dakika sürebilir)*

```bash
docker compose exec llm ollama pull qwen2.5:3b

```

### 5. Veritabanını Hazırlayın

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

```

### 6. Admin Hesabı Oluşturun

```bash
docker compose exec web python manage.py createsuperuser

```

### 7. Verileri Çekin (Scraping)

Üniversitenin sisteminden verileri çekip veritabanına kaydetmek için botu çalıştırın:

```bash
docker compose exec web python manage.py veri_cek

```

---

## 🎯 Kullanım

Tüm kurulumlar tamamlandıktan sonra tarayıcınızdan şu adreslere gidebilirsiniz:

* **Sohbet Arayüzü:** `http://localhost:8000` (Yapay zeka ile sohbet edebileceğiniz ana ekran)
* **Yönetim Paneli:** `http://localhost:8000/admin` (Çekilen verileri ve sohbet geçmişlerini yönetebileceğiniz panel)

## 📌 Geliştirici Notları

Bu proje, web scraping süreçlerinde karşılaşılan "görünmez metin", "dinamik yükleme", "iframe izolasyonu" ve "session/cookie koruması" gibi ileri düzey sorunların Selenium ve Python kullanılarak nasıl aşılacağını göstermek üzere geliştirilmiştir.
