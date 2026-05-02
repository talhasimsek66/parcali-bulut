from django.db import models


class ChatSession(models.Model):
    title = models.CharField(max_length=255, verbose_name="Sohbet Başlığı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        null=True,
        blank=True,
        verbose_name="Sohbet"
    )
    user_message = models.TextField(verbose_name="Kullanıcı Sorusu")
    ai_response = models.TextField(verbose_name="Yapay Zeka Cevabı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Sohbet Mesajı"
        verbose_name_plural = "Sohbet Mesajları"
        ordering = ['-created_at']

    def __str__(self):
        session_title = self.session.title if self.session else "Session Yok"
        return f"{session_title} - {self.user_message[:40]}"