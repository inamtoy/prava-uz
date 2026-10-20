from datetime import timedelta

from django.conf import settings
from django.http import Http404
from django.test import TestCase
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
        topics = {t["topic"].slug: t for t in stats["topics"]}
        self.assertEqual(topics["a"]["percent"], 90)  # 18/20
        self.assertEqual(topics["b"]["percent"], 65)  # 13/20
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
