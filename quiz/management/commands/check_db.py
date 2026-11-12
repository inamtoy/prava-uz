"""Bazani tekshirish: ulanish, migratsiyalar, ma'lumotlar yaxlitligi.

    python manage.py check_db            # faqat o'qiydi, hech narsani o'zgartirmaydi
    python manage.py check_db --details  # har bir muammoli yozuvning ID'larini ham chiqaradi

Chiqish kodi: 0 — xato yo'q (ogohlantirishlar bo'lishi mumkin), 1 — XATO topildi.
"""
import os
from collections import Counter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Count, F, Q
from django.db.models.functions import Lower
from django.utils import timezone

from quiz.models import Answer, Question, Topic
from results.models import Exam, ExamAnswer


class Command(BaseCommand):
    help = "Bazani tekshiradi (faqat o'qish): ulanish, migratsiyalar, savol/javob va imtihon ma'lumotlari."

    def add_arguments(self, parser):
        parser.add_argument("--details", action="store_true", help="Muammoli yozuvlarning ID'larini ko'rsatish")

    # ---------- chiqarish ----------
    def _ids(self, qs_or_list, limit=30):
        ids = list(qs_or_list.values_list("pk", flat=True)[: limit + 1]) if hasattr(qs_or_list, "values_list") else list(qs_or_list)[: limit + 1]
        more = "…" if len(ids) > limit else ""
        return ", ".join(str(i) for i in ids[:limit]) + more

    def ok(self, msg):
        self.stdout.write(self.style.SUCCESS("  [OK]   ") + msg)

    def warn(self, msg, ids=None):
        self.warnings += 1
        self.stdout.write(self.style.WARNING("  [OGOH] ") + msg)
        if ids is not None and self.details:
            self.stdout.write(f"         ID: {self._ids(ids)}")

    def err(self, msg, ids=None):
        self.errors += 1
        self.stdout.write(self.style.ERROR("  [XATO] ") + msg)
        if ids is not None and self.details:
            self.stdout.write(f"         ID: {self._ids(ids)}")

    def section(self, title):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(title))

    def expect(self, qs, ok_msg, bad_msg, level="err"):
        n = qs.count() if hasattr(qs, "count") else len(qs)
        if n:
            (self.err if level == "err" else self.warn)(bad_msg.format(n=n), qs)
        else:
            self.ok(ok_msg)
        return n

    # ---------- asosiy ----------
    def handle(self, *args, **opts):
        self.details = opts["details"]
        self.errors = 0
        self.warnings = 0

        self.check_connection()
        if not self.check_migrations():
            self.summary()
            return
        self.check_counts()
        self.check_topics()
        self.check_questions()
        self.check_images()
        self.check_users()
        self.check_exams()
        self.check_sequences()
        self.check_sessions()
        self.summary()

    def summary(self):
        self.section("Xulosa")
        if self.errors:
            self.stdout.write(self.style.ERROR(f"  {self.errors} ta xato, {self.warnings} ta ogohlantirish."))
            self.stdout.write("  Tafsilot uchun: python manage.py check_db --details")
            raise SystemExit(1)
        if self.warnings:
            self.stdout.write(self.style.WARNING(f"  Xato yo'q, {self.warnings} ta ogohlantirish."))
        else:
            self.stdout.write(self.style.SUCCESS("  Hammasi joyida."))

    # 1. Ulanish
    def check_connection(self):
        self.section("1. Ulanish")
        db = settings.DATABASES["default"]
        with connection.cursor() as c:
            if connection.vendor == "postgresql":
                c.execute("SELECT version(), pg_encoding_to_char(encoding), pg_size_pretty(pg_database_size(current_database())) "
                          "FROM pg_database WHERE datname = current_database()")
                version, encoding, size = c.fetchone()
                self.ok(f"PostgreSQL: {version.split(',')[0]}")
                self.ok(f"Baza: {db['NAME']} @ {db.get('HOST') or 'localhost'}:{db.get('PORT') or 5432}, hajmi {size}")
                if encoding != "UTF8":
                    self.err(f"Baza kodirovkasi {encoding} — UTF8 bo'lishi kerak (o'zbekcha harflar buziladi)")
                else:
                    self.ok("Kodirovka: UTF8")
            else:
                c.execute("SELECT sqlite_version()")
                self.ok(f"SQLite {c.fetchone()[0]}: {db['NAME']}")
                c.execute("PRAGMA integrity_check")
                res = c.fetchone()[0]
                (self.ok if res == "ok" else self.err)(f"integrity_check: {res}")
                c.execute("PRAGMA foreign_key_check")
                bad = c.fetchall()
                if bad:
                    self.err(f"Buzilgan tashqi kalitlar: {len(bad)} ta")
                else:
                    self.ok("Tashqi kalitlar butun")

    # 2. Migratsiyalar
    def check_migrations(self):
        self.section("2. Migratsiyalar")
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            names = ", ".join(f"{m.app_label}.{m.name}" for m, _ in plan)
            self.err(f"Qo'llanmagan migratsiyalar ({len(plan)} ta): {names}. Bajaring: python manage.py migrate")
            return False
        self.ok("Barcha migratsiyalar qo'llangan")
        return True

    # 3. Sonlar
    def check_counts(self):
        self.section("3. Jadvallar")
        User = get_user_model()
        rows = [
            ("foydalanuvchilar", User.objects.count()),
            ("mavzular (biletlar)", Topic.objects.count()),
            ("savollar", Question.objects.count()),
            ("  shundan faol", Question.objects.filter(is_active=True).count()),
            ("javoblar", Answer.objects.count()),
            ("imtihonlar", Exam.objects.filter(mode=Exam.MODE_EXAM).count()),
            ("mashqlar", Exam.objects.filter(mode=Exam.MODE_PRACTICE).count()),
            ("imtihon javoblari", ExamAnswer.objects.count()),
        ]
        for name, n in rows:
            self.stdout.write(f"         {name:<22} {n:>7}")
        active = rows[3][1]
        if active < settings.EXAM_QUESTION_COUNT:
            self.err(f"Faol savollar {active} ta — imtihon uchun kamida {settings.EXAM_QUESTION_COUNT} ta kerak")

    # 4. Biletlar
    def check_topics(self):
        self.section("4. Biletlar")
        topics = Topic.objects.annotate(n=Count("questions", filter=Q(questions__is_active=True)))
        self.expect(topics.filter(n=0), "Har bir biletda faol savol bor",
                   "{n} ta biletda faol savol yo'q (bosh sahifada ko'rinmaydi, mashq boshlanmaydi)", "warn")
        dup = [o for o, c in Counter(Topic.objects.values_list("order", flat=True)).items() if c > 1]
        if dup:
            self.warn(f"Bir xil tartib raqamli biletlar: {', '.join(map(str, sorted(dup)[:20]))} (bosh sahifadagi raqamlar takrorlanadi)")
        else:
            self.ok("Bilet tartib raqamlari takrorlanmaydi")
        self.expect(Topic.objects.filter(Q(name="") | Q(slug="")), "Bilet nomi va slug to'ldirilgan",
                   "{n} ta biletda nom yoki slug bo'sh")

    # 5. Savollar va javoblar
    def check_questions(self):
        self.section("5. Savollar va javoblar")
        active = Question.objects.filter(is_active=True).annotate(
            total=Count("answers"), correct=Count("answers", filter=Q(answers__is_correct=True))
        )
        self.expect(active.exclude(correct=1), "Har bir faol savolda aynan 1 ta to'g'ri javob",
                   "{n} ta faol savolda to'g'ri javob soni 1 emas (0 yoki bir nechta)")
        self.expect(active.filter(Q(total__lt=2) | Q(total__gt=4)), "Har bir faol savolda 2–4 ta javob",
                   "{n} ta faol savolda javoblar soni 2–4 oralig'ida emas")
        self.expect(Question.objects.filter(text__regex=r"^\s*$"), "Savol matnlari bo'sh emas",
                   "{n} ta savolning matni bo'sh")
        self.expect(Answer.objects.filter(text__regex=r"^\s*$"), "Javob matnlari bo'sh emas",
                   "{n} ta javobning matni bo'sh")
        self.expect(Question.objects.filter(is_active=True, explanation=""), "Har bir faol savolda izoh bor",
                   "{n} ta faol savolda izoh (explanation) yo'q — mashqda izoh chiqmaydi", "warn")

        # Bir savolda bir xil matnli javoblar
        dup_ans = (Answer.objects.annotate(t=Lower("text")).values("question_id", "t")
                   .annotate(c=Count("id")).filter(c__gt=1).values_list("question_id", flat=True))
        self.expect(Question.objects.filter(pk__in=list(dup_ans)), "Bitta savol ichida takroriy javoblar yo'q",
                   "{n} ta savolda bir xil matnli javoblar bor", "warn")

        # Takroriy savollar: matni ham, rasmi ham bir xil
        dup_q = (Question.objects.filter(is_active=True).values("text", "image")
                 .annotate(c=Count("id")).filter(c__gt=1))
        n = dup_q.count()
        if n:
            ids = []
            for row in dup_q[:30]:
                ids += list(Question.objects.filter(is_active=True, text=row["text"], image=row["image"])
                            .values_list("pk", flat=True))
            self.warn(f"{n} xil savol bir necha marta takrorlangan (matni va rasmi bir xil)", ids)
        else:
            self.ok("Takroriy savollar yo'q")

    # 6. Rasmlar
    def check_images(self):
        self.section("6. Savol rasmlari")
        with_img = Question.objects.exclude(image="").exclude(image__isnull=True).only("id", "image")
        total = with_img.count()
        missing = [q.pk for q in with_img.iterator() if not os.path.exists(os.path.join(settings.MEDIA_ROOT, q.image.name))]
        if missing:
            self.err(f"{len(missing)} / {total} ta savolning rasm fayli diskda yo'q ({settings.MEDIA_ROOT})", missing)
        else:
            self.ok(f"Rasmli {total} ta savolning barcha fayllari joyida")

    # 7. Foydalanuvchilar
    def check_users(self):
        self.section("7. Foydalanuvchilar")
        User = get_user_model()
        admins = User.objects.filter(is_staff=True, is_active=True).count()
        if admins:
            self.ok(f"Faol adminlar: {admins} ta")
        else:
            self.err("Faol admin yo'q — boshqaruv paneliga hech kim kira olmaydi")
        self.expect(User.objects.filter(Q(role="admin", is_staff=False) | Q(role="student", is_staff=True)),
                   "Rol va is_staff mos", "{n} ta foydalanuvchida rol va is_staff mos emas", "warn")
        dup = (User.objects.annotate(e=Lower("email")).values("e").annotate(c=Count("id"))
               .filter(c__gt=1).values_list("e", flat=True))
        self.expect(User.objects.annotate(e=Lower("email")).filter(e__in=list(dup)),
                   "Email manzillar takrorlanmaydi (katta-kichik harfni hisobga olmay)",
                   "{n} ta foydalanuvchi bir xil emailga ega (katta-kichik harf farqi bilan) — email bilan kirishda chalkashlik", "warn")
        if settings.DEBUG is False and User.objects.filter(username__in=["admin", "demo"]).exists():
            self.warn("Production'da demo loginlar (admin/demo) bor — parollarini o'zgartiring yoki o'chiring")

    # 8. Imtihonlar
    def check_exams(self):
        self.section("8. Imtihon va mashqlar")
        now = timezone.now()
        done = [Exam.STATUS_FINISHED, Exam.STATUS_EXPIRED]
        exams = Exam.objects.annotate(
            n_items=Count("items"), n_correct=Count("items", filter=Q(items__is_correct=True))
        )

        stuck = [e.pk for e in Exam.objects.filter(mode=Exam.MODE_EXAM, status=Exam.STATUS_IN_PROGRESS).only("pk", "started_at", "duration_seconds")
                 if now > e.started_at + timezone.timedelta(seconds=e.duration_seconds)]
        if stuck:
            self.warn(f"{len(stuck)} ta imtihon vaqti o'tgan, lekin 'jarayonda' qolgan (foydalanuvchi qaytganda avtomatik yakunlanadi)", stuck)
        else:
            self.ok("Vaqti o'tib, osilib qolgan imtihon yo'q")

        self.expect(exams.exclude(n_items=F("total_questions")), "Savollar soni total_questions bilan mos",
                   "{n} ta imtihonda haqiqiy savollar soni total_questions dan farq qiladi")
        self.expect(exams.filter(status__in=done).exclude(score=F("n_correct")), "Yakunlangan imtihonlar balli to'g'ri hisoblangan",
                   "{n} ta yakunlangan imtihonda score to'g'ri javoblar soniga teng emas")
        self.expect(Exam.objects.filter(status__in=done, finished_at__isnull=True), "Yakunlanganlarda finished_at bor",
                   "{n} ta yakunlangan imtihonda finished_at bo'sh")

        limit = settings.EXAM_MAX_MISTAKES
        bad_pass = Exam.objects.filter(mode=Exam.MODE_EXAM, status__in=done).filter(
            Q(is_passed=True, score__lt=F("total_questions") - limit)
            | Q(is_passed=False, score__gte=F("total_questions") - limit)
            | Q(is_passed__isnull=True)
        )
        self.expect(bad_pass, "O'tdi/o'tmadi natijalari qoidaga mos", "{n} ta imtihonda o'tdi/o'tmadi noto'g'ri belgilangan")

        # Javoblar
        self.expect(ExamAnswer.objects.filter(selected_answer__isnull=False).exclude(selected_answer__question_id=F("question_id")),
                   "Tanlangan javoblar o'z savoliga tegishli",
                   "{n} ta yozuvda tanlangan javob boshqa savolga tegishli")
        self.expect(ExamAnswer.objects.filter(selected_answer__isnull=False).exclude(is_correct=F("selected_answer__is_correct")),
                   "ExamAnswer.is_correct javob kalitiga mos",
                   "{n} ta yozuvda is_correct javob kalitiga mos emas (savol javobi keyin o'zgartirilgan bo'lishi mumkin)", "warn")
        self.expect(ExamAnswer.objects.filter(selected_answer__isnull=True, is_correct=True),
                   "Javobsiz savollar to'g'ri deb belgilanmagan", "{n} ta javobsiz savol to'g'ri deb belgilangan")
        self.expect(ExamAnswer.objects.filter(question__is_active=False, exam__status=Exam.STATUS_IN_PROGRESS),
                   "Jarayondagi imtihonlarda o'chirilgan (nofaol) savol yo'q",
                   "{n} ta jarayondagi imtihon savoli nofaol qilingan", "warn")

    # 9. PostgreSQL ketma-ketliklari (loaddata'dan keyin tez-tez buziladi)
    def check_sequences(self):
        if connection.vendor != "postgresql":
            return
        self.section("9. ID ketma-ketliklari (sequence)")
        User = get_user_model()
        models = [User, Topic, Question, Answer, Exam, ExamAnswer]
        bad = []
        with connection.cursor() as c:
            for m in models:
                table, pk = m._meta.db_table, m._meta.pk.column
                c.execute("SELECT pg_get_serial_sequence(%s, %s)", [table, pk])
                seq = c.fetchone()[0]
                if not seq:
                    continue
                c.execute(f'SELECT COALESCE(MAX("{pk}"), 0) FROM "{table}"')
                max_id = c.fetchone()[0]
                c.execute(f"SELECT last_value, is_called FROM {seq}")
                last, called = c.fetchone()
                nxt = last + 1 if called else last
                if nxt <= max_id:
                    bad.append(f"{table} (keyingi ID {nxt}, mavjud max {max_id})")
        if bad:
            self.err("Sequence orqada qolgan — yangi yozuv qo'shishda 'duplicate key' xatosi chiqadi: " + "; ".join(bad)
                     + ". Tuzatish: python manage.py sqlsequencereset accounts quiz results | python manage.py dbshell")
        else:
            self.ok("Barcha ID ketma-ketliklari to'g'ri")

    # 10. Sessiyalar
    def check_sessions(self):
        self.section("10. Sessiyalar")
        expired = Session.objects.filter(expire_date__lt=timezone.now()).count()
        if expired > 1000:
            self.warn(f"{expired} ta eskirgan sessiya — tozalash: python manage.py clearsessions")
        else:
            self.ok(f"Eskirgan sessiyalar: {expired} ta")
