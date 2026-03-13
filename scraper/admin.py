from django.contrib import admin
from .models import AcibademData

@admin.register(AcibademData)
class AcibademDataAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'scraped_at')
    search_fields = ('title', 'content')
