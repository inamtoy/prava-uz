# Prava.uz — mobil ilova (Flutter)

Saytning mobil versiyasi: biletlar bo'yicha mashq, 20 savollik imtihon (25 daqiqa taymer), natija va xatolar tahlili, profil statistikasi. Ma'lumotlar Django serveridagi `/api/v1/` dan olinadi (internet kerak).

## Ishga tushirish (Android emulyator)

1. Serverni ishga tushiring (loyiha ildizida): `python manage.py runserver`
   `.env` da `ALLOWED_HOSTS` ichida `10.0.2.2` bo'lishi kerak.
2. Emulyatorni oching va:
   ```bash
   cd mobile
   flutter pub get
   flutter run
   ```
   Sukut bo'yicha ilova `http://10.0.2.2:8000/api/v1` ga ulanadi (emulyator ichidan kompyuter manzili).

Haqiqiy telefon yoki server uchun manzilni bering:
```bash
flutter run --dart-define=API_BASE=http://192.168.1.10:8000/api/v1
flutter build apk --release --dart-define=API_BASE=https://prava.uz/api/v1
```
(Telefondan kompyuterga ulanish uchun `runserver 0.0.0.0:8000` va `ALLOWED_HOSTS` ga kompyuter IP manzilini qo'shing. Release build faqat HTTPS bilan ishlaydi.)

Demo login: `demo` / `demo12345`.

## Tuzilma

```
lib/
  main.dart            ilova, token bo'lsa — asosiy ekran, bo'lmasa — kirish
  config.dart          API_BASE
  api.dart             HTTP klient, token (shared_preferences), xatolar
  theme.dart           "Yo'l belgisi" ranglari va shriftlari (sayt bilan bir xil)
  widgets/common.dart  logo, cheklov belgisi, xato bloki
  screens/             auth, home_shell (pastki menyu), topics, exam_start, quiz, result, profile
test/widget_test.dart  ekran testlari (tarmoqsiz)
```

## API (`/api/v1/`, `Authorization: Token <key>`)

| Metod | Yo'l | Vazifa |
|---|---|---|
| POST | `auth/register/`, `auth/login/` | `{token, user}` (login — username yoki email) |
| POST | `auth/logout/` | tokenni o'chiradi |
| GET | `me/`, `config/`, `topics/`, `stats/` | foydalanuvchi, imtihon sozlamalari, biletlar (progress bilan), statistika |
| POST | `topics/<slug>/practice/` | mashq sessiyasi |
| GET / POST | `exams/` | ochiq imtihon / imtihon boshlash (ochiq bo'lsa davom ettiradi) |
| GET | `sessions/<id>/` | savollar (to'g'ri javob faqat javob berilgandan keyin) |
| POST | `sessions/<id>/answer/` | `{question_id, answer_id}` → `{is_correct, correct_answer_id, explanation, time_left}`; muddat o'tgan → 409 |
| POST | `sessions/<id>/finish/`, GET `sessions/<id>/result/` | natija va xatolar |

## Testlar

```bash
flutter analyze
flutter test
python manage.py test api   # loyiha ildizida — API testlari
```
