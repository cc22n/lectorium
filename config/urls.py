from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("books/", include("apps.books.urls", namespace="books")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    # Clubs at root so home is at /
    path("", include("apps.clubs.urls", namespace="clubs")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "config.views.handler404"
handler500 = "config.views.handler500"
