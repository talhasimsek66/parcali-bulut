from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("chat.urls")),  # anasayfada direkt chat llm i açılsın diye ana uygulama url ine ekledim
]
