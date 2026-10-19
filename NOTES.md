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

## Admin panel: django-unfold + Stitch (design/admin/)
- `unfold`, `unfold.contrib.filters` — `django.contrib.admin` dan oldin. Sozlamalar: `settings.UNFOLD` (ranglar saytdagi tokenlardan: primary #2457F5, base #0B1B33…#F4F6FA), stillar `static/css/admin.css` (Manrope sarlavhalar, "prava-" klasslari — unfold Tailwind'i oldindan kompilyatsiya qilingan, yangi Tailwind klasslari ishlamaydi).
- Dashboard: `results/dashboard.py` (DASHBOARD_CALLBACK) + `templates/admin/index.html`. Har blok — bitta aggregatsiya so'rovi; test: `AdminPagesTests` (ma'lumot ko'payganda so'rovlar soni o'zgarmaydi).
- Savol formasi 2 ustunli: `templates/admin/quiz/question/change_form.html` ("prava-side" klassli fieldset'lar o'ngga, javoblar inline chap ustunga).
- Unfold o'zbekcha tarjimasiz keladi: `locale/uz/LC_MESSAGES/django.po` (+ `.mo`). Bu muhitda GNU gettext yo'q — `python tools/compile_messages.py` bilan kompilyatsiya qilinadi.
- `role=admin` → `is_staff` va `is_superuser` (to'liq huquq); admin formada bu ikki maydon faqat o'qish uchun.

### Unfold'da qilib bo'lmagan / soddalashtirilgan joylar (Stitch'ga nisbatan)
1. Tepadagi global qidiruv (savol/mavzu/foydalanuvchi bo'yicha) — unfold'da yon menyu qidiruvi faqat menyu bandlarini filtrlaydi; ro'yxatlarda har model o'z qidiruviga ega.
2. Ro'yxat ustidagi tezkor filtr "pill"lari (Hammasi/Faol/Nofaol, Faqat rasmli, Izohsiz) — unfold'da filtrlar "Filtrlar" yon panelida (mavzu dropdown, faol, rasm, izoh).
3. Ro'yxatda qator ichidagi faol/nofaol tugmachasi (toggle) — o'rniga holat belgisi va bulk action'lar (Faollashtirish / O'chirib qo'yish).
4. Javob variantlarini sudrab tartiblash, A–D harflari va "to'g'ri javob" radio tugmasi — oddiy tabular inline (matn + "To'g'ri mi" switch); qoida formset validatsiyasida (aynan 1 to'g'ri, 2–4 javob).
5. Savol formasidagi "O'quvchi ko'rinishi (live preview)", "Qiyinlik darajasi", "Savol bali", "Vaqt chegarasi", "Modda/YHQ havolasi", matn muharriri (bold/italic) — modelda bunday maydonlar yo'q.
6. Import (CSV) / Eksport tugmalari, dashboard'dagi "Oxirgi 7 kun" davr tanlagichi va "Eksport" — qilinmadi (django-import-export kerak bo'lardi; davr 7 kunga qat'iy).
7. Bildirishnomalar (qo'ng'iroqcha), "Adminlar", "Rasmlar", "Statistika" alohida bo'limlari — sahifalar yo'q (statistika = dashboard; adminlar = Foydalanuvchilar, rol filtri).
8. Dashboard KPI'laridagi o'sish foizlari (+14% va h.k.) — o'rniga real "bu hafta +N" va "kecha: N" qiymatlari.
9. Bo'sh holat (empty state) — unfold'ning standart "natija yo'q" bloki.
10. "O'chirish savol" so'z tartibi — Django'ning o'zbekcha katalogidan ("O'chirish %(verbose_name)s").

## Yagona login (rolga qarab)
- Bitta kirish sahifasi `/accounts/login/` (`accounts.views.RoleLoginView`). Manzil `redirect_url_for(user, next)`: admin → `/admin/`, o'quvchi → profil; `next` faqat shu sayt (`url_has_allowed_host_and_scheme`) va rolga ruxsat bo'lsa (o'quvchiga `/admin/...` berilmaydi).
- `/admin/login/` → `admin_login_redirect` (URL admin'dan oldin ulangan): mehmon → `/accounts/login/?next=...`, o'quvchi → profil + "Bu bo'limga faqat administratorlar kira oladi", admin → `next`. Admin'dan chiqish → bosh sahifa (`LOGOUT_REDIRECT_URL`).
- Rol qoidasi: `role` — yagona manba; `is_superuser = role == "admin"`, `is_staff = is_admin_role` (`role == "admin" or is_superuser`). Admin roli to'liq huquq beradi, aks holda unfold'da 403 bo'lardi. `createsuperuser` → role="admin"; `0003_sync_admin_roles` mavjud yozuvlarni tuzatadi.
- Ro'yxatdan o'tish formasida rol maydoni yo'q — POST'da `role=admin` yuborilsa ham o'quvchi yaratiladi (test bor).
- Ro'yxatdan o'tgandan keyin avvalgidek mavzularga (birinchi qadam — mashq); keyingi kirishlarda — profil.

## Keyingi versiya
1. **Kontent admin guruhi (superuser'siz, cheklangan huquqlar).** Hozir `role=admin` = superuser. Keyingi qadam: `role` choices'ga `editor` qo'shish; `editor` → `is_staff=True`, `is_superuser=False` va data migratsiyada yaratiladigan "Kontent muharrirlari" guruhi (`quiz.add/change/view_topic|question|answer`, `results.view_exam`, foydalanuvchilarni ko'rmaydi). `is_admin_role` faqat to'liq admin uchun qoladi, `redirect_url_for` editor'ni ham `/admin/` ga yuboradi; dashboard'dagi "Foydalanuvchilar" KPI va sidebar bandi `permission` callback bilan yashiriladi. Testlar: editor savol qo'sha oladi, foydalanuvchi/imtihonni o'zgartira olmaydi, rolni o'zgartira olmaydi.
2. **CSV import (savollar).** `django-import-export` + `unfold.contrib.import_export` (Stitch'dagi "Import (CSV)" tugmasi). Format: `mavzu_slug, savol, javob1..javob4, togri (1–4), izoh, rasm_fayl`. Import oldidan preview va bir xil validatsiya: aynan 1 to'g'ri, 2–4 javob; xato qatorlar hisoboti. Eksport — natijalar jurnali (imtihonlar) uchun ham.
3. **Unfold'da qilinmagan joylar** (yuqoridagi ro'yxatdan) — imkon bo'yicha:
   - global qidiruv: `UNFOLD["COMMAND"]["search_models"]` + `search_callback` (savol matni, foydalanuvchi email);
   - ro'yxat ustidagi tezkor filtr "pill"lari va faol/nofaol toggle — `list_before_template` + `actions_row`;
   - javoblarni tartiblash (drag) — `Answer.order` maydoni + `ordering_field` (unfold sortable inline);
   - savol formasida "o'quvchi ko'rinishi" preview — `change_form_after_template` + saytdagi `question_card.html`;
   - dashboard davr tanlagichi (7/30 kun) va eksport;
   - qiyinlik darajasi — `Question.difficulty` maydoni yoki xato % dan avtomatik.
4. **Boshqa:** `deploy/` fayllari (nginx, gunicorn.service, `backup.sh` — kunlik `pg_dump` + cron), `ExamAnswer.question` uchun `PROTECT` (savol o'chirilsa tarix saqlansin), Stitch'dagi "Rasmlar" bo'limi (yuklangan belgilar kutubxonasi).

## Deploy (10-bosqich)
- `deploy/`: `nginx.conf` (unix socket, `/static/` 1 yil immutable — `ManifestStaticFilesStorage` hash beradi, `/media/` da skriptlar taqiqlangan), `gunicorn.service` (Type=notify, `RuntimeDirectory=prava_uz`, socket guruhi www-data, `ProtectSystem=strict` + yozish faqat `media/`), `backup.sh` (`pg_dump -Fc` + `pg_restore --list` tekshiruvi + media tar, 14 kun), `prava_uz.cron`, `env.production.example`.
- `DEBUG=False` da `STORAGES.staticfiles = ManifestStaticFilesStorage` (testlarda emas). Tekshirilgan: collectstatic (unfold bilan) va barcha sahifalar hashli statik bilan 200.
- `seed_data` serverda: demo foydalanuvchi yaratilmaydi (`--demo` bilan majburlash mumkin), `--reset` taqiqlangan (imtihon tarixi o'chib ketmasin).
- Bu Windows muhitda Linux/Docker yo'q: `nginx -t` va `systemd-analyze verify` ishga tushirilmagan — birinchi o'rnatishda serverda bajarilsin. `backup.sh` Git Bash'da lokal PostgreSQL'ga qarshi to'liq sinalgan (dump → retention → tiklash, qatorlar soni bir xil).
