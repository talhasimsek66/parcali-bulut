import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from scraper.models import AcibademData
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class Command(BaseCommand):
    help = "Acıbadem Üniversitesi web sitelerinden veri çeker ve veritabanına kaydeder."

    def handle(self, *args, **kwargs):
        urls_to_scrape = [
            "https://www.acibadem.edu.tr/hakkimizda",
            "https://www.acibadem.edu.tr/iletisim",
            "https://obs.acibadem.edu.tr/oibs/bologna/progAbout.aspx?lang=tr&curSunit=6246"
        ]

        # selenium Ayarları
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
                # sadece obs sistemi ise selenium kullan
                if "obs.acibadem.edu.tr" in url:
                    self.stdout.write("Güvenlik duvarı aşılıyor, ana sayfadan oturum alınıyor...")
                    # önce index.aspx git (cookie)
                    driver.get(
                        "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246")
                    time.sleep(3)
                    self.stdout.write("Oturum alındı, doğrudan veri sayfasına gidiliyor...")
                    driver.get(url)
                    time.sleep(3)
                    body_element = driver.find_element(By.TAG_NAME, "body")
                    text_content = body_element.text

                    title = "Bilgisayar Mühendisliği - Program Bilgileri"

                # diğer normal sayfalar için requests yöntemi
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
                        self.stdout.write(self.style.ERROR(f"Sayfa çekilemedi, Durum Kodu: {response.status_code}"))
                        continue

                # veritabanına kaydet
                AcibademData.objects.update_or_create(
                    url=url,
                    defaults={'title': title, 'content': text_content}
                )
                self.stdout.write(self.style.SUCCESS(f"Başarıyla kaydedildi: {title}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata oluştu: {str(e)}"))

            self.stdout.write("2 saniye bekleniyor...")
            time.sleep(2)

        driver.quit()
        self.stdout.write(self.style.SUCCESS('Tüm veri çekme işlemleri tamamlandı!'))
