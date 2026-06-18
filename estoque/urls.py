"""URL Configuration for estoque project."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("contas/", include("accounts.urls")),
    path("estoque/", include("stock.urls")),
    path("inteligencia/", include("intelligence.urls")),
    path("auditoria/", include("audit.urls")),
    path("relatorios/", include("reports.urls")),
    path("notificacoes/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
