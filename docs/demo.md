# Prava.uz — himoya uchun 5 daqiqalik demo

Maqsad: 5 daqiqada butun foydalanuvchi yoʻlini (oʻquvchi) va boshqaruv panelini (admin) koʻrsatish. Har qadamda **nima bosiladi** va **nima aytiladi**.

## Tayyorgarlik (himoyadan 10 daqiqa oldin)

```bash
# PostgreSQL ishlab turganini tekshiring (yoki .env da DB_ENGINE=sqlite)
python manage.py migrate
python manage.py seed_data --reset   # toza maʼlumot: 139 bilet, 1381 savol (Excel), admin + demo (3 ta imtihon)
python manage.py test                # 76 ta test — yashil boʻlishi kerak
python manage.py runserver
```

- Brauzerda **ikkita oyna**: oddiy (oʻquvchi) va inkognito (admin) — sessiyalar aralashmasin.
- Oʻquvchi oynasida `demo` / `demo12345` bilan kirib qoʻying va **chiqing** (birinchi kirish tezroq ochiladi).
- Ekran oʻlchami: 1440px yoki undan katta; telefon koʻrinishi uchun DevTools → 375px tayyor tursin.
- Zaxira: internet boʻlmasa ham ishlaydi, faqat shriftlar va ikonkalar CDN'dan — oldindan bir marta oching (kesh).
- Excel faylni (`savollar/avtotest_savollar_javoblar.xlsx`) alohida oynada ochib qoʻying — «maʼlumot qayerdan» savoliga koʻrsatish uchun.

| Login | Parol | Kimligi |
|---|---|---|
| `demo` | `demo12345` | Oʻquvchi, 3 ta tugallangan imtihon (statistika toʻla) |
| `admin` | `admin12345` | Administrator |

## Ssenariy

### 0:00 – 0:30 · Bosh sahifa (mehmon)
- `http://127.0.0.1:8000/` — «Haydovchilik imtihonini birinchi urinishda topshiring».
- **Ayting:** statistika qatoridagi raqamlar bazadan olinadi (1357 faol savol, 139 bilet, 20 savol / 25 daqiqa, 2 tagacha xato) — soxta raqam yoʻq. Savollar — haqiqiy avtotest savollari, Excel fayldan yuklangan.

### 0:30 – 1:15 · Yagona kirish → mashq
- «Kirish» → `demo` / `demo12345` → **profilga** tushadi (oʻquvchi roli).
- «Biletlar» → 139 ta bilet katakchasi: savollar soni va oʻzlashtirish foizi; boshlangani sariq, oʻzlashtirilgani (90%+) yashil; pastda «Kuchsiz biletlaringiz».
- Istalgan biletni bosing (masalan «1-bilet») → mashq. **Rasmli** savolga **ataylab xato** javob bering → qizil + toʻgʻri javob yashil. Keyingisiga toʻgʻri javob → «Toʻgʻri javob!».
- **Ayting:** toʻgʻri/xato serverda hisoblanadi, sahifada toʻgʻri javob oldindan yashirilgan.

### 1:15 – 2:45 · Imtihon simulyatori
- «Imtihon» → qoidalar kartasi (20 savol · 25 daqiqa · 2 xatogacha) → «Imtihonni boshlash». Savollar 1357 ta faol savoldan tasodifiy.
- 3–4 savolga javob bering: klaviatura `1`–`4`, `→` keyingi savol; xato javob darrov qizil (toʻgʻrisi yashil), savollar xaritasida ham katak qizil/yashil. Variantlar soni 2–4 — Excel'dagidek.
- **F5 bosing** → taymer va javoblar joyida qoladi. **Ayting:** «taymer brauzerda, vaqt nazorati serverda — muddat oʻtgan javob qabul qilinmaydi».
- «Yakunlash» → modal: «N ta savolga javob berilmagan» → «Yakunlash».
- Natija: katta ball doirasi, «Oʻtmadi» (javobsizlar = xato), **xatolar tahlili** — birinchi kartani oching: savol rasmi, siz tanlagan (qizil), toʻgʻri (yashil).

### 2:45 – 3:30 · Profil va statistika
- Avatar → «Profil va statistika»: 4 ta kartochka, natijalar dinamikasi grafigi (oʻtish chegarasi 90%), biletlar boʻyicha foizlar, kuchsiz biletlar, oxirgi imtihonlar jadvali.
- (Ixtiyoriy, 10 soniya) DevTools → 375px: sayt telefonda buzilmaydi, pastda tab bar.

### 3:30 – 4:45 · Admin (inkognito oyna)
- `http://127.0.0.1:8000/admin/` → **yagona login sahifasiga** yoʻnaltiriladi (`?next=/admin/`). `admin` / `admin12345` → **boshqaruv paneli**.
- **Ayting:** bitta login sahifa, rolga qarab yoʻnaltirish; Django'ning oʻz admin login sahifasi oʻchirilgan.
- Dashboard: KPI'lar, 7 kunlik grafik — hozirgina topshirilgan imtihon shu yerda koʻrinadi; «Eng qiyin biletlar»; «Kontent holati» — izohsiz va nofaol savollar soni.
- «Savollar» roʻyxati: rasm miniatyuralari, filtrlar (bilet, rasmli, izohsiz). **«Nofaol (24)»** tabini bosing → **Ayting:** «Excel'da bu savollarning rasmi yoʻq edi — import ularni avtomatik nofaol qildi, rasm qoʻshilgach faollashtiriladi».
- Rasmli savolni oching (2 ustun): oʻngda rasm va **savol statistikasi**. Ikkinchi javobni ham «Toʻgʻri mi» qilib **Saqlash** → xato: «Aynan bitta javob toʻgʻri deb belgilanishi kerak». Bekor qiling.
- «Imtihonlar» → bitta imtihon: faqat koʻrish, xatolar tahlili kartalari.

### 4:45 – 5:00 · Huquqlar
- Oʻquvchi oynasida manzilga `/admin/` yozing → profilga qaytadi: «Bu boʻlimga faqat administratorlar kira oladi».
- **Yakun:** «Qabul mezonlari testlar bilan tasdiqlangan — `python manage.py test`: 76 ta test, Excel import ham test bilan tekshiriladi».

## Ehtimoliy savollar va qisqa javoblar

| Savol | Javob |
|---|---|
| Savollar qayerdan? | Rasmiy avtotest savollari (PDF → Excel, 1382 qator, 139 bilet, 902 rasm). `python manage.py seed_data` Excel'ni oʻqib bazaga yozadi |
| Excel qanday oʻqiladi? | `quiz/xlsx_import.py`: `.xlsx` — bu ZIP ichidagi XML. Standart `zipfile` + `ElementTree` bilan varaq yacheykalari va joylashtirilgan rasmlar (rasm qaysi qatorga bogʻlangani — drawing XML'dan) oʻqiladi. Qoʻshimcha kutubxona kerak emas |
| Nechta savol yuklandi, nega 1382 emas? | 1381: 95-bilet 4-savolda manbada toʻgʻri javob belgilanmagan — import uni tashlab, konsolga yozadi. Yana 24 tasining rasmi manbada yoʻq — ular nofaol |
| Nega «mavzu» emas, «bilet»? | Excel'da mavzu ustuni yoʻq, faqat bilet raqami. Avtomatik mavzuga ajratish xato berishi mumkin edi, shuning uchun manbadagidek biletlar. Jadval nomi hujjatdagidek `mavzular` |
| Nega baʼzi savollarda 2–3 javob? | Manbada shunday. Model 2–4 javobga ruxsat beradi, aynan bittasi toʻgʻri (admin formasida tekshiriladi) |
| Yangi savol qanday qoʻshiladi? | Admin → «Yangi savol»: matn, bilet, rasm, 2–4 javob, izoh. Yoki Excel'ga qator qoʻshib `seed_data --file ...` |
| Nega MySQL emas, PostgreSQL? | Muallif qarori: drayver Windows'da kompilyatsiyasiz oʻrnatiladi, `select_for_update` haqiqiy qulf beradi, DDL tranzaksiyali. Hujjatdagi 6 jadval nomi saqlangan (`db_table`). `NOTES.md` |
| Vaqtni qanday aldab boʻlmaydi? | Deadline = `started_at + 25 daqiqa`, har javob va yakunlashda serverda tekshiriladi; muddat oʻtsa imtihon `expired` boʻladi |
| Javobni oʻzgartirib aldash mumkinmi? | Yoʻq — toʻgʻri/xato darrov koʻrsatilgani uchun birinchi javob yakuniy (`save_answer`), `is_correct` faqat serverda hisoblanadi |
| Natija qanday hisoblanadi? | `results/services.py` → `finish_exam`: toʻgʻri javoblar soni; xato = 20 − toʻgʻri (javobsiz ham xato); ≤ 2 xato → oʻtdi. Testlar: 18/20 oʻtdi, 17/20 oʻtmadi |
| Begona natijani koʻrish mumkinmi? | Yoʻq — har soʻrov `user=request.user` bilan filtrlanadi, aks holda 404 |
| Parollar qanday saqlanadi? | Django PBKDF2 xeshi; ochiq saqlanmasligi testda tekshirilgan. Formalar CSRF bilan himoyalangan |
| Nega app nomi `quiz`, hujjatda `tests`? | Django'da `tests` nomi test-runner va `tests.py` bilan toʻqnashadi |
| Sahifalar sekinlashmaydimi? | `select_related`/`prefetch_related`; 1381 savolda ham sahifalar 4–12 ta SQL soʻrov bilan ochiladi, N+1 yoʻqligi testda |

## Zaxira: taymer avtomatik yakunlanishini koʻrsatish (ixtiyoriy)

Imtihon ochiq turganida boshqa terminalda (vaqtni 10 soniya qoldiradi):

```bash
python manage.py shell -c "from datetime import timedelta; from django.utils import timezone; from results.models import Exam; Exam.objects.filter(user__username='demo', status='in_progress', mode='exam').update(started_at=timezone.now() - timedelta(seconds=1490))"
```

Imtihon sahifasini yangilang → taymer qizil, 0 da imtihon oʻzi yakunlanadi va natija ochiladi.
