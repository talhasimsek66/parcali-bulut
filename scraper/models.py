from django.db import models
from pgvector.django import VectorField

class AcibademData(models.Model):
    title = models.CharField(max_length=255, verbose_name="Sayfa Başlığı")
    url = models.URLField(unique=True, verbose_name="Sayfa Linki")
    content = models.TextField(verbose_name="Sayfa İçeriği")
    # nomic-embed-text modeli 768 boyutlu vektör üretir
    embedding = VectorField(dimensions=768, null=True, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True, verbose_name="Çekilme Tarihi")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Acıbadem Verisi"
        verbose_name_plural = "Acıbadem Verileri"
