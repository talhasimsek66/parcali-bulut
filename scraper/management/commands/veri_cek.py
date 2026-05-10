# scraper/management/commands/veri_cek.py

import json
import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from scraper.models import AcibademData
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class Command(BaseCommand):
    help = "Acıbadem Üniversitesi web sitelerinden veri çeker, parçalar ve vektörler."

    def handle(self, *args, **kwargs):
        urls_to_scrape = [
            "https://www.acibadem.edu.tr/hakkimizda",
            "https://www.acibadem.edu.tr/iletisim",
            "https://obs.acibadem.edu.tr/oibs/bologna/progAbout.aspx?lang=tr&curSunit=6246"
        ]

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

        # eski verileri temizle ki parçalanmış halleriyle tertemiz baştan eklensin (bunu yapmazsam değişmemiş datalarda değişiklik olmadığını fark edip olduğu gibi bırakıyor)
        AcibademData.objects.all().delete()

        for url in urls_to_scrape:
            self.stdout.write(f"Bağlanılıyor: {url}")

            try:
                if "obs.acibadem.edu.tr" in url:
                    self.stdout.write("Güvenlik duvarı aşılıyor, ana sayfadan oturum alınıyor...")
                    driver.get(
                        "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246")
                    time.sleep(3)
                    self.stdout.write("Oturum alındı, doğrudan veri sayfasına gidiliyor...")
                    driver.get(url)
                    time.sleep(3)
                    text_content = driver.find_element(By.TAG_NAME, "body").text
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

                # metin parçalama
                chunk_size = 800  # her parça ortalama 800 karakter olacak
                overlap = 200  # anlam kopukluğu olmasın diye 200 karakter üst üste binecek (overlap)
                chunks = []

                if len(text_content) > chunk_size:
                    for i in range(0, len(text_content), chunk_size - overlap):
                        chunks.append(text_content[i:i + chunk_size])
                else:
                    chunks.append(text_content)

                self.stdout.write(f"Metin {len(chunks)} parçaya bölündü, vektörleniyor...")

                for i, chunk in enumerate(chunks):
                    try:
                        embed_response = requests.post('http://llm:11434/api/embeddings', json={
                            "model": "nomic-embed-text",
                            "prompt": chunk
                        })
                        embedding_vector = embed_response.json().get('embedding')
                    except Exception as e:
                        embedding_vector = None

                    # aynı url yi veritabanına birden fazla kez kaydedebilmek için sonuna #parca-1 gibi etiketler ekliyoruz
                    chunk_url = f"{url}#parca-{i + 1}"
                    chunk_title = f"{title} (Kısım {i + 1})"

                    AcibademData.objects.create(
                        url=chunk_url,
                        title=chunk_title,
                        content=chunk,
                        embedding=embedding_vector
                    )
                self.stdout.write(self.style.SUCCESS(f"Başarıyla kaydedildi: {title} (Tüm Parçalar)"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata oluştu: {str(e)}"))

        driver.quit()
        self.stdout.write(self.style.SUCCESS('Tüm veri çekme işlemleri tamamlandı!'))
