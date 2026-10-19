# CLAUDE.md — Prava.uz (haydovchilik imtihoniga tayyorlov test sayti)

> Bu fayl Claude Code uchun. Loyihani **noldan ishlaydigan prototipgacha** shu fayldagi tartibda qur.
> Muddat qisqa (1 kun): avval hamma narsa **ishlashi** kerak, keyin chiroyli bo'lishi. Ortiqcha narsa qo'shma.

---

## 0. Ish qoidalari (Claude uchun)

1. **Savol berma — qur.** Noaniq joyda shu fayldagi qarorga amal qil, bo'lmasa eng oddiy yechimni tanla va `NOTES.md` ga bir qator yozib qo'y.
2. Har bir bosqich oxirida `python manage.py check` va `python manage.py test` ishlat. Xato bo'lsa — keyingi bosqichga o'tma.
3. Butun interfeys matni **o'zbek tilida (lotin yozuvi)**. Kod, o'zgaruvchi va model nomlari — inglizcha.
4. Har bir bosqichdan keyin git commit qil (`git init` qilinmagan bo'lsa — qil). Commit xabarlari qisqa, inglizcha.
5. Maxfiy narsalar (SECRET_KEY, DB parol) faqat `.env` da. `.env` → `.gitignore` ga. `.env.example` ni repoga qo'sh.
6. Kutubxonalarni minimal tut. Ruxsat etilganlari: `Django>=5.0,<6`, `psycopg[binary]` (psycopg 3), `python-decouple`, `Pillow`, `gunicorn`. Boshqa kerak bo'lsa — sababini `NOTES.md` ga yoz.
7. Frontend: Bootstrap 5.3 va Bootstrap Icons — CDN orqali. React/Vue/npm ishlatilmaydi. JavaScript — oddiy (vanilla), `static/js/` da.

---

## 1. Loyiha haqida qisqacha

**Prava.uz** — haydovchilik guvohnomasi imtihoniga tayyorlanuvchilar uchun bepul onlayn test sayti.
Universitet loyihasi (TATU, Dasturiy injiniring). Hujjatlarda belgilangan: **Python + Django, MySQL, Bootstrap**. Baza keyinroq **PostgreSQL** ga almashtirildi (sababi — `NOTES.md`).

### Birinchi versiyaga (MVP) kiradi
- Ro'yxatdan o'tish, kirish, chiqish
- Mavzular ro'yxati
- **Mashq rejimi** — mavzu bo'yicha, har javobdan keyin darrov to'g'ri/xato ko'rsatiladi
- **Imtihon rejimi** — 20 ta tasodifiy savol, 25 daqiqa taymer
- Natija sahifasi va **xatolar tahlili**
- Profil va statistika
- Admin panel (Django admin) — savol, javob, rasm qo'shish

### Keyinga qoladi (QILMA)
Mobil ilova, to'lov, video darslar, reyting jadvali, rus tili.

### Qabul mezonlari (prototip shularni bajarishi shart)
- [ ] Yangi odam ro'yxatdan o'tib, imtihonni boshidan oxirigacha yecha oladi
- [ ] Natija to'g'ri hisoblanadi (testlar bilan tasdiqlangan)
- [ ] Admin savol + 4 ta javob + rasm qo'sha oladi
- [ ] Sayt telefon ekranida (360px) buzilmasdan ochiladi
- [ ] Foydalanuvchi faqat o'z natijalarini ko'ra oladi
- [ ] Sahifalar tez ochiladi (N+1 so'rov yo'q — `select_related`/`prefetch_related`)

---

## 2. Texnologiyalar

| Qism | Tanlov |
|---|---|
| Backend | Python 3.11+, Django 5.x |
| Baza | **PostgreSQL** (asosiy, 14+). Lokal tez ishga tushirish uchun `.env` da `DB_ENGINE=sqlite` bo'lsa — SQLite |
| Frontend | Django templates + Bootstrap 5.3 (CDN) + vanilla JS |
| Statik/media | `static/` (CSS, JS), `media/questions/` (savol rasmlari) |
| Server (keyin) | Ubuntu VPS, Nginx + Gunicorn, Let's Encrypt |

---

## 3. Papka tuzilmasi

```
prava_uz/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── NOTES.md
├── config/                 # settings.py, urls.py, wsgi.py, asgi.py
├── accounts/               # ro'yxatdan o'tish, kirish, profil
├── quiz/                   # mavzular, savollar, mashq va imtihon, taymer
├── results/                # ball hisoblash, xatolar tahlili, statistika
├── templates/
│   ├── base.html
│   ├── partials/           # navbar, footer, messages, question_card
│   ├── accounts/
│   ├── quiz/
│   └── results/
├── static/
│   ├── css/main.css
│   ├── js/practice.js
│   ├── js/exam.js
│   └── img/
└── media/questions/
```

> **Muhim:** arxitektura hujjatida modul nomi `tests`. Django'da `tests` nomli app test-runner va `tests.py`
> fayllari bilan to'qnashadi, shuning uchun app nomi **`quiz`**. README'da "tests moduli = `quiz` app" deb izoh yoz.
> Admin uchun alohida app yozilmaydi — Django'ning tayyor admin bo'limi ishlatiladi (`quiz/admin.py`).

---

## 4. Ma'lumotlar bazasi (6 ta jadval)

Hujjatdagi jadvallar → Django modellari. `db_table` bilan hujjatdagi nomlarni saqla (himoyada ko'rsatish oson bo'ladi).

### 4.1 `accounts.User` → `foydalanuvchilar`
`AbstractUser` dan meros (Django parolni o'zi xeshlaydi — PBKDF2).
- `email` — `unique=True`
- `role` — `CharField(choices=[("student","O'quvchi"),("admin","Admin")], default="student")`
- `is_staff` `role == "admin"` bilan sinxron bo'lsin (`save()` ichida).
- `AUTH_USER_MODEL = "accounts.User"` — **birinchi migratsiyadan oldin** sozla.
- Kirish: **email yoki username** + parol (oddiy custom auth backend yoki formada email→username aylantirish).

### 4.2 `quiz.Topic` → `mavzular`
- `name` (CharField 200), `slug` (unique), `description` (TextField, blank), `order` (PositiveIntegerField, default 0)
- `Meta.ordering = ["order", "name"]`

### 4.3 `quiz.Question` → `savollar`
- `topic` → FK Topic (`related_name="questions"`, CASCADE)
- `text` (TextField)
- `image` (ImageField, `upload_to="questions/"`, blank, null)
- `explanation` (TextField, blank) — xato qilganda ko'rsatiladigan izoh
- `is_active` (Boolean, default True)
- `created_at` (auto_now_add)

### 4.4 `quiz.Answer` → `javoblar`
- `question` → FK Question (`related_name="answers"`, CASCADE)
- `text` (CharField 500)
- `is_correct` (Boolean, default False) — hujjatda `togri_mi`
- Qoida: har savolda **2–4 ta javob** (odatda 4), **aynan bitta** to'g'ri. Admin inline formsetda tekshir.

### 4.5 `results.Exam` → `imtihonlar`
- `user` → FK User (`related_name="exams"`)
- `mode` — `choices=[("exam","Imtihon"),("practice","Mashq")]`
- `topic` → FK Topic, null (mashq uchun)
- `started_at` (auto_now_add), `finished_at` (null)
- `duration_seconds` (PositiveIntegerField, default 1500) — 25 daqiqa
- `total_questions` (PositiveSmallIntegerField)
- `score` (PositiveSmallIntegerField, default 0) — to'g'ri javoblar soni
- `is_passed` (Boolean, null)
- `status` — `choices=[("in_progress",...),("finished",...),("expired",...)]`
- Property: `deadline`, `time_left_seconds`, `is_expired`, `percent`

### 4.6 `results.ExamAnswer` → `imtihon_javoblari`
- `exam` → FK Exam (`related_name="items"`, CASCADE)
- `question` → FK Question
- `selected_answer` → FK Answer, null (javob berilmagan bo'lishi mumkin)
- `is_correct` (Boolean, default False) — yozish paytida hisoblanadi
- `order` (PositiveSmallIntegerField) — savolning imtihondagi tartibi
- `answered_at` (null)
- `unique_together = ("exam", "question")`

> Imtihon boshlanganda 20 ta `ExamAnswer` qatori **oldindan** yaratiladi (`selected_answer=None`).
> Shunda savollar tartibi saqlanadi, sahifa yangilansa ham o'sha savollar chiqadi.

---

## 5. Biznes qoidalari

### Imtihon rejimi
- `EXAM_QUESTION_COUNT = 20`, `EXAM_DURATION_SECONDS = 25 * 60`, `EXAM_MAX_MISTAKES = 2` — `settings.py` da konstanta.
- **O'tish sharti:** xatolar soni ≤ 2 (ya'ni kamida 18/20). Javob berilmagan savol = xato.
- Savollar faqat `is_active=True` lardan, tasodifiy (`order_by("?")` prototip uchun yetarli). Bazada 20 tadan kam bo'lsa — borini ol va ogohlantir.
- Foydalanuvchida `in_progress` imtihon bo'lsa, "Imtihonni boshlash" yangisini yaratmaydi — **davom ettiradi**.
- **Taymer brauzerda, vaqt nazorati serverda:** har javob saqlashda va yakunlashda server `now() > deadline` ni tekshiradi. Muddat o'tgan bo'lsa javob qabul qilinmaydi, imtihon `expired` → avtomatik yakunlanadi.
- Imtihon davomida to'g'ri/xato **ko'rsatilmaydi**. Faqat natija sahifasida.
- Javob o'zgartirish mumkin (yakunlanguncha).

### Mashq rejimi
- Mavzu tanlanadi → shu mavzudagi savollar (aralashtirilgan, max 20 ta, mavzuda kam bo'lsa — hammasi).
- Javob bosilganda **darrov** natija: tanlangan javob yashil/qizil, to'g'ri javob yashil bilan belgilanadi, `explanation` chiqadi.
- Taymer yo'q. Mashq ham `Exam(mode="practice")` sifatida saqlanadi — statistikaga kiradi, lekin "o'tdi/o'tmadi" yo'q.

### Ball hisoblash (`results/services.py`)
Mantiqni view'larga yozma — servis funksiyalarga:
- `start_exam(user) -> Exam`
- `start_practice(user, topic) -> Exam`
- `save_answer(exam, question_id, answer_id) -> ExamAnswer` (tekshiruvlar: imtihon egasi, status, deadline, javob shu savolniki)
- `finish_exam(exam) -> Exam` (score, is_passed, finished_at, status)
- `user_stats(user) -> dict` (jami imtihonlar, o'tganlar, o'rtacha %, mavzular bo'yicha to'g'ri %, eng kuchsiz 3 mavzu)

`is_correct` qiymatini **hech qachon klientdan olma** — doim serverda `Answer.is_correct` dan hisobla.

---

## 6. URL'lar va sahifalar

| URL | Nomi | Kim | Vazifa |
|---|---|---|---|
| `/` | `home` | hamma | Bosh sahifa: qisqa tavsif, "Imtihonni boshlash", "Mashq qilish" tugmalari, nechta savol/mavzu borligi |
| `/accounts/register/` | `register` | mehmon | Ro'yxatdan o'tish (ism, username, email, parol ×2) → avtomatik kirish |
| `/accounts/login/` | `login` | mehmon | Kirish |
| `/accounts/logout/` | `logout` | kirgan | POST orqali chiqish |
| `/accounts/profile/` | `profile` | kirgan | Profil + statistika + oxirgi imtihonlar ro'yxati |
| `/mavzular/` | `topic_list` | kirgan | Mavzular kartochkalari (savol soni, foydalanuvchi progressi %) |
| `/mashq/<slug>/` | `practice_start` | kirgan | POST → mashq yaratadi → redirect |
| `/mashq/sessiya/<id>/` | `practice` | egasi | Mashq ekrani (savollar ketma-ket, JS bilan) |
| `/imtihon/` | `exam_start` | kirgan | Ma'lumot sahifasi (20 savol, 25 daq, 2 xato) + "Boshlash" (POST) |
| `/imtihon/<id>/` | `exam` | egasi | Test ekrani |
| `/api/imtihon/<id>/javob/` | `exam_answer` | egasi | POST JSON `{question_id, answer_id}` → saqlaydi. Mashqda `{is_correct, correct_answer_id, explanation}` qaytaradi, imtihonda faqat `{ok, time_left}` |
| `/imtihon/<id>/yakunlash/` | `exam_finish` | egasi | POST → `finish_exam` → natijaga redirect |
| `/natija/<id>/` | `result` | egasi | Ball, o'tdi/o'tmadi, vaqt, **xatolar tahlili** (har xato savol: savol, rasm, siz tanlagan (qizil), to'g'ri (yashil), izoh) |
| `/admin/` | — | admin | Django admin |

- Kirish talab qilinadigan joylarda `@login_required`. Begona imtihonga kirilsa → **404** (`get_object_or_404(Exam, pk=id, user=request.user)`).
- API view'lar CSRF bilan ishlaydi: JS `csrftoken` cookie'sidan `X-CSRFToken` header yuboradi. `csrf_exempt` ishlatma.

---

## 7. Test ekrani (eng muhim sahifa) — `templates/quiz/exam.html` + `static/js/exam.js`

Layout (telefonda ham):
- Tepada: savol raqami "7 / 20", **taymer** (MM:SS), "Yakunlash" tugmasi.
- 20 ta raqamli tugmachadan iborat **navigatsiya paneli**: javob berilgan — ko'k, joriy — chegarali, berilmagan — kulrang.
- Savol kartasi: rasm (bo'lsa, `img-fluid`), savol matni, 4 ta javob — katta bosiladigan tugmalar (F1–F4 tarzida raqamlangan).
- Pastda "‹ Oldingi" / "Keyingi ›".

Xatti-harakat:
- Barcha 20 savol bitta sahifada render qilinadi (har biri `<section>`, faqat joriysi ko'rinadi) — sahifalar orasida yuklanish yo'q.
- Javob bosilganda: `fetch` POST → muvaffaqiyatli bo'lsa navigatsiyada belgilanadi. Xato bo'lsa — kichik ogohlantirish, qayta urinish.
- Taymer boshlang'ich qiymati serverdan keladi (`time_left_seconds` — `data-` atribut orqali), sahifa yangilansa ham to'g'ri davom etadi.
- 5 daqiqa qolganda taymer sariq, 1 daqiqada qizil. 0 bo'lganda — avtomatik yakunlash formasi submit.
- "Yakunlash" bosilganda javob berilmagan savollar soni ko'rsatilgan Bootstrap modal (JS `confirm()` ishlatma).
- Klaviatura: `1`–`4` javob tanlash, `←`/`→` savollar orasida.
- `beforeunload` ogohlantirish (imtihon davomida).

Mashq ekrani (`practice.html` + `practice.js`) — xuddi shu karta, lekin taymer yo'q, javobdan keyin rang + izoh + "Keyingi savol". Oxirida qisqa natija va "Natijani ko'rish".

---

## 8. Dizayn (UI/UX)

- Ranglar (`static/css/main.css` da CSS o'zgaruvchilari): asosiy **ko'k** `#1f6feb`, to'g'ri **yashil** `#1a7f37`, xato **qizil** `#cf222e`, fon och kulrang `#f6f8fa`.
- Bootstrap komponentlari: navbar (logo "Prava.uz" + menyu: Mavzular, Imtihon, Profil, Chiqish), card, progress, badge, modal, alert.
- Mobile-first. Javob tugmalari kamida 48px balandlik. Matn kamida 16px.
- Foydalanuvchi yo'li: **Bosh sahifa → Kirish → Mavzular → Test ekrani → Natija → Profil**. Har sahifada keyingi qadam tugmasi aniq ko'rinsin, hech qayerda "boshi berk ko'cha" bo'lmasin.
- Bo'sh holatlar: imtihon yo'q bo'lsa profilda "Hali imtihon topshirmagansiz — [Boshlash]".
- Django `messages` — Bootstrap alert ko'rinishida.
- Profil statistikasi: 4 ta kartochka (jami imtihonlar, o'tganlar, o'rtacha ball %, eng yaxshi natija) + mavzular bo'yicha progress bar'lar + "Kuchsiz mavzular" bloki (mashq qilish tugmasi bilan) + oxirgi 10 ta imtihon jadvali.

---

## 9. Admin panel (`quiz/admin.py`, `results/admin.py`, `accounts/admin.py`)

- `Question` admin: `AnswerInline` (TabularInline, `extra=4`, `max_num=4`), list_display: id, qisqa matn, mavzu, rasm bormi, is_active; filter: mavzu, is_active; search: text. Rasm uchun kichik preview (`readonly_fields`).
- Inline formset validatsiyasi: aynan 1 ta `is_correct=True`, kamida 2 ta javob. Xato xabari o'zbekcha.
- `Topic` admin: `prepopulated_fields = {"slug": ("name",)}`, savollar soni ustuni.
- `Exam` admin: faqat o'qish (list_display: user, mode, score, is_passed, started_at), `ExamAnswer` inline readonly.
- `User` admin: `role` maydoni qo'shilgan `UserAdmin`.
- `admin.site.site_header = "Prava.uz boshqaruv paneli"`.
- Faqat `is_staff` (role=admin) kira oladi — Django buni o'zi ta'minlaydi.

---

## 10. Namuna ma'lumotlar — `python manage.py seed_data`

`quiz/management/commands/seed_data.py` yoz. Idempotent bo'lsin (qayta ishga tushirsa dublikat yaratmasin; `--reset` flagi bilan tozalab qayta yaratadi).

Yaratadi:
- Admin: `admin` / `admin12345` (role=admin) — faqat `DEBUG=True` bo'lsa. README'da ogohlantir.
- Demo o'quvchi: `demo` / `demo12345` + 3 ta tugallangan imtihon (statistika bo'sh ko'rinmasligi uchun).
- **6 ta mavzu**, har birida **kamida 8 ta savol** (jami ≥ 50), har savolda 4 ta javob, 1 tasi to'g'ri, har birida qisqa `explanation`:
  1. Umumiy qoidalar va atamalar
  2. Yo'l belgilari
  3. Svetofor va tartibga soluvchi ishoralari
  4. Chorrahalardan o'tish
  5. Quvib o'tish, to'xtash va to'xtab turish
  6. Birinchi tibbiy yordam va xavfsizlik
- Savollar O'zbekiston Respublikasi Yo'l harakati qoidalari mazmuniga mos, o'zbek tilida, real va mantiqiy bo'lsin (tezlik chegaralari: aholi punktida 70 km/soat, va h.k.). Faktlarda ishonching komil bo'lmasa — umumiy, xavfsiz faktlardan foydalan. Savol matnini ma'lumot faylida saqla: `quiz/fixtures/questions_uz.json` (komanda shuni o'qiydi) — keyin admin osongina to'ldiradi.
- Rasmlar: "Yo'l belgilari" mavzusidagi 4–6 ta savol uchun **oddiy SVG/PNG** belgilarni o'zing yasab (`Pillow` bilan: doira/uchburchak + raqam yoki belgi, masalan "70" tezlik cheklovi, STOP sakkizburchagi) `media/questions/` ga saqla va savolga biriktir. Haqiqiy rasm yuklab olishga urinma.

---

## 11. Xavfsizlik va sozlamalar (`config/settings.py`)

- `python-decouple`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_ENGINE` (`postgres`|`sqlite`), `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
- PostgreSQL: `ENGINE = "django.db.backends.postgresql"` (psycopg 3), baza `ENCODING 'UTF8'`. `manage.py test` sukut bo'yicha SQLite'da (`TEST_DB_ENGINE=postgres` bilan Postgres'da).
- `LANGUAGE_CODE = "uz"`, `TIME_ZONE = "Asia/Tashkent"`, `USE_TZ = True`.
- `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "topic_list"`, `LOGOUT_REDIRECT_URL = "home"`.
- `STATIC_ROOT`, `MEDIA_ROOT`, `MEDIA_URL`; DEBUG'da media'ni `urls.py` orqali ber.
- `DEBUG=False` bo'lganda: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` yoqiladi.
- CSRF middleware yoqilgan. Parol validatorlari standart.
- Har qanday imtihon/natija so'rovi `user=request.user` bilan filtrlanadi.
- 404 va 500 uchun oddiy o'zbekcha shablonlar.

---

## 12. Testlar (`*/tests.py` — Django TestCase)

Kamida shular yozilsin va o'tsin:
- **accounts:** ro'yxatdan o'tish ishlaydi va avtomatik kiradi; email bilan kirish; parol ochiq saqlanmaydi.
- **quiz/results servislari:**
  - `start_exam` 20 ta savol tanlaydi, takrorlanmaydi; ochiq imtihon bo'lsa yangisini yaratmaydi.
  - `save_answer` — boshqa savolning javobini rad etadi; begona foydalanuvchi imtihonini rad etadi (404); muddat o'tganda rad etadi.
  - `finish_exam` — 18/20 → o'tdi, 17/20 → o'tmadi; javob berilmagan = xato.
  - `user_stats` — to'g'ri foizlarni hisoblaydi.
- **views:** kirmagan foydalanuvchi `/imtihon/` dan login'ga yo'naltiriladi; begona `/natija/<id>/` → 404; to'liq oqim (boshlash → 20 javob → yakunlash → natija sahifasi 200).
- **admin:** savolda 2 ta to'g'ri javob bo'lsa formset xato beradi.

Testlar SQLite'da ishlasin (tezlik uchun) — settings'da `DB_ENGINE` orqali.

---

## 13. Bajarish tartibi (shu ketma-ketlikda)

**Bosqich 1 — Skelet (≈30 daq)**
- `python -m venv .venv`, `requirements.txt`, `django-admin startproject config .`, app'lar: `accounts`, `quiz`, `results`.
- settings (`.env`, til, vaqt zonasi, templates/static/media), `.gitignore`, `.env.example`, `base.html` (Bootstrap CDN, navbar, messages).
- Custom `User` modeli → `makemigrations` → `migrate`. ✅ `runserver` ochiladi.

**Bosqich 2 — Modellar + admin (≈45 daq)**
- Barcha 6 model, `db_table`, admin sozlamalari, javoblar validatsiyasi. ✅ Admin'da savol qo'shiladi.

**Bosqich 3 — Namuna ma'lumotlar (≈45 daq)**
- `questions_uz.json`, rasmlar generatsiyasi, `seed_data` komandasi. ✅ ≥50 savol bazada.

**Bosqich 4 — accounts (≈45 daq)**
- Register/login/logout, email bilan kirish, shablonlar. ✅ Ro'yxatdan o'tib kirish ishlaydi.

**Bosqich 5 — Servislar + testlar (≈1 soat)**
- `results/services.py` + 12-bo'limdagi servis testlari. ✅ `manage.py test` yashil.

**Bosqich 6 — Mashq rejimi (≈1 soat)**
- Mavzular sahifasi, mashq ekrani, `practice.js`, API. ✅ Mavzu tanlab, javob berib, rang va izoh ko'rinadi.

**Bosqich 7 — Imtihon rejimi (≈1.5 soat)**
- Ma'lumot sahifasi, test ekrani, `exam.js` (taymer, navigatsiya, modal, avto-yakunlash), yakunlash. ✅ To'liq imtihon yechiladi.

**Bosqich 8 — Natija + profil (≈1 soat)**
- Natija sahifasi va xatolar tahlili, profil statistikasi. ✅ Statistika demo foydalanuvchida to'la ko'rinadi.

**Bosqich 9 — Sayqal va tekshiruv (≈1 soat)**
- Bosh sahifa, bo'sh holatlar, 404/500, mobil ko'rinishni tekshir (360px), N+1 so'rovlarni tekshir.
- View testlari. `python manage.py check --deploy` (DEBUG=False holatda) ogohlantirishlarini ko'rib chiq.
- `README.md` ni yakunla. ✅ 1-bo'limdagi qabul mezonlarining hammasi belgilandi.

**Bosqich 10 — (ixtiyoriy, vaqt qolsa) Deploy fayllari**
- `deploy/nginx.conf`, `deploy/gunicorn.service` (systemd), `deploy/backup.sh` (kunlik `pg_dump` + cron qatori), README'da VPS'ga qo'yish qadamlari (Ubuntu, `git clone`, `.env`, `collectstatic`, `certbot --nginx`).

---

## 14. README.md tarkibi

1. Loyiha nomi, qisqa tavsif, muallif/guruh uchun bo'sh joy
2. Imkoniyatlar ro'yxati (MVP)
3. Texnologiyalar
4. **Tez ishga tushirish (SQLite):**
   ```bash
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env            # tez ishga tushirish uchun DB_ENGINE=sqlite qiling
   python manage.py migrate
   python manage.py seed_data
   python manage.py runserver
   ```
5. **PostgreSQL bilan ishga tushirish** (`psql -U postgres`):
   ```sql
   CREATE USER prava WITH PASSWORD 'parol' CREATEDB;
   CREATE DATABASE prava_uz OWNER prava ENCODING 'UTF8' TEMPLATE template0;
   ```
   `.env` da `DB_ENGINE=postgres`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=localhost`, `DB_PORT=5432`. Drayver: `psycopg[binary]` (Windows'da ham tayyor wheel). `CREATEDB` faqat `TEST_DB_ENGINE=postgres` bilan test uchun kerak.
6. Demo loginlar: `admin/admin12345`, `demo/demo12345`
7. Arxitektura: 5 qatlam, 4 modul (accounts, quiz=tests, results, admin), 6 jadval — hujjatdagi nomlar bilan moslik jadvali
8. Testlarni ishga tushirish: `python manage.py test`
9. Keyingi rejalar (mobil ilova, rus tili, reyting, to'lov)

---

## 15. Tayyorlik ro'yxati (oxirida o'zingni tekshir)

- [ ] `pip install -r requirements.txt && python manage.py migrate && python manage.py seed_data && python manage.py runserver` toza muhitda xatosiz ishlaydi
- [ ] `python manage.py test` — hammasi yashil
- [ ] Demo oqim: ro'yxatdan o'tish → mavzu → mashq → imtihon (20 savol, taymer) → natija va xatolar → profil
- [ ] Sahifa yangilansa imtihon va taymer to'g'ri davom etadi
- [ ] Taymer tugaganda imtihon avtomatik yakunlanadi; server muddatdan keyingi javobni qabul qilmaydi
- [ ] Begona imtihon/natija → 404
- [ ] Admin: savol + 4 javob + rasm qo'shish, 2 ta to'g'ri javob → xato
- [ ] 360px kenglikda gorizontal scroll yo'q
- [ ] `.env` repoda yo'q, `.env.example` bor
- [ ] Barcha interfeys matni o'zbekcha (lotin)
