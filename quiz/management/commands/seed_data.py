import random
from datetime import timedelta
from itertools import groupby

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from quiz.models import Answer, Question, Topic
from quiz.xlsx_import import read_questions
from results.models import Exam, ExamAnswer

QUESTIONS_FILE = settings.BASE_DIR / "savollar" / "avtotest_savollar_javoblar.xlsx"


class Command(BaseCommand):
    help = "Savollarni Excel fayldan yuklash (biletlar, savollar, rasmlar) + admin va demo foydalanuvchi."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Mavzular, savollar va demo maʼlumotlarni oʻchirib qayta yaratish (faqat DEBUG=True)")
        parser.add_argument("--demo", action="store_true", help="DEBUG=False boʻlsa ham demo oʻquvchini yaratish")
        parser.add_argument("--file", default=str(QUESTIONS_FILE), help="Savollar Excel fayli (.xlsx)")

    @transaction.atomic
    def handle(self, *args, reset=False, demo=False, file=None, **options):
        if reset and not settings.DEBUG:
            # Serverda barcha foydalanuvchilarning imtihon tarixini o'chirib yubormaslik uchun
            raise CommandError("--reset faqat DEBUG=True (lokal) muhitda ishlaydi.")
        if reset:
            Exam.objects.all().delete()
            for question in Question.objects.exclude(image=""):
                question.image.delete(save=False)  # media/ da eski fayllar qolmasin
            Topic.objects.all().delete()
            User.objects.filter(username__in=["admin", "demo"]).delete()
            self.stdout.write("Eski maʼlumotlar oʻchirildi.")

        created = self._load_questions(file or QUESTIONS_FILE)
        self._create_users(with_demo=settings.DEBUG or demo)
        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {Topic.objects.count()} bilet, {Question.objects.count()} savol ({created} ta yangi)."
        ))

    def _load_questions(self, path):
        try:
            rows = read_questions(path)
        except (OSError, KeyError, ValueError) as e:
            raise CommandError(f"Savollar faylini oʻqib boʻlmadi ({path}): {e}")
        bad = [r for r in rows if r.problems]
        for r in bad:
            self.stderr.write(f"{r.number}-qator ({r.ticket}-bilet, {r.position}-savol) oʻtkazib yuborildi: {', '.join(r.problems)}")
        rows = sorted((r for r in rows if not r.problems), key=lambda r: (r.ticket, r.position or 0))

        created_count = 0
        for ticket, group in groupby(rows, key=lambda r: r.ticket):
            topic, _ = Topic.objects.update_or_create(
                slug=f"bilet-{ticket}", defaults={"name": f"{ticket}-bilet", "order": ticket},
            )
            if topic.questions.exists():
                continue  # bilet avval yuklangan — qayta ishga tushirilsa dublikat yaratilmaydi
            group = list(group)
            questions = Question.objects.bulk_create([
                Question(
                    topic=topic, text=r.text,
                    image=self._save_image(r) if r.image else None,
                    # Rasmi PDFda yo'qolgan savolni rasmsiz ko'rsatib bo'lmaydi — admin rasmni qo'shib faollashtiradi
                    is_active=not r.image_missing,
                )
                for r in group
            ])
            Answer.objects.bulk_create([
                Answer(question=q, text=text, is_correct=(i == r.correct))
                for q, r in zip(questions, group)
                for i, text in enumerate(r.answers)
            ])
            created_count += len(questions)
        inactive = sum(r.image_missing for r in rows)
        if created_count and inactive:
            self.stdout.write(self.style.WARNING(f"{inactive} ta savolning rasmi faylda yoʻq — ular nofaol qilib qoʻyildi."))
        return created_count

    def _save_image(self, row):
        name = row.image_name or f"b{row.ticket:03d}_s{row.position:02d}.jpeg"
        return default_storage.save(f"questions/{name}", ContentFile(row.image))

    def _create_users(self, with_demo):
        if settings.DEBUG:
            if not User.objects.filter(username="admin").exists():
                User.objects.create_user("admin", "admin@prava.uz", "admin12345", role=User.ROLE_ADMIN, first_name="Admin")
                self.stdout.write("Admin yaratildi: admin / admin12345")
        else:
            self.stdout.write(self.style.WARNING("DEBUG=False: demo admin yaratilmadi (createsuperuser dan foydalaning)."))

        if not with_demo:
            self.stdout.write(self.style.WARNING("DEBUG=False: demo oʻquvchi yaratilmadi (kerak boʻlsa: --demo)."))
            return
        demo = User.objects.filter(username="demo").first()
        if demo is None:
            demo = User.objects.create_user("demo", "demo@prava.uz", "demo12345", first_name="Demo")
            self.stdout.write("Demo oʻquvchi yaratildi: demo / demo12345")
        if not demo.exams.exists():
            self._create_demo_exams(demo)

    def _create_demo_exams(self, user):
        rng = random.Random(42)
        now = timezone.now()
        questions = list(Question.objects.filter(is_active=True).prefetch_related("answers"))
        # (rejim, mavzu slug, to'g'ri javob ehtimoli, necha kun oldin)
        plans = [
            (Exam.MODE_PRACTICE, "bilet-1", 0.7, 5),
            (Exam.MODE_EXAM, None, 0.75, 3),
            (Exam.MODE_EXAM, None, 0.97, 1),
        ]
        for mode, slug, accuracy, days_ago in plans:
            topic = Topic.objects.get(slug=slug) if slug else None
            pool = [q for q in questions if topic is None or q.topic_id == topic.pk]
            picked = rng.sample(pool, min(settings.EXAM_QUESTION_COUNT, len(pool)))
            started = now - timedelta(days=days_ago, minutes=30)
            exam = Exam.objects.create(
                user=user, mode=mode, topic=topic, total_questions=len(picked),
                duration_seconds=settings.EXAM_DURATION_SECONDS,
            )
            items, score = [], 0
            for order, q in enumerate(picked, start=1):
                answers = list(q.answers.all())
                correct = next(a for a in answers if a.is_correct)
                choice = correct if rng.random() < accuracy else rng.choice([a for a in answers if not a.is_correct])
                score += choice.is_correct
                items.append(ExamAnswer(
                    exam=exam, question=q, selected_answer=choice, is_correct=choice.is_correct,
                    order=order, answered_at=started + timedelta(seconds=40 * order),
                ))
            ExamAnswer.objects.bulk_create(items)
            # started_at auto_now_add — o'tmish sanasini update() bilan qo'yamiz
            Exam.objects.filter(pk=exam.pk).update(
                started_at=started,
                finished_at=started + timedelta(minutes=15),
                score=score,
                status=Exam.STATUS_FINISHED,
                is_passed=(len(picked) - score <= settings.EXAM_MAX_MISTAKES) if mode == Exam.MODE_EXAM else None,
            )
        self.stdout.write("Demo foydalanuvchiga 3 ta tugallangan imtihon qoʻshildi.")
