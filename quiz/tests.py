import io

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Question, Topic


class QuestionAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("boss", "boss@example.com", "parol12345", role="admin")
        self.client.force_login(self.admin)
        self.topic = Topic.objects.create(name="Belgilar", slug="belgilar")
        self.url = reverse("admin:quiz_question_add")

    def _payload(self, correct_flags, texts=None):
        texts = texts or ["A", "B", "C", "D"]
        data = {
            "topic": self.topic.pk,
            "text": "Savol?",
            "explanation": "",
            "is_active": "on",
            "answers-TOTAL_FORMS": "4",
            "answers-INITIAL_FORMS": "0",
            "answers-MIN_NUM_FORMS": "0",
            "answers-MAX_NUM_FORMS": "4",
        }
        for i, text in enumerate(texts):
            data[f"answers-{i}-text"] = text
            if correct_flags[i]:
                data[f"answers-{i}-is_correct"] = "on"
        return data

    def test_admin_role_sets_is_staff(self):
        self.assertTrue(self.admin.is_staff)
        student = User.objects.create_user("s", "s@example.com", "parol12345")
        self.assertFalse(student.is_staff)

    def test_valid_question_with_four_answers(self):
        resp = self.client.post(self.url, self._payload([True, False, False, False]))
        self.assertEqual(resp.status_code, 302)
        q = Question.objects.get()
        self.assertEqual(q.answers.count(), 4)
        self.assertEqual(q.answers.filter(is_correct=True).count(), 1)

    def test_two_correct_answers_rejected(self):
        resp = self.client.post(self.url, self._payload([True, True, False, False]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Aynan bitta javob")
        self.assertFalse(Question.objects.exists())

    def test_no_correct_answer_rejected(self):
        resp = self.client.post(self.url, self._payload([False, False, False, False]))
        self.assertContains(resp, "Aynan bitta javob")

    def test_single_answer_rejected(self):
        resp = self.client.post(self.url, self._payload([True, False, False, False], ["A", "", "", ""]))
        self.assertContains(resp, "kamida 2 ta javob")


class SeedDataTests(TestCase):
    def test_seed_is_idempotent_and_valid(self):
        import tempfile

        from django.core.management import call_command
        from django.db.models import Count, Q

        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media, DEBUG=True):
            call_command("seed_data", stdout=io.StringIO())
            call_command("seed_data", stdout=io.StringIO())
            self.assertEqual(Topic.objects.count(), 6)
            self.assertGreaterEqual(Question.objects.count(), 50)
            counts = Question.objects.annotate(
                n=Count("answers"), ok=Count("answers", filter=Q(answers__is_correct=True))
            )
            self.assertFalse(counts.exclude(n=4).exists())
            self.assertFalse(counts.exclude(ok=1).exists())
            self.assertGreaterEqual(Question.objects.exclude(image="").exclude(image=None).count(), 4)
            self.assertEqual(User.objects.get(username="demo").exams.count(), 3)
            self.assertTrue(User.objects.get(username="admin").is_staff)


class PracticeFlowTests(TestCase):
    def setUp(self):
        from results.tests import make_questions

        self.user = User.objects.create_user("ali", "ali@example.com", "Kuchli-parol-2026")
        self.client.force_login(self.user)
        self.topic = Topic.objects.create(name="Belgilar", slug="belgilar")
        make_questions(self.topic, 5)

    def test_topic_list_shows_counts(self):
        resp = self.client.get(reverse("topic_list"))
        self.assertContains(resp, "Belgilar")
        self.assertContains(resp, "5 ta savol")

    def test_practice_start_requires_post(self):
        self.assertEqual(self.client.get(reverse("practice_start", args=["belgilar"])).status_code, 405)

    def test_practice_flow(self):
        from results.models import Exam

        resp = self.client.post(reverse("practice_start", args=["belgilar"]))
        exam = Exam.objects.get(user=self.user)
        self.assertRedirects(resp, reverse("practice", args=[exam.pk]))
        page = self.client.get(reverse("practice", args=[exam.pk]))
        self.assertEqual(page.status_code, 200)
        # To'g'ri javob belgisi sahifada oldindan oshkor qilinmaydi
        self.assertNotContains(page, "answer-btn correct")
        self.assertNotContains(page, "is_correct")

        item = exam.items.select_related("question").first()
        wrong = item.question.answers.filter(is_correct=False).first()
        right = item.question.answers.get(is_correct=True)
        api = reverse("exam_answer", args=[exam.pk])
        data = self.client.post(api, {"question_id": item.question_id, "answer_id": wrong.pk}, content_type="application/json").json()
        self.assertEqual(data, {
            "ok": True, "is_correct": False, "selected_answer_id": wrong.pk,
            "correct_answer_id": right.pk, "explanation": item.question.explanation,
        })
        bad = self.client.post(api, {"question_id": item.question_id}, content_type="application/json")
        self.assertEqual(bad.status_code, 400)

        resp = self.client.post(reverse("exam_finish", args=[exam.pk]))
        self.assertRedirects(resp, reverse("result", args=[exam.pk]))
        exam.refresh_from_db()
        self.assertEqual(exam.status, Exam.STATUS_FINISHED)

    def test_foreign_practice_is_404(self):
        from results import services

        other = User.objects.create_user("vali", "vali@example.com", "Kuchli-parol-2026")
        exam = services.start_practice(other, self.topic)
        self.assertEqual(self.client.get(reverse("practice", args=[exam.pk])).status_code, 404)
        item = exam.items.first()
        resp = self.client.post(
            reverse("exam_answer", args=[exam.pk]),
            {"question_id": item.question_id, "answer_id": item.question.answers.first().pk},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_api_requires_csrf(self):
        from django.test import Client

        from results import services

        exam = services.start_practice(self.user, self.topic)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        item = exam.items.first()
        resp = client.post(
            reverse("exam_answer", args=[exam.pk]),
            {"question_id": item.question_id, "answer_id": item.question.answers.first().pk},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


class ExamFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from results.tests import make_questions

        cls.user = User.objects.create_user("ali", "ali@example.com", "Kuchli-parol-2026")
        cls.other = User.objects.create_user("vali", "vali@example.com", "Kuchli-parol-2026")
        topic = Topic.objects.create(name="Umumiy", slug="umumiy")
        make_questions(topic, 25)

    def setUp(self):
        self.client.force_login(self.user)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        resp = self.client.get(reverse("exam_start"))
        self.assertRedirects(resp, reverse("login") + "?next=" + reverse("exam_start"))

    def test_full_exam_flow(self):
        from results.models import Exam

        self.assertContains(self.client.get(reverse("exam_start")), "Imtihonni boshlash")
        resp = self.client.post(reverse("exam_start"))
        exam = Exam.objects.get(user=self.user)
        self.assertRedirects(resp, reverse("exam", args=[exam.pk]))

        page = self.client.get(reverse("exam", args=[exam.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'class="question-card', count=20)
        self.assertContains(page, 'data-time-left="')
        self.assertNotContains(page, "answer-btn correct")

        api = reverse("exam_answer", args=[exam.pk])
        for i, item in enumerate(exam.items.select_related("question")):
            answers = item.question.answers.all()
            answer = answers.filter(is_correct=False).first() if i == 0 else answers.get(is_correct=True)
            data = self.client.post(api, {"question_id": item.question_id, "answer_id": answer.pk}, content_type="application/json").json()
            self.assertTrue(data["ok"])
            self.assertNotIn("is_correct", data)  # imtihonda to'g'ri/xato oshkor qilinmaydi
            self.assertNotIn("correct_answer_id", data)
            self.assertGreater(data["time_left"], 0)

        # Sahifa yangilansa o'sha savollar chiqadi, tanlangan javoblar saqlangan
        page = self.client.get(reverse("exam", args=[exam.pk]))
        self.assertContains(page, "nav-num answered", count=20)

        resp = self.client.post(reverse("exam_finish", args=[exam.pk]))
        self.assertRedirects(resp, reverse("result", args=[exam.pk]))
        exam.refresh_from_db()
        self.assertEqual(exam.score, 19)
        self.assertTrue(exam.is_passed)
        self.assertEqual(self.client.get(reverse("result", args=[exam.pk])).status_code, 200)
        # Yakunlangan imtihon sahifasi natijaga yo'naltiradi
        self.assertRedirects(self.client.get(reverse("exam", args=[exam.pk])), reverse("result", args=[exam.pk]))

    def test_start_twice_resumes(self):
        from results.models import Exam

        self.client.post(reverse("exam_start"))
        self.client.post(reverse("exam_start"))
        self.assertEqual(Exam.objects.filter(user=self.user).count(), 1)
        self.assertContains(self.client.get(reverse("exam_start")), "Davom ettirish")

    def test_answer_after_deadline_rejected(self):
        from datetime import timedelta

        from django.utils import timezone

        from results import services
        from results.models import Exam

        exam = services.start_exam(self.user)
        Exam.objects.filter(pk=exam.pk).update(started_at=timezone.now() - timedelta(minutes=26))
        item = exam.items.first()
        resp = self.client.post(
            reverse("exam_answer", args=[exam.pk]),
            {"question_id": item.question_id, "answer_id": item.question.answers.first().pk},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(resp.json()["expired"])
        exam.refresh_from_db()
        self.assertEqual(exam.status, Exam.STATUS_EXPIRED)
        self.assertRedirects(self.client.get(reverse("exam", args=[exam.pk])), reverse("result", args=[exam.pk]))

    def test_foreign_exam_and_result_404(self):
        from results import services

        exam = services.start_exam(self.other)
        self.assertEqual(self.client.get(reverse("exam", args=[exam.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("exam_finish", args=[exam.pk])).status_code, 404)
        services.finish_exam(exam)
        self.assertEqual(self.client.get(reverse("result", args=[exam.pk])).status_code, 404)


class QueryCountTests(TestCase):
    """N+1 yo'qligini tekshiradi: ma'lumot ko'paysa ham sahifadagi so'rovlar soni o'zgarmaydi."""

    def setUp(self):
        self.user = User.objects.create_user("ali", "ali@example.com", "Kuchli-parol-2026")
        self.client.force_login(self.user)

    def _grow(self, topics, per_topic):
        from results import services
        from results.tests import make_questions

        start = Topic.objects.count()
        for i in range(start, start + topics):
            topic = Topic.objects.create(name=f"Mavzu {i}", slug=f"mavzu-{i}", order=i)
            make_questions(topic, per_topic, start=i * 100)
            practice = services.start_practice(self.user, topic)
            for item in practice.items.select_related("question")[:3]:
                services.save_answer(practice, item.question_id, item.question.answers.first().pk)
            services.finish_exam(practice)
        exam = services.start_exam(self.user)
        for item in exam.items.select_related("question"):
            services.save_answer(exam, item.question_id, item.question.answers.last().pk)
        services.finish_exam(exam)
        return exam, services.start_practice(self.user, Topic.objects.first()), services

    def _counts(self, exam, practice, open_exam):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        urls = {
            "topics": reverse("topic_list"),
            "profile": reverse("profile"),
            "result": reverse("result", args=[exam.pk]),
            "practice": reverse("practice", args=[practice.pk]),
            "exam": reverse("exam", args=[open_exam.pk]),
            "home": reverse("home"),
        }
        counts = {}
        for name, url in urls.items():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get(url).status_code, 200, name)
            counts[name] = len(ctx)
        return counts

    def test_query_count_does_not_grow_with_data(self):
        exam, practice, services = self._grow(topics=2, per_topic=12)
        open_exam = services.start_exam(self.user)
        small = self._counts(exam, practice, open_exam)
        services.finish_exam(open_exam)

        exam, practice, services = self._grow(topics=4, per_topic=15)
        open_exam = services.start_exam(self.user)
        large = self._counts(exam, practice, open_exam)
        self.assertEqual(small, large)
        self.assertTrue(all(n <= 10 for n in large.values()), large)


class AdminPagesTests(TestCase):
    """Admin (unfold): sahifalar ochiladi, so'rovlar soni ma'lumotga bog'liq emas."""

    def setUp(self):
        self.admin = User.objects.create_user("boss", "boss@example.com", "parol12345", role="admin")
        self.client.force_login(self.admin)

    def _fill(self, n_topics, per_topic):
        from results import services
        from results.tests import make_questions

        start = Topic.objects.count()
        student = User.objects.create_user(f"s{start}", f"s{start}@example.com", "Kuchli-parol-2026")
        for i in range(start, start + n_topics):
            topic = Topic.objects.create(name=f"Mavzu {i}", slug=f"mavzu-{i}", order=i)
            make_questions(topic, per_topic, start=i * 100)
        exam = services.start_exam(student)
        for item in exam.items.select_related("question"):
            services.save_answer(exam, item.question_id, item.question.answers.last().pk)
        return services.finish_exam(exam)

    def _count(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200, url)
        return len(ctx)

    def test_dashboard_shows_real_data(self):
        self._fill(2, 12)
        resp = self.client.get(reverse("admin:index"))
        dash = resp.context["dash"]
        self.assertEqual(dash["kpi"]["questions"]["total"], 24)
        self.assertEqual(dash["kpi"]["exams"]["finished"], 1)
        self.assertEqual(dash["chart"]["total"], 1)
        self.assertEqual(len(dash["hardest"]), 5)
        self.assertContains(resp, "Kontent holati")

    def test_query_counts_do_not_grow(self):
        exam = self._fill(2, 12)
        urls = lambda e: [
            reverse("admin:index"),
            reverse("admin:quiz_question_changelist"),
            reverse("admin:quiz_question_changelist") + "?izoh=yoq",
            reverse("admin:results_exam_changelist"),
            reverse("admin:results_exam_change", args=[e.pk]),
            reverse("admin:accounts_user_changelist"),
            reverse("admin:quiz_topic_changelist"),
        ]
        [self._count(u) for u in urls(exam)]  # keshlarni isitish (ContentType va h.k.)
        small = [self._count(u) for u in urls(exam)]
        exam = self._fill(4, 15)
        large = [self._count(u) for u in urls(exam)]
        self.assertEqual(small, large)

    def test_question_change_form_with_stats(self):
        exam = self._fill(1, 20)
        question = exam.items.first().question
        resp = self.client.get(reverse("admin:quiz_question_change", args=[question.pk]))
        self.assertContains(resp, "Savol statistikasi")
        self.assertContains(resp, "1 marta")

    def test_bulk_deactivate(self):
        self._fill(1, 3)
        ids = list(Question.objects.values_list("pk", flat=True))
        self.client.post(reverse("admin:quiz_question_changelist"), {"action": "deactivate", "_selected_action": ids})
        self.assertFalse(Question.objects.filter(is_active=True).exists())

    def test_exam_admin_is_read_only(self):
        exam = self._fill(1, 3)
        resp = self.client.post(reverse("admin:results_exam_delete", args=[exam.pk]), {"post": "yes"})
        self.assertEqual(resp.status_code, 403)
