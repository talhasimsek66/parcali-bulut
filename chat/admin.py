from django.contrib import admin
from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user_message', 'created_at')
    search_fields = ('user_message', 'ai_response')
    readonly_fields = ('user_message', 'ai_response', 'created_at')  # geçmiş değiştirilemesin only read olsun
