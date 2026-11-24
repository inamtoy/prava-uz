from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import User
from quiz.models import Topic
from results.models import Exam
from results.tests import make_questions

PASSWORD = "Kuchli-parol-2026"


class ApiTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("ali", "ali@example.com", PASSWORD, first_name="Ali")
        cls.other = User.objects.create_user("vali", "vali@example.com", PASSWORD)
        cls.topic = Topic.objects.create(name="1-bilet", slug="bilet-1", order=1)
        cls.topic2 = Topic.objects.create(name="2-bilet", slug="bilet-2", order=2)
        make_questions(cls.topic, 15)
        make_questions(cls.topic2, 15, start=100)

    def setUp(self):
        cache.clear()  # throttling hisoblagichi
        self.client = APIClient()

    def auth(self, user=None):
        token, _ = Token.objects.get_or_create(user=user or self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


class AuthApiTests(ApiTestBase):
    def test_register_returns_token(self):
        r = self.client.post("/api/v1/auth/register/", {
            "first_name": "Nodira", "username": "nodira", "email": "Nodira@Example.com", "password": PASSWORD,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        user = User.objects.get(username="nodira")
        self.assertEqual(r.json()["token"], Token.objects.get(user=user).key)
        self.assertEqual(user.email, "nodira@example.com")
        self.assertNotEqual(user.password, PASSWORD)

    def test_register_validation_in_uzbek(self):
        r = self.client.post("/api/v1/auth/register/", {
            "first_name": "X", "username": "x2", "email": "ali@example.com", "password": PASSWORD,
        }, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.json()["errors"])
        self.assertIn("allaqachon", r.json()["error"])

    def test_login_with_email_or_username(self):
        for login in ("ali", "ali@example.com"):
            r = self.client.post("/api/v1/auth/login/", {"login": login, "password": PASSWORD}, format="json")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["user"]["username"], "ali")

    def test_login_wrong_password(self):
        r = self.client.post("/api/v1/auth/login/", {"login": "ali", "password": "xato"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_protected_endpoints_need_token(self):
        for url in ("/api/v1/me/", "/api/v1/topics/", "/api/v1/stats/", "/api/v1/exams/"):
            self.assertEqual(self.client.get(url).status_code, 401, url)

    def test_logout_revokes_token(self):
        self.auth()
        self.assertEqual(self.client.post("/api/v1/auth/logout/").status_code, 200)
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 401)


class SessionApiTests(ApiTestBase):
    def start_exam(self):
        r = self.client.post("/api/v1/exams/")
        self.assertIn(r.status_code, (200, 201), r.content)
        return r.json()

    def correct_id(self, item):
        from quiz.models import Answer
        return Answer.objects.get(question_id=item["question_id"], is_correct=True).pk

    def wrong_id(self, item):
        from quiz.models import Answer
        return Answer.objects.filter(question_id=item["question_id"], is_correct=False).first().pk

    def post_answer(self, sid, item, answer_id):
        return self.client.post(f"/api/v1/sessions/{sid}/answer/",
                                {"question_id": item["question_id"], "answer_id": answer_id}, format="json")

    def test_topics_with_progress(self):
        self.auth()
        data = self.client.get("/api/v1/topics/").json()
        self.assertEqual([t["slug"] for t in data], ["bilet-1", "bilet-2"])
        self.assertEqual(data[0]["question_count"], 15)
        self.assertEqual(data[0]["progress"], 0)

    def test_session_hides_correct_answer_until_answered(self):
        self.auth()
        exam = self.start_exam()
        self.assertEqual(len(exam["items"]), 20)
        item = exam["items"][0]
        self.assertNotIn("correct_answer_id", item)
        self.assertNotIn("is_correct", str(item["answers"]))

        r = self.post_answer(exam["id"], item, self.wrong_id(item))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["is_correct"])
        self.assertEqual(r.json()["correct_answer_id"], self.correct_id(item))
        self.assertIn("time_left", r.json())

        again = self.client.get(f"/api/v1/sessions/{exam['id']}/").json()["items"][0]
        self.assertTrue(again["answered"])
        self.assertEqual(again["correct_answer_id"], self.correct_id(item))

    def test_first_answer_is_final(self):
        self.auth()
        exam = self.start_exam()
        item = exam["items"][0]
        self.post_answer(exam["id"], item, self.wrong_id(item))
        r = self.post_answer(exam["id"], item, self.correct_id(item))
        self.assertFalse(r.json()["is_correct"])

    def test_full_exam_flow_pass(self):
        self.auth()
        exam = self.start_exam()
        for i, item in enumerate(exam["items"]):
            answer_id = self.correct_id(item) if i < 18 else self.wrong_id(item)
            self.assertEqual(self.post_answer(exam["id"], item, answer_id).status_code, 200)
        r = self.client.post(f"/api/v1/sessions/{exam['id']}/finish/")
        self.assertEqual(r.status_code, 200)
        res = r.json()
        self.assertEqual(res["score"], 18)
        self.assertTrue(res["is_passed"])
        self.assertEqual(len(res["mistakes"]), 2)
        self.assertEqual(self.client.get(f"/api/v1/sessions/{exam['id']}/result/").json()["score"], 18)

    def test_resume_open_exam(self):
        self.auth()
        first = self.start_exam()
        second = self.client.post("/api/v1/exams/")
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["resumed"])
        self.assertEqual(second.json()["id"], first["id"])
        self.assertEqual(self.client.get("/api/v1/exams/").json()["current"]["id"], first["id"])

    def test_foreign_session_404(self):
        self.auth()
        exam = self.start_exam()
        self.auth(self.other)
        for url in (f"/api/v1/sessions/{exam['id']}/", f"/api/v1/sessions/{exam['id']}/result/"):
            self.assertEqual(self.client.get(url).status_code, 404)
        r = self.post_answer(exam["id"], exam["items"][0], self.correct_id(exam["items"][0]))
        self.assertEqual(r.status_code, 404)

    def test_expired_exam_rejects_answer(self):
        self.auth()
        exam = self.start_exam()
        Exam.objects.filter(pk=exam["id"]).update(started_at=timezone.now() - timedelta(minutes=26))
        item = exam["items"][0]
        r = self.post_answer(exam["id"], item, self.correct_id(item))
        self.assertEqual(r.status_code, 409)
        self.assertTrue(r.json()["expired"])
        self.assertEqual(Exam.objects.get(pk=exam["id"]).status, Exam.STATUS_EXPIRED)

    def test_answer_from_other_question_rejected(self):
        self.auth()
        exam = self.start_exam()
        a, b = exam["items"][0], exam["items"][1]
        r = self.post_answer(exam["id"], a, self.correct_id(b))
        self.assertEqual(r.status_code, 400)

    def test_practice_and_stats(self):
        self.auth()
        r = self.client.post("/api/v1/topics/bilet-1/practice/")
        self.assertEqual(r.status_code, 201)
        practice = r.json()
        self.assertEqual(practice["mode"], "practice")
        self.assertIsNone(practice["time_left"])
        for item in practice["items"][:10]:
            self.post_answer(practice["id"], item, self.correct_id(item))
        self.client.post(f"/api/v1/sessions/{practice['id']}/finish/")
        st = self.client.get("/api/v1/stats/").json()
        self.assertEqual(st["practice_count"], 1)
        self.assertEqual(st["practiced_topics"][0]["percent"], 100)
        self.assertEqual(self.client.get("/api/v1/topics/").json()[0]["progress"], round(10 * 100 / 15))


class HomeApiTests(ApiTestBase):
    def test_home_requires_auth(self):
        self.assertEqual(self.client.get("/api/v1/home/").status_code, 401)

    def test_home_and_mistakes_flow(self):
        self.auth()
        r = self.client.get("/api/v1/home/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["mistakes_count"], 0)
        self.assertIsNone(r.data["current"])
        self.assertEqual(r.data["daily"]["goal"], 20)
        self.assertEqual(len(r.data["daily"]["week"]), 7)
        self.assertEqual(r.data["goal_choices"], [10, 20, 30, 50])

        self.assertEqual(self.client.post("/api/v1/mistakes/").status_code, 400)

        practice = self.client.post(f"/api/v1/topics/{self.topic.slug}/practice/").data
        item = practice["items"][0]
        wrong = next(a for a in item["answers"] if not self._is_correct(a["id"]))
        self.client.post(f"/api/v1/sessions/{practice['id']}/answer/",
                         {"question_id": item["question_id"], "answer_id": wrong["id"]}, format="json")

        r = self.client.get("/api/v1/home/")
        self.assertEqual(r.data["mistakes_count"], 1)
        self.assertEqual(r.data["daily"]["today"], 1)
        self.assertEqual(r.data["current"]["id"], practice["id"])
        self.assertEqual(r.data["current"]["answered_count"], 1)

        m = self.client.post("/api/v1/mistakes/")
        self.assertEqual(m.status_code, 201)
        self.assertEqual(m.data["mode"], "mistakes")
        self.assertEqual([i["question_id"] for i in m.data["items"]], [item["question_id"]])
        self.assertNotIn("correct_answer_id", m.data["items"][0])

    def test_daily_goal(self):
        self.auth()
        r = self.client.post("/api/v1/me/goal/", {"daily_goal": 50}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["daily"]["goal"], 50)
        self.assertEqual(self.client.get("/api/v1/me/").data["daily_goal"], 50)
        self.assertEqual(self.client.post("/api/v1/me/goal/", {"daily_goal": 3}, format="json").status_code, 400)

    @staticmethod
    def _is_correct(answer_id):
        from quiz.models import Answer
        return Answer.objects.get(pk=answer_id).is_correct
