# NOTES — qabul qilingan qarorlar

- Loyiha ildizi `prava_uz/` emas, shu repo ildizi (`pravauz/`) — tuzilma ichi CLAUDE.md'dagidek.
- `tests` moduli Django'dagi `tests` bilan to'qnashmasligi uchun `quiz` app deb nomlandi.
- Email yoki username bilan kirish — `accounts/backends.py` dagi `EmailOrUsernameBackend`.
- `role` — yagona manba: `role=admin` → `is_staff=True` va `is_superuser=True` (prototipda admin to'liq huquqli). `createsuperuser` avtomatik `role=admin` qo'yadi.
- `gunicorn` Windows'da ishlamaydi — faqat serverda kerak; lokal ishlab chiqishda `runserver`.
- `ExamAnswer.question` CASCADE: savolni o'chirish o'rniga admin `is_active` ni o'chirsin (tarix saqlanadi).
- Dizayn manbasi: `design/` (Stitch, "Asphalt & Signal"). Shrift Manrope + Inter (Stitch bo'yicha), Bootstrap'dan faqat bootstrap-grid.min.css va JS (modal/dropdown); modal/dropdown CSS main.css da.
- Landing'da Stitch'dagi soxta raqamlar (12 000+ o'quvchi, 4.9 reyting), fikrlar va narxlar qo'yilmadi — statistika bazadan olinadi.
- `playwright` faqat dev uchun (`requirements-dev.txt`): `tools/screenshots.py` dizayn skrinshotlari va to'liq oqim tekshiruvi. Lokal Chrome ishlatiladi (`channel="chrome"`).
- Natija sahifasida MM:SS custom template tag'siz `widthratio` bilan hisoblanadi (.py o'zgarmasin deb).
- Chart.js 4.4.1 (jsDelivr) faqat profilda va faqat imtihon ma'lumoti bo'lsa yuklanadi.
- Sahifaga xos stillar `static/css/pages/*.css` da; umumiy tokenlar va komponentlar `main.css` da.
- `accounts/forms.py` xato matnlarida oddiy apostrof (') qolgan — shablonlarda U+02BB (ʻ) ishlatilgan.

## Baza: MySQL o'rniga PostgreSQL (2026-10-20)
- Qaror egasi — loyiha muallifi ("MySQL o'rniga PostgreSQL ishlatamiz"). Universitet hujjatida MySQL yozilgan — himoyada shu almashtirishni izohlash kerak.
- Texnik sabablar: `psycopg[binary]` Windows'da kompilyatsiyasiz o'rnatiladi (`mysqlclient` C kompilyator/wheel muammosi yo'q); lokal kompyuterda PostgreSQL 18 allaqachon o'rnatilgan; `select_for_update()` (results/services.py) Postgres'da haqiqiy qator qulfini beradi (SQLite'da e'tiborsiz qoladi); DDL tranzaksiyali — migratsiya yarim yo'lda buzilsa orqaga qaytadi; standart rejimda qat'iy (MySQL'dagi `STRICT_TRANS_TABLES` sozlamasi kerak emas).
- `manage.py test` sukut bo'yicha SQLite'da (tezlik, CLAUDE.md §12). Postgres'da sinash: `TEST_DB_ENGINE=postgres python manage.py test` (`prava` userda `CREATEDB` bo'lishi kerak).
- Ko'chirish: `dumpdata --natural-foreign --natural-primary ...` → `backup.json` (repoga kirmaydi), Postgres'da `migrate` + `loaddata` + `sqlsequencereset`.
