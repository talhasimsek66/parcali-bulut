from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_interface, name='chat_interface'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/history/<uuid:session_id>/', views.get_chat_history, name='get_chat_history'),
]
