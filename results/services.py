"""Imtihon va mashq mantiqi. View'lar faqat shu funksiyalarni chaqiradi."""

import random
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import Http404
from django.utils import timezone

from quiz.models import Answer, Question, Topic
from quiz.utils import question_key

from .models import Exam, ExamAnswer

FINISHED_STATUSES = (Exam.STATUS_FINISHED, Exam.STATUS_EXPIRED)


class ExamError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato (matni o'zbekcha)."""


class ExamExpired(ExamError):
    pass


def _create_session(user, mode, questions, topic=None):
    if not questions:
        raise ExamError("Hozircha savollar mavjud emas.")
    exam = Exam.objects.create(
        user=user,
        mode=mode,
        topic=topic,
        total_questions=len(questions),
        duration_seconds=settings.EXAM_DURATION_SECONDS,
    )
    ExamAnswer.objects.bulk_create([
        ExamAnswer(exam=exam, question=q, order=i) for i, q in enumerate(questions, start=1)
    ])
    return exam


def _pick_exam_questions(count):
    """Tasodifiy `count` ta faol savol; matni va rasmi bir xil savollardan faqat bittasi olinadi.

    Bir xil savol bir necha biletda takrorlanadi (rasmiy biletlarda ham shunday) — ular bazada qoladi,
    lekin bitta imtihonda ikki marta chiqmasligi kerak.
    """
    picked, seen = [], set()
    for q in Question.objects.filter(is_active=True).order_by("?").iterator(chunk_size=100):
        key = question_key(q.text, q.image)
        if key in seen:
            continue
        seen.add(key)
        picked.append(q)
        if len(picked) == count:
            break
    return picked


@transaction.atomic
def start_exam(user):
    """Ochiq imtihon bo'lsa — uni qaytaradi (exam.resumed=True), aks holda yangisini yaratadi."""
    current = (
        Exam.objects.filter(user=user, mode=Exam.MODE_EXAM, status=Exam.STATUS_IN_PROGRESS)
        .order_by("-started_at")
        .first()
    )
    if current is not None:
        if not expire_if_needed(current):
            current.resumed = True
            return current

    exam = _create_session(user, Exam.MODE_EXAM, _pick_exam_questions(settings.EXAM_QUESTION_COUNT))
    exam.resumed = False
    return exam


@transaction.atomic
def start_practice(user, topic):
    questions = list(
        topic.questions.filter(is_active=True).order_by("?")[: settings.PRACTICE_QUESTION_COUNT]
    )
    if not questions:
        raise ExamError("Bu biletda hozircha savollar yoʻq.")
    return _create_session(user, Exam.MODE_PRACTICE, questions, topic=topic)


def mistake_question_ids(user):
    """"Xatolarim": foydalanuvchi xato javob bergan va keyin ketma-ket MISTAKES_CLEAR_STREAK marta
    to'g'ri yechmagan faol savollar — eng oxirgi xato birinchi.

    Barcha rejimlar hisobga olinadi (imtihon ham). Javob berilmagan savol bu yerda xato emas.
    """
    rows = (
        ExamAnswer.objects.filter(exam__user=user, answered_at__isnull=False, question__is_active=True)
        .order_by("answered_at", "id")
        .values_list("question_id", "is_correct", "answered_at")
    )
    need = settings.MISTAKES_CLEAR_STREAK
    state = {}  # question_id -> [ketma-ket to'g'ri, oxirgi xato vaqti]
    for qid, ok, at in rows:
        if not ok:
            state[qid] = [0, at]
        elif qid in state:
            state[qid][0] += 1
            if state[qid][0] >= need:
                del state[qid]
    return [qid for qid, _ in sorted(state.items(), key=lambda kv: kv[1][1], reverse=True)]


@transaction.atomic
def start_mistakes(user):
    """Xato qilingan savollardan mashq (eng oxirgi xatolardan, ko'pi bilan PRACTICE_QUESTION_COUNT ta)."""
    ids = mistake_question_ids(user)
    if not ids:
        raise ExamError("Hozircha xatolaringiz yoʻq — biletlar boʻyicha mashq qiling.")
    by_id = Question.objects.in_bulk(ids)
    picked, seen = [], set()
    for qid in ids:
        q = by_id[qid]
        key = question_key(q.text, q.image)
        if key in seen:
            continue
        seen.add(key)
        picked.append(q)
        if len(picked) == settings.PRACTICE_QUESTION_COUNT:
            break
    random.shuffle(picked)
    return _create_session(user, Exam.MODE_MISTAKES, picked)


WEEKDAYS_UZ = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
STREAK_LOOKBACK_DAYS = 400


def daily_progress(user, today=None):
    """Kunlik maqsad va seriya. Kun — Toshkent vaqti bo'yicha; hisob — javob berilgan savollar soni.

    Seriya: maqsad bajarilgan ketma-ket kunlar. Bugun hali bajarilmagan bo'lsa seriya kechagidan
    hisoblanadi (kun oxirigacha uzilmaydi).
    """
    today = today or timezone.localdate()
    rows = (
        ExamAnswer.objects.filter(
            exam__user=user,
            answered_at__isnull=False,
            answered_at__date__gte=today - timedelta(days=STREAK_LOOKBACK_DAYS),
        )
        .annotate(day=TruncDate("answered_at"))
        .values("day")
        .annotate(n=Count("id"))
    )
    counts = {r["day"]: r["n"] for r in rows}
    goal = user.daily_goal or 20

    def reached(day):
        return counts.get(day, 0) >= goal

    streak = 0
    day = today if reached(today) else today - timedelta(days=1)
    while reached(day):
        streak += 1
        day -= timedelta(days=1)

    done = counts.get(today, 0)
    week = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        week.append({
            "date": d,
            "label": WEEKDAYS_UZ[d.weekday()],
            "count": counts.get(d, 0),
            "reached": reached(d),
            "is_today": i == 0,
        })
    return {
        "goal": goal,
        "today": done,
        "percent": min(100, round(done * 100 / goal)),
        "reached": done >= goal,
        "left": max(0, goal - done),
        "streak": streak,
        "week": week,
    }


def current_session(user):
    """Eng oxirgi tugallanmagan sessiya (imtihon yoki mashq) — "Davom ettirish" uchun. Muddati o'tgan imtihon yopiladi."""
    sessions = (
        Exam.objects.filter(user=user, status=Exam.STATUS_IN_PROGRESS)
        .select_related("topic")
        .annotate(answered=Count("items", filter=Q(items__selected_answer__isnull=False)))
        .order_by("-started_at")[:5]
    )
    for exam in sessions:
        if expire_if_needed(exam):
            continue
        answered = exam.answered
        # Bitta ham javob berilmagan mashq — tasodifan ochilgan; davom ettirishga taklif qilinmaydi
        if not exam.is_exam and answered == 0:
            continue
        exam.answered_count = answered
        exam.minutes_left = (exam.time_left_seconds or 0) // 60
        return exam
    return None


def overall_progress(user, total=None):
    """Mashqda kamida bir marta to'g'ri yechilgan faol savollar ulushi. `total` — faol savollar soni (ma'lum bo'lsa)."""
    if total is None:
        total = Question.objects.filter(is_active=True).count()
    solved = (
        ExamAnswer.objects.filter(
            exam__user=user, exam__mode__in=Exam.PRACTICE_MODES, is_correct=True, question__is_active=True
        )
        .values("question_id").distinct().count()
    )
    return {"total": total, "solved": solved, "percent": round(solved * 100 / total) if total else 0}


def expire_if_needed(exam):
    """Muddat o'tgan ochiq imtihonni yakunlaydi. Yakunlangan bo'lsa True qaytaradi."""
    if exam.is_in_progress and exam.is_expired:
        finish_exam(exam)
        return True
    return False


def save_answer(exam, question_id, answer_id, user=None):
    if user is not None and exam.user_id != user.pk:
        raise Http404
    if not exam.is_in_progress:
        raise ExamError("Bu imtihon allaqachon yakunlangan.")
    # Muddat tekshiruvi transaksiyadan tashqarida: xato ko'tarilganda ham imtihon yopilib qoladi.
    if expire_if_needed(exam):
        raise ExamExpired("Imtihon vaqti tugadi. Javob qabul qilinmadi.")

    with transaction.atomic():
        try:
            item = ExamAnswer.objects.select_for_update().get(exam=exam, question_id=question_id)
        except (ExamAnswer.DoesNotExist, ValueError, TypeError):
            raise ExamError("Bu savol ushbu imtihonga tegishli emas.")
        try:
            answer = Answer.objects.get(pk=answer_id, question_id=item.question_id)
        except (Answer.DoesNotExist, ValueError, TypeError):
            raise ExamError("Bu javob ushbu savolga tegishli emas.")

        # Birinchi javob hisoblanadi — to'g'ri/xato darrov ko'rsatiladi, keyin o'zgartirib bo'lmaydi.
        if item.selected_answer_id is not None:
            return item

        item.selected_answer = answer
        item.is_correct = answer.is_correct  # faqat serverdagi qiymat
        item.answered_at = timezone.now()
        item.save(update_fields=["selected_answer", "is_correct", "answered_at"])
        return item


@transaction.atomic
def finish_exam(exam):
    exam = Exam.objects.select_for_update().get(pk=exam.pk)
    if not exam.is_in_progress:
        return exam
    now = timezone.now()
    exam.score = exam.items.filter(is_correct=True).count()
    if exam.is_exam:
        # Javob berilmagan savol is_correct=False — ya'ni xato hisoblanadi.
        exam.is_passed = exam.mistakes <= settings.EXAM_MAX_MISTAKES
        exam.status = Exam.STATUS_EXPIRED if now > exam.deadline else Exam.STATUS_FINISHED
        exam.finished_at = min(now, exam.deadline)
    else:
        exam.is_passed = None
        exam.status = Exam.STATUS_FINISHED
        exam.finished_at = now
    exam.save(update_fields=["score", "is_passed", "status", "finished_at"])
    return exam


def user_stats(user):
    finished = Exam.objects.filter(user=user, status__in=FINISHED_STATUSES)
    exams = list(finished.filter(mode=Exam.MODE_EXAM).only("score", "total_questions", "is_passed"))
    percents = [e.percent for e in exams]

    # Biletlar bo'yicha faqat mashq: imtihon savollari barcha biletlardan tasodifiy (har biletga 0–2 ta),
    # ular hisobga olinsa ochilmagan biletlarda ham foiz chiqib qoladi
    rows = (
        ExamAnswer.objects.filter(exam__in=finished, exam__mode__in=Exam.PRACTICE_MODES, selected_answer__isnull=False)
        .values("question__topic_id")
        .annotate(total=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
    )
    by_topic = {r["question__topic_id"]: r for r in rows}
    topics = []
    for topic in Topic.objects.all():
        r = by_topic.get(topic.pk)
        total = r["total"] if r else 0
        correct = r["correct"] if r else 0
        topics.append({
            "topic": topic,
            "total": total,
            "correct": correct,
            "percent": round(correct * 100 / total) if total else 0,
        })
    attempted = [t for t in topics if t["total"]]
    weakest = sorted(attempted, key=lambda t: (t["percent"], -t["total"]))[:3]

    return {
        "total_exams": len(exams),
        "passed_exams": sum(1 for e in exams if e.is_passed),
        "average_percent": round(sum(percents) / len(percents)) if percents else 0,
        "best_percent": max(percents) if percents else 0,
        "practice_count": finished.filter(mode__in=Exam.PRACTICE_MODES).count(),
        "topics": topics,
        "practiced_topics": attempted,
        "weakest_topics": weakest,
    }


def topic_progress(user):
    """{topic_id: %} — biletdagi faol savollardan mashqda kamida bir marta to'g'ri yechilganlari ulushi."""
    solved = (
        ExamAnswer.objects.filter(
            exam__user=user, exam__mode__in=Exam.PRACTICE_MODES, is_correct=True, question__is_active=True
        )
        .values("question__topic_id")
        .annotate(n=Count("question_id", distinct=True))
    )
    solved = {r["question__topic_id"]: r["n"] for r in solved}
    totals = Topic.objects.annotate(n=Count("questions", filter=Q(questions__is_active=True))).values("id", "n")
    return {t["id"]: round(solved.get(t["id"], 0) * 100 / t["n"]) if t["n"] else 0 for t in totals}
