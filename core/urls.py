from django.urls import path, include
from django.contrib import admin
from .views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("health/", health, name="health"),
]
