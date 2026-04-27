import time
import requests
import os
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from scraper.models import AcibademData
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- RAG İÇİN YENİ EKLENENLER ---
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter


# ------------------------------

class Command(BaseCommand):
    help = "Acıbadem Üniversitesi web sitelerinden veri çeker ve RAG için indexler."

    def handle(self, *args, **kwargs):
        urls_to_scrape = [
            "https://www.acibadem.edu.tr/hakkimizda",
            "https://www.acibadem.edu.tr/iletisim",
            "https://obs.acibadem.edu.tr/oibs/bologna/progAbout.aspx?lang=tr&curSunit=6246"
        ]

        # Selenium Ayarları
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        self.stdout.write(self.style.SUCCESS('Veri çekme işlemi başlatılıyor...'))

        try:
            driver = webdriver.Remote(
                command_executor='http://selenium:4444/wd/hub',
                options=chrome_options
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Selenium başlatılamadı: {e}"))
            return

        for url in urls_to_scrape:
            self.stdout.write(f"Bağlanılıyor: {url}")
            try:
                if "obs.acibadem.edu.tr" in url:
                    driver.get(
                        "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246")
                    time.sleep(3)
                    driver.get(url)
                    time.sleep(3)
                    body_element = driver.find_element(By.TAG_NAME, "body")
                    text_content = body_element.text
                    title = "Bilgisayar Mühendisliği - Program Bilgileri"
                else:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        for script in soup(["script", "style", "nav", "footer", "header"]):
                            script.extract()
                        title = soup.title.string.strip() if soup.title else "Başlık Bulunamadı"
                        text_content = soup.get_text(separator=' ', strip=True)
                    else:
                        continue

                # Veritabanına kaydet
                AcibademData.objects.update_or_create(
                    url=url,
                    defaults={'title': title, 'content': text_content}
                )
                self.stdout.write(self.style.SUCCESS(f"Başarıyla kaydedildi: {title}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata: {str(e)}"))

            time.sleep(2)

        driver.quit()

        # ==========================================================
        # ADIM 2: RAG INDEX OLUŞTURMA (BURASI YENİ)
        # ==========================================================
        self.stdout.write(self.style.WARNING("\nVeritabanı verileri vektörleştiriliyor (RAG Indexing)..."))

        try:
            # 1. Veritabanındaki tüm içerikleri çek
            tum_veriler = AcibademData.objects.all()
            if not tum_veriler:
                self.stdout.write(self.style.ERROR("Indexlenecek veri bulunamadı!"))
                return

            # Metinleri birleştirip parçalara (chunk) ayıralım
            # Her bir veriyi sayfa başlığıyla birlikte ekliyoruz ki bağlam kaybolmasın
            hazir_metinler = [f"Başlık: {d.title}\nİçerik: {d.content}" for d in tum_veriler]

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=75)
            docs = text_splitter.create_documents(hazir_metinler)

            # 2. Embedding modelini tanımla (Ollama Docker üzerinde çalıştığı için base_url gerekebilir)
            # Eğer hata alırsan base_url='http://llm:11434' ekleyebilirsin
            embeddings = OllamaEmbeddings(model="qwen2.5:3b")

            # 3. FAISS Vektör Veritabanını oluştur
            vector_db = FAISS.from_documents(docs, embeddings)

            # 4. Yerel klasöre kaydet (faiss_index adında klasör oluşur)
            vector_db.save_local("faiss_index")

            self.stdout.write(self.style.SUCCESS('RAG için vektör index başarıyla oluşturuldu!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Vektörleştirme hatası: {str(e)}"))

        self.stdout.write(self.style.SUCCESS('Tüm işlemler tamamlandı!'))