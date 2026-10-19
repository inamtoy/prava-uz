import os

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
            call_command("seed_data", stdout=open(os.devnull, "w"))
            call_command("seed_data", stdout=open(os.devnull, "w"))
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
