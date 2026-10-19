# NOTES — qabul qilingan qarorlar

- Loyiha ildizi `prava_uz/` emas, shu repo ildizi (`pravauz/`) — tuzilma ichi CLAUDE.md'dagidek.
- `tests` moduli Django'dagi `tests` bilan to'qnashmasligi uchun `quiz` app deb nomlandi.
- Email yoki username bilan kirish — `accounts/backends.py` dagi `EmailOrUsernameBackend`.
- Superuser yaratilsa `role` avtomatik `admin` bo'ladi (aks holda `is_staff` o'chib qolardi).
- `gunicorn` Windows'da ishlamaydi — faqat serverda kerak; lokal ishlab chiqishda `runserver`.
