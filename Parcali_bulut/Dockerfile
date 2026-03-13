FROM python:3.11-slim

WORKDIR /app

# Çevresel değişkenler
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Mevcut projenin tüm dosyalarını kopyala
COPY . .
