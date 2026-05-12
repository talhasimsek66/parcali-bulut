# ==============================================================================
# CHATBOT UYGULAMASI - DOCKER YAPILANDIRMASI
# ==============================================================================
# Bu Dockerfile, uygulamanın her ortamda (Local, CI/CD, Production) 
# aynı şekilde çalışmasını sağlayan bir imaj oluşturur.
# ------------------------------------------------------------------------------

# Hafif ve performanslı olması için 'slim' tabanlı Python imajı seçiyoruz:
FROM python:3.11-slim

# Uygulamanın konteynır içinde çalışacağı ana dizini belirliyoruz:
WORKDIR /app

# ------------------------------------------------------------------------------
# ÇEVRESEL DEĞİŞKENLER (Optimization)
# ------------------------------------------------------------------------------
# Python'un .pyc dosyaları oluşturmasını engeller (Konteynır temizliği için):
ENV PYTHONDONTWRITEBYTECODE 1

# Python loglarının anlık olarak terminale düşmesini sağlar (Buffer'ı kapatır):
ENV PYTHONUNBUFFERED 1

# ------------------------------------------------------------------------------
# BAĞIMLILIKLARIN YÜKLENMESİ
# ------------------------------------------------------------------------------
# Önce sadece requirements.txt dosyasını kopyalıyoruz.
# Bu sayede kod değişse bile Docker katman (cache) mekanizmasını kullanarak 
# kütüphaneleri tekrar tekrar indirmez, zamandan tasarruf sağlar.
COPY requirements.txt .

# pip aracını güncelliyoruz ve projeye özel kütüphaneleri yüklüyoruz:
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ------------------------------------------------------------------------------
# KAYNAK KODUN KOPYALANMASI
# ------------------------------------------------------------------------------
# Projenin tüm dosyalarını mevcut dizinden konteynırın /app dizinine kopyalıyoruz:
COPY . .

# Not: Konteynır başlatıldığında çalışacak komut docker-compose.yml içinde 
# 'command: python manage.py runserver 0.0.0.0:8000' olarak tanımlanmıştır.
