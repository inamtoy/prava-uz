import json
import random
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from quiz.models import Answer, Question, Topic
from quiz.signs import SIGNS
from results.models import Exam, ExamAnswer

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "questions_uz.json"


class Command(BaseCommand):
    help = "Namuna maʼlumotlar: mavzular, savollar, rasmlar, admin va demo foydalanuvchi."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Mavzular, savollar va demo maʼlumotlarni oʻchirib qayta yaratish (faqat DEBUG=True)")
        parser.add_argument("--demo", action="store_true", help="DEBUG=False boʻlsa ham demo oʻquvchini yaratish")

    @transaction.atomic
    def handle(self, *args, reset=False, demo=False, **options):
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

        created = self._load_questions()
        self._create_users(with_demo=settings.DEBUG or demo)
        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {Topic.objects.count()} mavzu, {Question.objects.count()} savol ({created} ta yangi)."
        ))

    def _load_questions(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        created_count = 0
        for t in data["topics"]:
            topic, _ = Topic.objects.update_or_create(
                slug=t["slug"],
                defaults={"name": t["name"], "description": t.get("description", ""), "order": t.get("order", 0)},
            )
            for q in t["questions"]:
                question, created = Question.objects.get_or_create(
                    topic=topic, text=q["text"], defaults={"explanation": q.get("explanation", "")},
                )
                if q.get("image") and not question.image:
                    self._attach_image(question, q["image"])
                if created:
                    created_count += 1
                    Answer.objects.bulk_create([
                        Answer(question=question, text=text, is_correct=(i == q["correct"]))
                        for i, text in enumerate(q["answers"])
                    ])
        return created_count

    def _attach_image(self, question, filename):
        draw = SIGNS.get(filename)
        if draw is None:
            self.stderr.write(f"Rasm generatori topilmadi: {filename}")
            return
        buf = BytesIO()
        draw().save(buf, format="PNG")
        question.image.save(filename, ContentFile(buf.getvalue()), save=True)

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
            (Exam.MODE_PRACTICE, "yol-belgilari", 0.7, 5),
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
