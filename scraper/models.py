from django.db import models


class AcibademData(models.Model):
    title = models.CharField(max_length=255, verbose_name="Sayfa Başlığı")
    url = models.URLField(unique=True, verbose_name="Sayfa Linki")
    content = models.TextField(verbose_name="Sayfa İçeriği")
    scraped_at = models.DateTimeField(auto_now_add=True, verbose_name="Çekilme Tarihi")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Acıbadem Verisi"
        verbose_name_plural = "Acıbadem Verileri"
