"""Yig'ilgan APK'ni yangi ilova versiyasi sifatida e'lon qiladi.

    python manage.py publish_apk mobile/build/app/outputs/flutter-apk/app-debug.apk --notes "Nima yangi"

Versiya kodi va nomi mobile/pubspec.yaml dagi `version: 0.2.0+2` dan olinadi (yoki --code/--name).
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from api.models import AppRelease


class Command(BaseCommand):
    help = "APK faylni yangi ilova versiyasi sifatida qo'shadi (ilovada 'Yangilash' oynasi chiqadi)."

    def add_arguments(self, parser):
        parser.add_argument("apk", help="APK fayl yo'li")
        parser.add_argument("--notes", default="", help="Nima yangi (foydalanuvchiga ko'rsatiladi)")
        parser.add_argument("--code", type=int, help="versionCode (sukut: pubspec.yaml)")
        parser.add_argument("--name", help="versionName (sukut: pubspec.yaml)")
        parser.add_argument("--required", action="store_true", help="Majburiy yangilanish")

    def handle(self, *args, **opts):
        apk = Path(opts["apk"])
        if not apk.is_file():
            raise CommandError(f"Fayl topilmadi: {apk}")
        code, name = opts["code"], opts["name"]
        if code is None or name is None:
            pubspec = Path(settings.BASE_DIR) / "mobile" / "pubspec.yaml"
            m = re.search(r"^version:\s*([\w.]+)\+(\d+)\s*$", pubspec.read_text(encoding="utf-8"), re.M)
            if not m:
                raise CommandError("pubspec.yaml da 'version: X.Y.Z+N' topilmadi — --code va --name bering.")
            name = name or m.group(1)
            code = code if code is not None else int(m.group(2))
        latest = AppRelease.objects.first()
        if latest and latest.version_code >= code:
            raise CommandError(f"versionCode {code} eng so'nggisidan ({latest.version_code}) katta bo'lishi kerak.")

        release = AppRelease(version_code=code, version_name=name, notes=opts["notes"], is_required=opts["required"])
        with apk.open("rb") as f:
            release.apk.save(f"prava-{name}-{code}.apk", File(f), save=False)
        release.save()
        self.stdout.write(self.style.SUCCESS(
            f"E'lon qilindi: {name} ({code}), {release.apk.size / 1024 / 1024:.1f} MB: {release.apk.url}"
        ))
