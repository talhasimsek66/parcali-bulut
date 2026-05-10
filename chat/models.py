from django.db import models


class ChatMessage(models.Model):
    user_message = models.TextField(verbose_name="Kullanıcı Sorusu")
    ai_response = models.TextField(verbose_name="Yapay Zeka Cevabı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Sohbet Geçmişi"
        verbose_name_plural = "Sohbet Geçmişleri"
        ordering = ['-created_at']  # en son sorulan en üstte görünsün

    def __str__(self):
        return f"Soru: {self.user_message[:50]}..."
