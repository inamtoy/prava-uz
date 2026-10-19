# NOTES — qabul qilingan qarorlar

- Loyiha ildizi `prava_uz/` emas, shu repo ildizi (`pravauz/`) — tuzilma ichi CLAUDE.md'dagidek.
- `tests` moduli Django'dagi `tests` bilan to'qnashmasligi uchun `quiz` app deb nomlandi.
- Email yoki username bilan kirish — `accounts/backends.py` dagi `EmailOrUsernameBackend`.
- `role` — yagona manba: `role=admin` → `is_staff=True` va `is_superuser=True` (prototipda admin to'liq huquqli). `createsuperuser` avtomatik `role=admin` qo'yadi.
- `gunicorn` Windows'da ishlamaydi — faqat serverda kerak; lokal ishlab chiqishda `runserver`.
- `ExamAnswer.question` CASCADE: savolni o'chirish o'rniga admin `is_active` ni o'chirsin (tarix saqlanadi).
