from django.contrib import admin
from django.urls import path

from apps.api.api import ops_api, v1_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", ops_api.urls),
    path("api/v1/", v1_api.urls),
]
