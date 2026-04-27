from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_interface, name='chat_interface'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/sessions/', views.chat_sessions, name='chat_sessions'),
    path('api/session/<int:session_id>/', views.get_session_messages),
]
