"""
URL configuration for config project.
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def healthz(request):
    """Cheap liveness probe for the hosting platform (no DB, no model loading)."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("api/", include("data_engineering.urls")),
]
