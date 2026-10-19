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
