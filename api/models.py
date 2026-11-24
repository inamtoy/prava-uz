from django.db import models


class AppRelease(models.Model):
    """Android ilova versiyasi (APK). Ilova ochilganda eng kattasi bilan o'zini solishtiradi."""

    version_code = models.PositiveIntegerField("versiya kodi", unique=True, help_text="pubspec.yaml dagi '+' dan keyingi son")
    version_name = models.CharField("versiya nomi", max_length=20, help_text="Masalan: 0.2.0")
    apk = models.FileField("APK fayl", upload_to="app/")
    notes = models.TextField("nima yangi", blank=True)
    is_required = models.BooleanField("majburiy", default=False, help_text="Belgilansa, eski versiyada ishlab bo'lmaydi")
    created_at = models.DateTimeField("qo'shilgan", auto_now_add=True)

    class Meta:
        db_table = "ilova_versiyalari"
        ordering = ["-version_code"]
        verbose_name = "ilova versiyasi"
        verbose_name_plural = "ilova versiyalari"

    def __str__(self):
        return f"{self.version_name} ({self.version_code})"
