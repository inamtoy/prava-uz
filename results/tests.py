from datetime import timedelta

from django.conf import settings
from django.http import Http404
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from quiz.models import Answer, Question, Topic

from . import services
from .models import Exam, ExamAnswer


def make_questions(topic, count, start=0):
    questions = []
    for i in range(start, start + count):
        q = Question.objects.create(topic=topic, text=f"Savol {i}", explanation=f"Izoh {i}")
        Answer.objects.bulk_create(
            [Answer(question=q, text=f"Javob {i}-{j}", is_correct=(j == 0)) for j in range(4)]
        )
        questions.append(q)
    return questions


class ServiceTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("ali", "ali@example.com", "Kuchli-parol-2026")
        cls.other = User.objects.create_user("vali", "vali@example.com", "Kuchli-parol-2026")
        cls.topic_a = Topic.objects.create(name="A mavzu", slug="a", order=1)
        cls.topic_b = Topic.objects.create(name="B mavzu", slug="b", order=2)
        make_questions(cls.topic_a, 15)
        make_questions(cls.topic_b, 15, start=100)

    def answer_all(self, exam, correct_count):
        """Birinchi `correct_count` ta savolga to'g'ri, qolganlariga xato javob beradi."""
        for i, item in enumerate(exam.items.select_related("question")):
            answers = item.question.answers.all()
            answer = answers.get(is_correct=True) if i < correct_count else answers.filter(is_correct=False).first()
            services.save_answer(exam, item.question_id, answer.pk)


class StartExamTests(ServiceTestBase):
    def test_selects_20_unique_questions(self):
        exam = services.start_exam(self.user)
        ids = list(exam.items.values_list("question_id", flat=True))
        self.assertEqual(len(ids), settings.EXAM_QUESTION_COUNT)
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(exam.total_questions, 20)
        self.assertEqual(list(exam.items.values_list("order", flat=True)), list(range(1, 21)))
        self.assertFalse(exam.items.exclude(selected_answer=None).exists())

    def test_only_active_questions(self):
        Question.objects.filter(topic=self.topic_b).update(is_active=False)
        exam = services.start_exam(self.user)
        self.assertEqual(exam.total_questions, 15)  # bazada 20 tadan kam — borini oladi
        self.assertFalse(exam.items.filter(question__is_active=False).exists())

    def test_resumes_open_exam(self):
        first = services.start_exam(self.user)
        second = services.start_exam(self.user)
        self.assertEqual(first.pk, second.pk)
        self.assertTrue(second.resumed)
        self.assertEqual(Exam.objects.filter(user=self.user).count(), 1)

    def test_expired_open_exam_is_closed_and_new_one_created(self):
        first = services.start_exam(self.user)
        Exam.objects.filter(pk=first.pk).update(started_at=timezone.now() - timedelta(hours=1))
        second = services.start_exam(self.user)
        self.assertNotEqual(first.pk, second.pk)
        first.refresh_from_db()
        self.assertEqual(first.status, Exam.STATUS_EXPIRED)

    def test_no_questions_raises(self):
        Question.objects.all().update(is_active=False)
        with self.assertRaises(services.ExamError):
            services.start_exam(self.user)

    def test_duplicate_questions_not_repeated_in_one_exam(self):
        """Matni (bo'sh joy va harf farqisiz) va rasmi bir xil savollardan imtihonda faqat bittasi chiqadi."""
        Question.objects.update(is_active=False)
        # 12 xil savol, har biri 3 nusxada (turli biletlarda, bo'sh joy / harf farqi bilan) = 36 ta faol savol
        for i in range(12):
            for n, (topic, text) in enumerate([
                (self.topic_a, f"Takroriy savol {i}"),
                (self.topic_b, f"  takroriy   SAVOL {i} "),
                (self.topic_a, f"Takroriy savol {i}"),
            ]):
                q = Question.objects.create(topic=topic, text=text, image=f"questions/dup_{i}.jpeg")
                Answer.objects.create(question=q, text="A", is_correct=True)
                Answer.objects.create(question=q, text="B")
        # Matni bir xil, rasmi boshqa — bu boshqa savol, ikkalasi ham chiqishi mumkin
        for img in ("questions/x1.jpeg", "questions/x2.jpeg"):
            q = Question.objects.create(topic=self.topic_a, text="Rasmga qarang", image=img)
            Answer.objects.create(question=q, text="A", is_correct=True)

        for _ in range(5):  # tasodifiy tanlov — bir necha marta tekshiramiz
            Exam.objects.filter(user=self.user).delete()
            exam = services.start_exam(self.user)
            qs = Question.objects.filter(pk__in=exam.items.values("question_id"))
            keys = [(" ".join(q.text.split()).lower(), q.image.name) for q in qs]
            self.assertEqual(len(keys), len(set(keys)), "bir xil savol imtihonda ikki marta chiqdi")
            # 12 + 2 = 14 xil savol bor — hammasi olinadi, takroriylar hisobiga 20 ga to'ldirilmaydi
            self.assertEqual(exam.total_questions, 14)

    def test_duplicates_do_not_reduce_count_when_enough_unique(self):
        # Bazadagi 30 ta noyob savolga 15 ta nusxa qo'shilsa ham imtihon to'liq 20 ta bo'ladi
        for q in list(Question.objects.filter(topic=self.topic_a)):
            Question.objects.create(topic=self.topic_b, text=q.text)
        exam = services.start_exam(self.user)
        self.assertEqual(exam.total_questions, settings.EXAM_QUESTION_COUNT)
        texts = list(Question.objects.filter(pk__in=exam.items.values("question_id")).values_list("text", flat=True))
        self.assertEqual(len(texts), len(set(texts)))


class StartPracticeTests(ServiceTestBase):
    def test_practice_uses_topic_questions(self):
        exam = services.start_practice(self.user, self.topic_a)
        self.assertEqual(exam.mode, Exam.MODE_PRACTICE)
        self.assertEqual(exam.total_questions, 15)
        self.assertFalse(exam.items.exclude(question__topic=self.topic_a).exists())


class SaveAnswerTests(ServiceTestBase):
    def setUp(self):
        self.exam = services.start_exam(self.user)
        self.item = self.exam.items.select_related("question").first()
        self.correct = self.item.question.answers.get(is_correct=True)
        self.wrong = self.item.question.answers.filter(is_correct=False).first()

    def test_saves_and_computes_correctness_on_server(self):
        item = services.save_answer(self.exam, self.item.question_id, self.correct.pk)
        self.assertTrue(item.is_correct)
        self.assertIsNotNone(item.answered_at)
        # Birinchi javob yakuniy — o'zgartirib bo'lmaydi
        item = services.save_answer(self.exam, self.item.question_id, self.wrong.pk)
        self.assertTrue(item.is_correct)
        self.assertEqual(item.selected_answer_id, self.correct.pk)

    def test_rejects_answer_of_another_question(self):
        other_item = self.exam.items.exclude(pk=self.item.pk).first()
        foreign = other_item.question.answers.first()
        with self.assertRaises(services.ExamError):
            services.save_answer(self.exam, self.item.question_id, foreign.pk)

    def test_rejects_question_not_in_exam(self):
        outside = Question.objects.exclude(pk__in=self.exam.items.values("question_id")).first()
        with self.assertRaises(services.ExamError):
            services.save_answer(self.exam, outside.pk, outside.answers.first().pk)

    def test_rejects_foreign_user(self):
        with self.assertRaises(Http404):
            services.save_answer(self.exam, self.item.question_id, self.correct.pk, user=self.other)

    def test_rejects_after_deadline_and_expires_exam(self):
        Exam.objects.filter(pk=self.exam.pk).update(started_at=timezone.now() - timedelta(seconds=1501))
        self.exam.refresh_from_db()
        with self.assertRaises(services.ExamExpired):
            services.save_answer(self.exam, self.item.question_id, self.correct.pk)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.selected_answer_id)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, Exam.STATUS_EXPIRED)
        self.assertIsNotNone(self.exam.finished_at)

    def test_rejects_finished_exam(self):
        services.finish_exam(self.exam)
        self.exam.refresh_from_db()
        with self.assertRaises(services.ExamError):
            services.save_answer(self.exam, self.item.question_id, self.correct.pk)

    def test_practice_first_answer_is_final(self):
        practice = services.start_practice(self.user, self.topic_a)
        item = practice.items.select_related("question").first()
        wrong = item.question.answers.filter(is_correct=False).first()
        right = item.question.answers.get(is_correct=True)
        services.save_answer(practice, item.question_id, wrong.pk)
        item = services.save_answer(practice, item.question_id, right.pk)
        self.assertFalse(item.is_correct)
        self.assertEqual(item.selected_answer_id, wrong.pk)


class FinishExamTests(ServiceTestBase):
    def test_18_of_20_passes(self):
        exam = services.start_exam(self.user)
        self.answer_all(exam, 18)
        exam = services.finish_exam(exam)
        self.assertEqual(exam.score, 18)
        self.assertTrue(exam.is_passed)
        self.assertEqual(exam.status, Exam.STATUS_FINISHED)
        self.assertIsNotNone(exam.finished_at)
        self.assertEqual(exam.percent, 90)

    def test_17_of_20_fails(self):
        exam = services.start_exam(self.user)
        self.answer_all(exam, 17)
        exam = services.finish_exam(exam)
        self.assertEqual(exam.score, 17)
        self.assertFalse(exam.is_passed)

    def test_unanswered_counts_as_mistake(self):
        exam = services.start_exam(self.user)
        items = list(exam.items.select_related("question"))
        for item in items[:17]:  # 17 to'g'ri, 3 tasi javobsiz
            services.save_answer(exam, item.question_id, item.question.answers.get(is_correct=True).pk)
        exam = services.finish_exam(exam)
        self.assertEqual(exam.score, 17)
        self.assertEqual(exam.mistakes, 3)
        self.assertFalse(exam.is_passed)

    def test_all_correct_but_none_answered_fails(self):
        exam = services.finish_exam(services.start_exam(self.user))
        self.assertEqual(exam.score, 0)
        self.assertFalse(exam.is_passed)

    def test_finish_is_idempotent(self):
        exam = services.start_exam(self.user)
        self.answer_all(exam, 20)
        first = services.finish_exam(exam)
        second = services.finish_exam(exam)
        self.assertEqual(first.finished_at, second.finished_at)
        self.assertEqual(second.score, 20)

    def test_practice_has_no_pass_flag(self):
        practice = services.start_practice(self.user, self.topic_a)
        practice = services.finish_exam(practice)
        self.assertIsNone(practice.is_passed)
        self.assertEqual(practice.status, Exam.STATUS_FINISHED)


class UserStatsTests(ServiceTestBase):
    def _exam_with_topic_split(self, correct_a, correct_b):
        """10 ta A va 10 ta B savolli imtihon; har mavzudan berilgan son to'g'ri."""
        exam = Exam.objects.create(user=self.user, mode=Exam.MODE_EXAM, total_questions=20)
        items, order = [], 1
        for topic, correct in ((self.topic_a, correct_a), (self.topic_b, correct_b)):
            for i, q in enumerate(Question.objects.filter(topic=topic)[:10]):
                items.append(ExamAnswer(exam=exam, question=q, is_correct=i < correct, order=order))
                order += 1
        ExamAnswer.objects.bulk_create(items)
        return services.finish_exam(exam)

    def test_empty_stats(self):
        stats = services.user_stats(self.user)
        self.assertEqual(stats["total_exams"], 0)
        self.assertEqual(stats["average_percent"], 0)
        self.assertEqual(stats["weakest_topics"], [])

    def test_percentages(self):
        self._exam_with_topic_split(10, 9)   # 19/20 = 95%, o'tdi
        self._exam_with_topic_split(8, 4)    # 12/20 = 60%, o'tmadi
        services.start_exam(self.other)      # begona — hisobga kirmaydi
        stats = services.user_stats(self.user)
        self.assertEqual(stats["total_exams"], 2)
        self.assertEqual(stats["passed_exams"], 1)
        self.assertEqual(stats["average_percent"], 78)  # (95 + 60) / 2 = 77.5 → 78
        self.assertEqual(stats["best_percent"], 95)
        # imtihon savollari biletlar statistikasiga kirmaydi
        self.assertFalse(any(t["total"] for t in stats["topics"]))
        self.assertEqual(stats["weakest_topics"], [])

    def test_topic_percentages_from_practice(self):
        for topic, correct in ((self.topic_a, 12), (self.topic_b, 6)):
            practice = services.start_practice(self.user, topic)
            self.answer_all(practice, correct)
            services.finish_exam(practice)
        unfinished = services.start_practice(self.user, self.topic_b)  # tugallanmagan — hisobga kirmaydi
        self.answer_all(unfinished, 0)
        stats = services.user_stats(self.user)
        topics = {t["topic"].slug: t for t in stats["topics"]}
        self.assertEqual(topics["a"]["percent"], 80)  # 12/15
        self.assertEqual(topics["b"]["percent"], 40)  # 6/15
        self.assertEqual(stats["weakest_topics"][0]["topic"], self.topic_b)

    def test_in_progress_exams_ignored(self):
        exam = services.start_exam(self.user)
        self.answer_all(exam, 20)
        self.assertEqual(services.user_stats(self.user)["total_exams"], 0)

    def test_topic_progress(self):
        practice = services.start_practice(self.user, self.topic_a)
        self.answer_all(practice, 3)
        progress = services.topic_progress(self.user)
        self.assertEqual(progress[self.topic_a.pk], 20)  # 3/15
        self.assertEqual(progress[self.topic_b.pk], 0)

    def test_topic_progress_ignores_exam_answers(self):
        exam = services.start_exam(self.user)
        self.answer_all(exam, 20)
        services.finish_exam(exam)
        self.assertFalse(any(services.topic_progress(self.user).values()))


class ResultProfileViewTests(ServiceTestBase):
    def setUp(self):
        self.client.force_login(self.user)

    def test_result_shows_mistake_analysis(self):
        exam = services.start_exam(self.user)
        self.answer_all(exam, 18)
        services.finish_exam(exam)
        resp = self.client.get(f"/natija/{exam.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["mistakes"]), 2)
        for item in resp.context["mistakes"]:
            self.assertTrue(item.correct_answer.is_correct)
            self.assertContains(resp, item.question.text)

    def test_result_query_count_is_constant(self):
        exam = services.start_exam(self.user)
        self.answer_all(exam, 5)
        services.finish_exam(exam)
        self.client.get(f"/natija/{exam.pk}/")  # sessiya/kesh isitish
        with self.assertNumQueries(5):  # sessiya, user, exam, items, answers — savollar soniga bog'liq emas
            self.client.get(f"/natija/{exam.pk}/")

    def test_profile_empty_state(self):
        resp = self.client.get("/accounts/profile/")
        self.assertContains(resp, "Hali imtihon topshirmagansiz")

    def test_profile_shows_only_own_exams(self):
        mine = services.finish_exam(services.start_exam(self.user))
        services.finish_exam(services.start_exam(self.other))
        resp = self.client.get("/accounts/profile/")
        self.assertEqual([e.pk for e in resp.context["recent_exams"]], [mine.pk])
        self.assertEqual(resp.context["stats"]["total_exams"], 1)


class MistakesAndDailyTests(ServiceTestBase):
    """"Xatolarim" ro'yxati, xatolar mashqi, kunlik maqsad va seriya."""

    def _answer(self, exam, question, correct):
        answers = question.answers.all()
        answer = answers.get(is_correct=True) if correct else answers.filter(is_correct=False).first()
        return services.save_answer(exam, question.pk, answer.pk)

    def _session_with(self, questions, correct):
        exam = services._create_session(self.user, Exam.MODE_PRACTICE, questions, topic=self.topic_a)
        for q in questions:
            self._answer(exam, q, correct)
        return exam

    def test_wrong_answer_goes_to_mistakes_and_two_correct_clear_it(self):
        q1, q2 = self.topic_a.questions.order_by("pk")[:2]
        self._session_with([q1, q2], correct=False)
        self.assertEqual(set(services.mistake_question_ids(self.user)), {q1.pk, q2.pk})

        self._session_with([q1], correct=True)
        self.assertIn(q1.pk, services.mistake_question_ids(self.user))  # 1 marta yetmaydi
        self._session_with([q1], correct=True)
        self.assertEqual(services.mistake_question_ids(self.user), [q2.pk])

    def test_new_mistake_resets_streak(self):
        q = self.topic_a.questions.first()
        self._session_with([q], correct=False)
        self._session_with([q], correct=True)
        self._session_with([q], correct=False)
        self._session_with([q], correct=True)
        self.assertEqual(services.mistake_question_ids(self.user), [q.pk])

    def test_correct_first_time_is_not_a_mistake_and_unanswered_ignored(self):
        exam = services.start_exam(self.user)
        item = exam.items.select_related("question").first()
        self._answer(exam, item.question, correct=True)
        services.finish_exam(exam)  # qolgan 19 ta javobsiz — "Xatolarim"ga tushmaydi
        self.assertEqual(services.mistake_question_ids(self.user), [])

    def test_mistakes_are_per_user_and_active_only(self):
        q1, q2 = self.topic_a.questions.order_by("pk")[:2]
        self._session_with([q1, q2], correct=False)
        self.assertEqual(services.mistake_question_ids(self.other), [])
        Question.objects.filter(pk=q2.pk).update(is_active=False)
        self.assertEqual(services.mistake_question_ids(self.user), [q1.pk])

    def test_start_mistakes(self):
        with self.assertRaises(services.ExamError):
            services.start_mistakes(self.user)
        wrong = list(self.topic_a.questions.order_by("pk")[:3])
        self._session_with(wrong, correct=False)
        exam = services.start_mistakes(self.user)
        self.assertEqual(exam.mode, Exam.MODE_MISTAKES)
        self.assertIsNone(exam.topic)
        self.assertEqual(set(exam.items.values_list("question_id", flat=True)), {q.pk for q in wrong})
        finished = services.finish_exam(exam)
        self.assertIsNone(finished.is_passed)

    def test_daily_progress_and_streak(self):
        self.user.daily_goal = 10
        self.user.save()
        today = timezone.localdate()
        d = services.daily_progress(self.user)
        self.assertEqual((d["today"], d["goal"], d["streak"], d["reached"]), (0, 10, 0, False))
        self.assertEqual(len(d["week"]), 7)
        self.assertTrue(d["week"][-1]["is_today"])

        questions = list(self.topic_a.questions.order_by("pk")[:12])
        exam = self._session_with(questions, correct=True)
        items = list(exam.items.order_by("order"))
        now = timezone.now()
        # 10 ta — kecha, 2 ta — bugun
        for it in items[:10]:
            ExamAnswer.objects.filter(pk=it.pk).update(answered_at=now - timedelta(days=1))
        d = services.daily_progress(self.user)
        self.assertEqual(d["today"], 2)
        self.assertEqual(d["left"], 8)
        self.assertEqual(d["streak"], 1)  # bugun hali tugamagan — kechagi seriya saqlanadi
        self.assertTrue(d["week"][-2]["reached"])

        more = list(self.topic_b.questions.order_by("pk")[:8])
        self._session_with(more, correct=False)
        d = services.daily_progress(self.user)
        self.assertEqual((d["today"], d["reached"], d["streak"], d["percent"]), (10, True, 2, 100))

        # Kecha maqsad bajarilmagan bo'lsa seriya uziladi
        ExamAnswer.objects.filter(pk=items[0].pk).update(answered_at=now - timedelta(days=3))
        d = services.daily_progress(self.user, today=today)
        self.assertEqual(d["streak"], 1)

    def test_current_session(self):
        self.assertIsNone(services.current_session(self.user))
        empty = services.start_practice(self.user, self.topic_a)
        self.assertIsNone(services.current_session(self.user))  # javobsiz mashq taklif qilinmaydi
        q = empty.items.first().question
        self._answer(empty, q, correct=True)
        cur = services.current_session(self.user)
        self.assertEqual((cur.pk, cur.answered_count), (empty.pk, 1))
        exam = services.start_exam(self.user)
        self.assertEqual(services.current_session(self.user).pk, exam.pk)


class HomeDashboardViewTests(ServiceTestBase):
    def setUp(self):
        self.client.force_login(self.user)

    def test_home_shows_today_panel_and_mistakes(self):
        q = self.topic_a.questions.first()
        exam = services._create_session(self.user, Exam.MODE_PRACTICE, [q], topic=self.topic_a)
        services.save_answer(exam, q.pk, q.answers.filter(is_correct=False).first().pk)
        services.finish_exam(exam)
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Kunlik maqsad")
        self.assertContains(resp, "Xatolar ustida ishlash")
        self.assertContains(resp, "<strong>1</strong> ta savol", html=False)

    def test_mistakes_start_flow(self):
        resp = self.client.post(reverse("mistakes_start"))
        self.assertRedirects(resp, reverse("home"))  # xato yo'q — xabar bilan qaytadi
        q = self.topic_a.questions.first()
        exam = services._create_session(self.user, Exam.MODE_PRACTICE, [q], topic=self.topic_a)
        services.save_answer(exam, q.pk, q.answers.filter(is_correct=False).first().pk)
        resp = self.client.post(reverse("mistakes_start"))
        session = Exam.objects.get(mode=Exam.MODE_MISTAKES)
        self.assertRedirects(resp, reverse("practice", args=[session.pk]))
        page = self.client.get(reverse("practice", args=[session.pk]))
        self.assertContains(page, "Xatolar ustida ishlash")
        services.save_answer(session, q.pk, q.answers.get(is_correct=True).pk)
        self.client.post(reverse("exam_finish", args=[session.pk]))
        self.assertEqual(self.client.get(reverse("result", args=[session.pk])).status_code, 200)

    def test_set_daily_goal(self):
        self.client.post(reverse("set_daily_goal"), {"daily_goal": "30"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.daily_goal, 30)
        self.client.post(reverse("set_daily_goal"), {"daily_goal": "7"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.daily_goal, 30)


class LeaderboardTests(ServiceTestBase):
    def _correct(self, user, n, days_ago=0):
        """`user` ga `n` ta to'g'ri javob (berilgan kunda) yozadi."""
        qs = list(Question.objects.order_by("pk")[:n])
        exam = services._create_session(user, Exam.MODE_PRACTICE, qs, topic=self.topic_a)
        for q in qs:
            services.save_answer(exam, q.pk, q.answers.get(is_correct=True).pk)
        if days_ago:
            exam.items.update(answered_at=timezone.now() - timedelta(days=days_ago))

    def test_ranking_privacy_and_week(self):
        self._correct(self.user, 5)
        self._correct(self.other, 8)
        third = User.objects.create_user("soli", "soli@example.com", "Kuchli-parol-2026", first_name="Soli")
        self._correct(third, 3)
        self._correct(third, 20, days_ago=8)  # o'tgan hafta — hisoblanmaydi
        admin = User.objects.create_user("boss", "boss@example.com", "Kuchli-parol-2026", role=User.ROLE_ADMIN)
        self._correct(admin, 25)  # admin reytingga kirmaydi

        b = services.weekly_leaderboard(self.user)
        self.assertEqual([(r["name"], r["correct"]) for r in b["top"]], [("vali", 8), ("ali", 5), ("Soli", 3)])
        self.assertEqual(b["me"]["rank"], 2)
        self.assertTrue(b["top"][1]["is_me"])
        self.assertEqual((b["participants"], b["my_correct"], b["to_top"]), (3, 5, 0))
        self.assertEqual(b["week_start"].weekday(), 0)

        self.other.show_in_leaderboard = False
        self.other.save()
        b = services.weekly_leaderboard(self.user)
        self.assertEqual([r["name"] for r in b["top"]], ["ali", "Soli"])
        hidden = services.weekly_leaderboard(self.other)
        self.assertTrue(hidden["hidden"])
        self.assertIsNone(hidden["me"])
        self.assertEqual(hidden["my_correct"], 8)  # o'z natijasini baribir ko'radi

    def test_to_top_outside_top_size(self):
        self._correct(self.other, 6)
        self._correct(self.user, 2)
        b = services.weekly_leaderboard(self.user, size=1)
        self.assertEqual(b["me"]["rank"], 2)
        self.assertEqual(b["to_top"], 5)

    def test_pages(self):
        self._correct(self.user, 4)
        self.client.force_login(self.user)
        resp = self.client.get(reverse("leaderboard"))
        self.assertContains(resp, "Haftalik TOP-10")
        self.assertContains(resp, "1-oʻrin")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("leaderboard")).status_code, 302)


class AccountSettingsViewTests(ServiceTestBase):
    def setUp(self):
        self.client.force_login(self.user)

    def test_profile_update_and_unique_email(self):
        url = reverse("account_settings")
        self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.post(url, {"action": "profile", "first_name": "Alisher", "email": "vali@example.com"})
        self.assertContains(resp, "boshqa foydalanuvchiga tegishli")
        resp = self.client.post(url, {"action": "profile", "first_name": "Alisher", "email": "New@Example.com"})
        self.assertRedirects(resp, url)
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.email, self.user.show_in_leaderboard),
                         ("Alisher", "new@example.com", False))  # belgilanmagan checkbox — yashirin

    def test_password_change_keeps_session(self):
        url = reverse("account_settings")
        resp = self.client.post(url, {"action": "password", "old_password": "xato",
                                      "new_password1": "Yangi-parol-2026", "new_password2": "Yangi-parol-2026"})
        self.assertContains(resp, "Joriy parol notoʻgʻri")
        resp = self.client.post(url, {"action": "password", "old_password": "Kuchli-parol-2026",
                                      "new_password1": "Yangi-parol-2026", "new_password2": "Yangi-parol-2026"})
        self.assertRedirects(resp, url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Yangi-parol-2026"))
        self.assertEqual(self.client.get(reverse("profile")).status_code, 200)  # sessiya saqlandi
