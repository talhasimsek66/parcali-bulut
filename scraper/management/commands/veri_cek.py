import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from scraper.models import AcibademData
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from langchain_text_splitters import RecursiveCharacterTextSplitter


class Command(BaseCommand):
    # terminalde görünecek açıklama metni
    help = "Acıbadem Üniversitesi web sitelerinden veri çeker, akıllıca parçalar ve vektörler."

    def handle(self, *args, **kwargs):
        # scrape edilecek hedef web sitelerinin listesi
        urls_to_scrape = [
            "https://www.acibadem.edu.tr/hakkimizda",
            "https://www.acibadem.edu.tr/iletisim",
            "https://obs.acibadem.edu.tr/oibs/bologna/progAbout.aspx?lang=tr&curSunit=6246"
        ]

        # selenium için arkaplan ayarları
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(
            "--window-size=1920,1080")

        self.stdout.write(self.style.SUCCESS('Veri çekme işlemi başlatılıyor...'))

        # docker üzerindeki selenyum a bağlan
        try:
            driver = webdriver.Remote(
                command_executor='http://selenium:4444/wd/hub',
                options=chrome_options
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Selenium başlatılamadı: {e}"))
            return

        AcibademData.objects.all().delete()

        # akıllı parçalayıcı (LangChain)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,  # her parça yaklaşık 800 karakter olacak
            chunk_overlap=200,  # parçalar arası 200 karakterlik bir kesişim olacak ki bağlam kopmasın
            length_function=len,  # uzunluğu ölçmek için standart Python len() fonksiyonu kullanılır
            # bölme öncelik sırası önce paragraflardan sığmazsa noktalardan sığmazsa boşluklardan böler
            separators=["\n\n", "\n", ".", "!", "?", " ", ""]
        )

        for url in urls_to_scrape:
            self.stdout.write(f"Bağlanılıyor: {url}")

            try:
                # dinamek sayfalar (selenyum kullan)
                if "obs.acibadem.edu.tr" in url:
                    self.stdout.write("Güvenlik duvarı aşılıyor, ana sayfadan oturum alınıyor...")
                    # obs doğrudan alt sayfalara girişi engeller önce ana sayfaya gidip cookie alıyoruz
                    driver.get(
                        "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246")
                    time.sleep(3)  # sayfanın yüklenmesi için 3 saniye bekle

                    self.stdout.write("Oturum alındı, doğrudan veri sayfasına gidiliyor...")
                    driver.get(url)  # şimdi asıl hedef sayfaya gidiyoruz
                    time.sleep(3)

                    # sayfadaki sadece body etiketinin içindeki görünen metni al
                    text_content = driver.find_element(By.TAG_NAME, "body").text
                    title = "Bilgisayar Mühendisliği - Program Bilgileri"

                # statik sayfa için beautiful soup + requests
                else:
                    # bazı siteler botları engeller bunu aşmak için gerçek bir tarayıcı gibi davran
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(url, headers=headers)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        # menü, footer, script kodları gibi yapay zekanın kafasını karıştıracak gereksiz html etiketlerini sil
                        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                            script.extract()

                        # sayfanın başlığını al
                        title = soup.title.string.strip() if soup.title else "Başlık Bulunamadı"
                        # kalan temiz html deki tüm metni boşluklarla birleştirerek al
                        text_content = soup.get_text(separator=' ', strip=True)
                    else:
                        continue  # sayfa 200 dönmezse bu url yi atla

                # metni parçala (akıllıca)
                # çekilen devasa metni yukarıda tanımladığımız LangChain ayarlarıyla mantıksal parçalara ayırıyoruz
                chunks = text_splitter.split_text(text_content)

                self.stdout.write(f"Metin {len(chunks)} mantıksal parçaya bölündü, vektörleniyor...")

                # her bir parçayı sırayla veritabanına kaydetme aşaması
                for i, chunk in enumerate(chunks):
                    try:
                        # ollama ya istek atıp metni matematiksel bir vektöre dönüştürüyoruz
                        embed_response = requests.post('http://llm:11434/api/embeddings', json={
                            "model": "nomic-embed-text",  # embeding için özel üretilmiş hafif model
                            "prompt": chunk
                        })
                        embedding_vector = embed_response.json().get('embedding')
                    except Exception as e:
                        embedding_vector = None  # Hata olursa vektörsüz kaydet

                    # veritabanında url lerin benzersiz olması için sonlarına "#parca-1", "#parca-2" gibi ekler
                    chunk_url = f"{url}#parca-{i + 1}"
                    chunk_title = f"{title} (Kısım {i + 1})"

                    # veritabanına kayıt
                    AcibademData.objects.create(
                        url=chunk_url,
                        title=chunk_title,
                        content=chunk,  # parçalanmış saf metin
                        embedding=embedding_vector  # anlamsal aramayı sağlayacak 768 boyutlu sayı dizisi
                    )
                self.stdout.write(self.style.SUCCESS(f"Başarıyla kaydedildi: {title}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata oluştu: {str(e)}"))

        # tüm işlemler bitince selenium tarayıcısını kapat (çok ram yiyor)
        driver.quit()
        self.stdout.write(self.style.SUCCESS('Tüm veri çekme ve vektörleme işlemleri tamamlandı!'))