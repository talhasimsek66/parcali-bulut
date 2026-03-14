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
            "https://obs.acibadem.edu.tr/oibs/bologna/progAbout.aspx?lang=tr&curSunit=6246"
        ]

        # selenium ayarları
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        self.stdout.write(self.style.SUCCESS('Veri çekme işlemi başlatılıyor...'))

        # dinamik sayfalar için selenium driver ını docker üzerinden başlat
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
                    self.stdout.write("Dinamik sayfa algılandı, Selenium ile işleniyor...")
                    driver.get(url)
                    # sitenin tamamen yüklenmesi için 5 saniye bekle
                    time.sleep(5)

                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    if len(iframes) > 0:
                        self.stdout.write("Gizli çerçeve (iframe) bulundu, içine giriliyor...")
                        # selenium u asıl içeriğin olduğu çerçevenin içine sokuyoruz
                        driver.switch_to.frame(iframes[0])
                        time.sleep(2)  # çerçeve içinin yüklenmesi için ufak bir bekleme

                    # çerçevenin içindeki html i al
                    html_source = driver.page_source
                    soup = BeautifulSoup(html_source, 'html.parser')

                    # bu kez sadece çalıştırılabilir kodları temizle diğer etiketlere dokunma
                    for element in soup(["script", "style"]):
                        element.extract()

                    title = "Bilgisayar Mühendisliği - Program Bilgileri"
                    text_content = soup.get_text(separator=' ', strip=True)

                    # işlem bitince ana sayfaya geri dön
                    driver.switch_to.default_content()

                # diğer normal sayfalar için hızlı requests yöntemi
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

                # veritabanına kaydet (veya güncelle)
                AcibademData.objects.update_or_create(
                    url=url,
                    defaults={'title': title, 'content': text_content}
                )
                self.stdout.write(self.style.SUCCESS(f"Başarıyla kaydedildi: {title}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata oluştu: {str(e)}"))

            self.stdout.write("Sunucu kurallarına uyuluyor, 2 saniye bekleniyor...")
            time.sleep(2)

        driver.quit()  # tarayıcıyı kapat ve belleği temizle
        self.stdout.write(self.style.SUCCESS('Tüm veri çekme işlemleri tamamlandı!'))
