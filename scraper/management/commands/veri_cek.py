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
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
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
                # Tüm sayfalar için Selenium kullanıyoruz (Dinamik içerik riski için)
                if "obs.acibadem.edu.tr" in url:
                    driver.get("https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246")
                    time.sleep(2)
                
                driver.get(url)
                time.sleep(4) # Sayfanın yüklenmesi için bekle
                
                body_element = driver.find_element(By.TAG_NAME, "body")
                text_content = body_element.text
                
                # İletişim sayfasında ekstra temizlik veya özel alan kontrolü (Örn: Footer)
                try:
                    footer = driver.find_element(By.TAG_NAME, "footer").text
                    if footer and footer not in text_content:
                        text_content += "\n\nİLETİŞİM VE ADRES BİLGİLERİ:\n" + footer
                except:
                    pass

                title = driver.title if driver.title else "Başlık Bulunamadı"
                
                if "obs.acibadem.edu.tr" in url:
                    title = "Bilgisayar Mühendisliği - Program Bilgileri"

                if len(text_content) < 100:
                    self.stdout.write(self.style.WARNING(f"Uyarı: {url} sayfasından çok az veri çekildi."))

                # Veritabanına kaydet
                AcibademData.objects.update_or_create(
                    url=url,
                    defaults={'title': title, 'content': text_content}
                )
                self.stdout.write(self.style.SUCCESS(f"Başarıyla kaydedildi: {title} ({len(text_content)} karakter)"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata: {str(e)}"))

            time.sleep(2)

        driver.quit()

        # ==========================================================
        # ADIM 2: RAG INDEX OLUŞTURMA (İYİLEŞTİRİLDİ)
        # ==========================================================
        self.stdout.write(self.style.WARNING("\nVeritabanı verileri vektörleştiriliyor (RAG Indexing)..."))

        try:
            # 1. Veritabanındaki tüm içerikleri çek
            tum_veriler = AcibademData.objects.all()
            if not tum_veriler:
                self.stdout.write(self.style.ERROR("Indexlenecek veri bulunamadı!"))
                return

            # Metinleri Document nesnelerine dönüştür ve metadata ekle
            raw_documents = []
            for d in tum_veriler:
                raw_documents.append(Document(
                    page_content=f"Başlık: {d.title}\nİçerik: {d.content}",
                    metadata={"source": d.url, "title": d.title}
                ))

            # --- KRİTİK BİLGİ ENJEKSİYONU (Garanti altına almak için) ---
            raw_documents.append(Document(
                page_content="Acıbadem Üniversitesi İletişim Bilgileri: Kerem Aydınlar Kampüsü, Kayışdağı Cad. No:32 Ataşehir/İstanbul. Telefon: +90 216 500 44 44. E-posta: info@acibadem.edu.tr. Web: www.acibadem.edu.tr",
                metadata={"source": "manual", "title": "Genel İletişim Bilgileri"}
            ))
            # -----------------------------------------------------------

            # Dokümanları parçalara (chunk) ayıralım
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=100)
            split_docs = text_splitter.split_documents(raw_documents)

            # --- CONTEXT PADDING (Her parçaya kritik bilgiyi ekle) ---
            # Böylece ne çekilirse çekilsin adres, telefon ve kilit kişiler LLM'in önünde olur.
            footer_info = """
[Üniversite Genel Bilgileri: 
Adres: Kerem Aydınlar Kampüsü, Kayışdağı Cad. No:32 Ataşehir/İstanbul. 
Telefon: +90 216 500 44 44. 
Bölüm Başkanı: Prof. Dr. Ahmet BULUT.
Email: info@acibadem.edu.tr]"""
            
            final_docs = []
            for doc in split_docs:
                doc.page_content += footer_info
                final_docs.append(doc)
            
            # 2. Embedding modelini tanımla
            embeddings = OllamaEmbeddings(
                model="nomic-embed-text",
                base_url="http://llm:11434"
            )

            # 3. FAISS Vektör Veritabanını oluştur
            vector_db = FAISS.from_documents(final_docs, embeddings)

            # 4. Yerel klasöre kaydet
            vector_db.save_local("faiss_index")

            self.stdout.write(self.style.SUCCESS('RAG için vektör index başarıyla oluşturuldu!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Vektörleştirme hatası: {str(e)}"))

        self.stdout.write(self.style.SUCCESS('Tüm işlemler tamamlandı!'))