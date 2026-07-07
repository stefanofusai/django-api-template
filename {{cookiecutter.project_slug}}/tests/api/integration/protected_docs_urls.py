from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path
from ninja import NinjaAPI

api = NinjaAPI(
    docs_decorator=staff_member_required,
    urls_namespace="prod-docs",
)

# `admin/` is included (mirroring config/urls.py) so that `staff_member_required`'s
# default `login_url="admin:login"` reverses successfully; without it, the
# decorator raises NoReverseMatch instead of redirecting anonymous users.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
