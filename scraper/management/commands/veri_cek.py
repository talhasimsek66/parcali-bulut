import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from scraper.models import AcibademData


class Command(BaseCommand):
    help = "Acıbadem Üniversitesi web sitelerinden veri çeker ve veritabanına kaydeder."

    def handle(self, *args, **kwargs):
        # çekeceğimiz linkler
        urls_to_scrape = [
            "https://www.acibadem.edu.tr/hakkimizda",
            "https://www.acibadem.edu.tr/universite/kurum-politikalari",
            "https://www.acibadem.edu.tr/akademik/fakulteler/muhendislik-ve-doga-bilimleri-fakultesi",
            "https://www.acibadem.edu.tr/iletisim",
            "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246#"
            # sonrasında başka linkler de ekleyebilirz ilk aşamada çok eklemedim
        ]

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        self.stdout.write(self.style.SUCCESS('Veri çekme işlemi başlatılıyor...'))

        for url in urls_to_scrape:
            self.stdout.write(f"Bağlanılıyor: {url}")

            try:
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # sayfadaki gereksiz script ve stil etiketlerini temizliyoruz eğer temizlemezsek hem daha fazla kaynak tüketir hem de kafası karışır
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.extract()

                    # sayfa başlığı
                    title = soup.title.string.strip() if soup.title else "Başlık Bulunamadı"

                    # sayfadaki tüm metni temiz bir şekilde al
                    text_content = soup.get_text(separator=' ', strip=True)

                    # veritabanına kaydet (eğer link zaten varsa günceller yoksa yeni oluşturur)
                    AcibademData.objects.update_or_create(
                        url=url,
                        defaults={
                            'title': title,
                            'content': text_content
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"Başarıyla kaydedildi: {title}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Sayfa çekilemedi, Durum Kodu: {response.status_code} - {url}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata oluştu: {str(e)}"))

            # ahmet hoca kumbaraylamasın diye saniye bekle
            self.stdout.write("Sunucu kurallarına uyuluyor, 2 saniye bekleniyor...")
            time.sleep(2)

        self.stdout.write(self.style.SUCCESS('Tüm veri çekme işlemleri tamamlandı!'))
