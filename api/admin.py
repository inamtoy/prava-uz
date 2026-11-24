from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AppRelease


@admin.register(AppRelease)
class AppReleaseAdmin(ModelAdmin):
    list_display = ("version_name", "version_code", "is_required", "size_mb", "created_at")
    readonly_fields = ("created_at",)

    @admin.display(description="hajmi (MB)")
    def size_mb(self, obj):
        try:
            return round(obj.apk.size / 1024 / 1024, 1)
        except (OSError, ValueError):
            return "—"
