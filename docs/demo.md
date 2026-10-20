# Prava.uz — himoya uchun 5 daqiqalik demo

Maqsad: 5 daqiqada butun foydalanuvchi yoʻlini (oʻquvchi) va boshqaruv panelini (admin) koʻrsatish. Har qadamda **nima bosiladi** va **nima aytiladi**.

## Tayyorgarlik (himoyadan 10 daqiqa oldin)

```bash
python manage.py seed_data --reset   # toza demo maʼlumot: 54 savol, 6 mavzu, admin + demo (3 ta imtihon)
python manage.py runserver
```

- Brauzerda **ikkita oyna**: oddiy (oʻquvchi) va inkognito (admin) — sessiyalar aralashmasin.
- Oʻquvchi oynasida `demo` / `demo12345` bilan kirib qoʻying va **chiqing** (birinchi kirish tezroq ochiladi).
- Ekran oʻlchami: 1440px yoki undan katta; telefon koʻrinishi uchun DevTools → 375px tayyor tursin.
- Zaxira: internet boʻlmasa ham ishlaydi, faqat shriftlar va ikonkalar CDN'dan — oldindan bir marta oching (kesh).

| Login | Parol | Kimligi |
|---|---|---|
| `demo` | `demo12345` | Oʻquvchi, 3 ta tugallangan imtihon (statistika toʻla) |
| `admin` | `admin12345` | Administrator |

## Ssenariy

### 0:00 – 0:30 · Bosh sahifa (mehmon)
- `http://127.0.0.1:8000/` — «Haydovchilik imtihonini birinchi urinishda topshiring».
- **Ayting:** statistika qatoridagi raqamlar bazadan olinadi (54 savol, 6 mavzu, 20 savol / 25 daqiqa, 2 tagacha xato) — soxta raqam yoʻq.

### 0:30 – 1:15 · Yagona kirish → mashq
- «Kirish» → `demo` / `demo12345` → **profilga** tushadi (oʻquvchi roli).
- «Mavzular» → mavzu kartochkalari: progress doirasi, holat («Yangi / Davom etmoqda / Oʻzlashtirildi»), pastda «Kuchsiz mavzularingiz».
- «Yoʻl belgilari» → «Mashq qilish». Bitta savolga **ataylab xato** javob bering → qizil + toʻgʻri javob yashil + izoh. Keyingisiga toʻgʻri javob → «Toʻgʻri javob!» toast.
- **Ayting:** toʻgʻri/xato serverda hisoblanadi, sahifada toʻgʻri javob oldindan yashirilgan.

### 1:15 – 2:45 · Imtihon simulyatori
- «Imtihon» → qoidalar kartasi (20 savol · 25 daqiqa · 2 xatogacha) → «Imtihonni boshlash».
- 3–4 savolga javob bering: klaviatura `1`–`4`, `→` keyingi savol; xato javob darrov qizil (toʻgʻrisi yashil), savollar xaritasida ham katak qizil/yashil boʻladi.
- **F5 bosing** → taymer va javoblar joyida qoladi. **Ayting:** «taymer brauzerda, vaqt nazorati serverda — muddat oʻtgan javob qabul qilinmaydi».
- «Yakunlash» → modal: «N ta savolga javob berilmagan» → «Yakunlash».
- Natija: katta ball doirasi, «Oʻtmadi» (javobsizlar = xato), **xatolar tahlili** — birinchi kartani oching: siz tanlagan (qizil), toʻgʻri (yashil), izoh.

### 2:45 – 3:30 · Profil va statistika
- Avatar → «Profil va statistika»: 4 ta kartochka, natijalar dinamikasi grafigi (oʻtish chegarasi 90%), mavzular boʻyicha foizlar, kuchsiz mavzular, oxirgi imtihonlar jadvali.
- (Ixtiyoriy, 10 soniya) DevTools → 375px: sayt telefonda buzilmaydi, pastda tab bar.

### 3:30 – 4:45 · Admin (inkognito oyna)
- `http://127.0.0.1:8000/admin/` → **yagona login sahifasiga** yoʻnaltiriladi (`?next=/admin/`). `admin` / `admin12345` → **boshqaruv paneli**.
- **Ayting:** bitta login sahifa, rolga qarab yoʻnaltirish; Django'ning oʻz admin login sahifasi oʻchirilgan.
- Dashboard: KPI'lar, 7 kunlik grafik — hozirgina topshirilgan imtihon shu yerda koʻrinadi; «Eng koʻp xato qilinadigan savollar» → qalam ikonkasi.
- Savol formasi (2 ustun): oʻngda **savol statistikasi**. Ikkinchi javobni ham «Toʻgʻri mi» qilib **Saqlash** → xato: «Aynan bitta javob toʻgʻri deb belgilanishi kerak». Bekor qiling.
- «Savollar» roʻyxati: filtrlar (mavzu, rasmli, izohsiz), bir nechta savolni belgilab «Tanlanganlarni oʻchirib qoʻyish (nofaol)» amalini koʻrsating (bajarmasdan).
- «Imtihonlar» → bitta imtihon: faqat koʻrish, ichida 20 ta savol va javoblar.

### 4:45 – 5:00 · Huquqlar
- Oʻquvchi oynasida manzilga `/admin/` yozing → profilga qaytadi: «Bu boʻlimga faqat administratorlar kira oladi».
- **Yakun:** «Qabul mezonlari testlar bilan tasdiqlangan — `python manage.py test`: 71 ta test».

## Ehtimoliy savollar va qisqa javoblar

| Savol | Javob |
|---|---|
| Nega MySQL emas, PostgreSQL? | Muallif qarori: drayver Windows'da kompilyatsiyasiz oʻrnatiladi, `select_for_update` haqiqiy qulf beradi, DDL tranzaksiyali. Hujjatdagi 6 jadval nomi saqlangan (`db_table`). `NOTES.md` |
| Vaqtni qanday aldab boʻlmaydi? | Deadline = `started_at + 25 daqiqa`, har javob va yakunlashda serverda tekshiriladi; muddat oʻtsa imtihon `expired` boʻladi |
| Natija qanday hisoblanadi? | `results/services.py` → `finish_exam`: toʻgʻri javoblar soni; xato = 20 − toʻgʻri (javobsiz ham xato); ≤ 2 xato → oʻtdi. Testlar: 18/20 oʻtdi, 17/20 oʻtmadi |
| Begona natijani koʻrish mumkinmi? | Yoʻq — har soʻrov `user=request.user` bilan filtrlanadi, aks holda 404 |
| Nega app nomi `quiz`, hujjatda `tests`? | Django'da `tests` nomi test-runner va `tests.py` bilan toʻqnashadi |
| Sahifalar sekinlashmaydimi? | `select_related`/`prefetch_related`; N+1 yoʻqligi testda: maʼlumot koʻpaysa ham soʻrovlar soni oʻzgarmaydi |

## Zaxira: taymer avtomatik yakunlanishini koʻrsatish (ixtiyoriy)

Imtihon ochiq turganida boshqa terminalda (vaqtni 10 soniya qoldiradi):

```bash
python manage.py shell -c "from datetime import timedelta; from django.utils import timezone; from results.models import Exam; Exam.objects.filter(user__username='demo', status='in_progress', mode='exam').update(started_at=timezone.now() - timedelta(seconds=1490))"
```

Imtihon sahifasini yangilang → taymer qizil, 0 da imtihon oʻzi yakunlanadi va natija ochiladi.
