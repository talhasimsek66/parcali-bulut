FROM python:3.11-slim

WORKDIR /app

# Çevresel değişkenler
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Bağımlılıkları yükle
COPY Parcali_bulut/requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Mevcut projenin tüm dosyalarını kopyala
COPY Parcali_bulut .
