from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import admin_login_redirect

urlpatterns = [
    # Admin'ning o'z login sahifasi o'chirilgan — yagona login: /accounts/login/
    path("admin/login/", admin_login_redirect, name="admin_login_redirect"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("results.urls")),
    path("", include("quiz.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
