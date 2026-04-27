from django.db import models


# sohbet oturumu (ChatGPT gibi her konuşma)
class ChatSession(models.Model):
    title = models.CharField(max_length=255, default="Yeni Sohbet")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# GÜNCELLENDİ: artık session’a bağlı
class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages", null=True)

    user_message = models.TextField(verbose_name="Kullanıcı Sorusu")
    ai_response = models.TextField(verbose_name="Yapay Zeka Cevabı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Sohbet Geçmişi"
        verbose_name_plural = "Sohbet Geçmişleri"
        ordering = ['-created_at']

    def __str__(self):
        return f"Soru: {self.user_message[:50]}..."