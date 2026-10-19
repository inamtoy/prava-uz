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
