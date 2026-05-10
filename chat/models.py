import uuid
from django.db import models

class ChatSession(models.Model):
    # Her sohbetin benzersiz bir kimliği (UUID) olacak
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Yeni Sohbet", verbose_name="Başlık")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class ChatMessage(models.Model):
    # Her mesaj artık bir oturuma bağlı
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    user_message = models.TextField(verbose_name="Kullanıcı Sorusu")
    ai_response = models.TextField(verbose_name="Yapay Zeka Cevabı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Sohbet Mesajı"
        verbose_name_plural = "Sohbet Mesajları"
        ordering = ['created_at'] # Akış için eskiden yeniye sıralı
