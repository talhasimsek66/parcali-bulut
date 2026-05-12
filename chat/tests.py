# ==============================================================================
# CHAT UYGULAMASI - BİRİM VE ENTEGRASYON TESTLERİ
# ==============================================================================
# Bu dosya, sohbet arayüzünün ve arka plandaki API uç noktalarının (endpoints)
# doğru çalışıp çalışmadığını denetlemek için yazılmış test senaryolarını içerir.
# ------------------------------------------------------------------------------

import uuid
from django.test import Client, TestCase
from chat.models import ChatMessage, ChatSession

class DeleteSessionApiTests(TestCase):
    """
    Sohbet oturumlarını silme işlemini yürüten API uç noktasını test eder.
    Güvenlik ve doğru HTTP durum kodlarının (status codes) döndürülmesini denetler.
    """

    def setUp(self):
        """
        Her test metodu çalışmadan önce çalıştırılan hazırlık aşaması.
        Temiz bir test ortamı oluşturmak için bir oturum (session) oluşturur.
        """
        # Django'nun dahili HTTP istemcisini (Client) başlatıyoruz:
        self.client = Client()
        # Testlerde silmek üzere bir oturum kaydı oluşturuyoruz:
        self.session = ChatSession.objects.create(title="Test oturumu")

    def test_delete_returns_204(self):
        """
        BAŞARILI SİLME: Bir oturumun ID'si ile DELETE isteği atıldığında,
        sistemin 204 No Content döndürdüğünü ve veritabanından silindiğini doğrular.
        """
        # API URL'sini oluşturuyoruz:
        url = f"/api/session/{self.session.id}/"
        
        # DELETE isteğini gönderiyoruz:
        response = self.client.delete(url)
        
        # HTTP 204 (Başarılı, İçerik Yok) döndüğünü kontrol ediyoruz:
        self.assertEqual(response.status_code, 204)
        # Cevap gövdesinin boş olduğunu doğruluyoruz:
        self.assertEqual(response.content, b"")
        # Veritabanında artık bu kaydın OLMADIĞINI teyit ediyoruz:
        self.assertFalse(ChatSession.objects.filter(pk=self.session.pk).exists())

    def test_delete_unknown_returns_404(self):
        """
        HATA YÖNETİMİ: Veritabanında olmayan (rastgele bir UUID) bir oturum
        silinmeye çalışıldığında, sistemin 404 Not Found döndürdüğünü kontrol eder.
        """
        # Rastgele bir UUID oluşturup olmayan bir adrese istek atıyoruz:
        url = f"/api/session/{uuid.uuid4()}/"
        response = self.client.delete(url)
        
        # Durum kodunun 404 olduğunu doğruluyoruz:
        self.assertEqual(response.status_code, 404)
        # Hata mesajının JSON formatında dönüp dönmediğine bakıyoruz:
        self.assertIn("error", response.json())

    def test_delete_method_not_allowed_for_get(self):
        """
        METOD GÜVENLİĞİ: Sadece DELETE metoduna izin veren bir uç noktasına 
        GET isteği atıldığında, 405 Method Not Allowed hatası alınmalıdır.
        """
        url = f"/api/session/{self.session.id}/"
        # Yanlış metodla (GET) istek atıyoruz:
        response = self.client.get(url)
        
        # Durum kodunun 405 olduğunu kontrol ediyoruz:
        self.assertEqual(response.status_code, 405)


class HistoryApiTests(TestCase):
    """
    Sohbet geçmişini getiren API'nın doğruluğunu test eder.
    Mesajların doğru oturuma bağlı olarak dönüp dönmediğini denetler.
    """

    def setUp(self):
        """
        Test için bir oturum ve bu oturuma bağlı bir mesaj kaydı oluşturur.
        """
        self.client = Client()
        # Geçmişi test etmek için örnek bir oturum:
        self.session = ChatSession.objects.create(title="Gecmis test")
        # Bu oturuma bir adet kullanıcı sorusu ve AI cevabı ekliyoruz:
        ChatMessage.objects.create(
            session=self.session,
            user_message="Soru",
            ai_response="Cevap",
        )

    def test_history_returns_messages(self):
        """
        VERİ DOĞRULAMA: Geçmiş API'sinden gelen mesajların içeriğinin 
        veritabanındaki ile birebir aynı olduğunu kontrol eder.
        """
        url = f"/api/history/{self.session.id}/"
        response = self.client.get(url)
        
        # İstek başarılı olmalı (200 OK):
        self.assertEqual(response.status_code, 200)
        
        # JSON verisini parse ediyoruz:
        data = response.json()
        
        # Mesaj listesinin uzunluğunu ve içeriğini doğruluyoruz:
        self.assertEqual(len(data["messages"]), 1)
        self.assertEqual(data["messages"][0]["user_message"], "Soru")
        self.assertEqual(data["messages"][0]["ai_response"], "Cevap")

    def test_history_unknown_session_404(self):
        """
        HATA YÖNETİMİ: Geçmişi istenen oturum bulunamadığında 404 hatası verilmelidir.
        """
        url = f"/api/history/{uuid.uuid4()}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class ChatPageTests(TestCase):
    """
    Kullanıcı arayüzünün (Frontend/HTML) temel yüklenme testlerini yapar.
    """

    def test_home_returns_200(self):
        """
        SAYFA YÜKLENME: Ana sayfanın (/) başarıyla açıldığını ve içerisinde 
        beklenen anahtar kelimelerin (örneğin 'Acıbadem') geçtiğini doğrular.
        """
        # Ana sayfaya GET isteği gönderiyoruz:
        response = self.client.get("/")
        
        # Sayfa başarılı bir şekilde render edildi mi (200)?
        self.assertEqual(response.status_code, 200)
        # Sayfa içeriğinde kurum adı geçiyor mu?
        self.assertContains(response, "Acıbadem", html=False)
