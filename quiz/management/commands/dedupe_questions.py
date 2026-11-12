"""Takroriy savollarni nofaol qilish (o'chirmaydi).

Takroriy = faol savollar, matni (bo'sh joylarsiz) va rasmi bir xil. Har guruhda bittasi qoladi:
imtihon/mashqlarda ko'proq ishlatilgani (ExamAnswer qatorlari soni), teng bo'lsa ID'si kichigi.
Qolganlariga is_active=False qo'yiladi.

Xavfsizlik:
- Javoblar to'plami yoki to'g'ri javobi farq qiladigan guruhga tegilmaydi — "qo'lda ko'rib chiqish" deb chiqariladi.
- Jarayondagi (in_progress) imtihonda turgan savol nofaol qilinmaydi.

    python manage.py dedupe_questions          # faqat reja (hech narsa o'zgarmaydi)
    python manage.py dedupe_questions --apply  # rejani bajarish
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Prefetch

from quiz.models import Answer, Question
from results.models import Exam, ExamAnswer


def _norm(s):
    return " ".join((s or "").split()).lower()


# Kirill harflari, ko'rinishi lotinchaga o'xshash (Excel'dagi aralash yozuv: "30 м")
_LOOKALIKE = str.maketrans("аеосрхмкту", "aeocpxmkty")


def _loose(s):
    """Javoblarni solishtirish uchun: apostrof, tinish belgilari va kirill/lotin o'xshash harflar farqi e'tiborsiz."""
    s = _norm(s).translate(_LOOKALIKE)
    # ʼ ʻ (U+02BC, U+02BB) Python uchun "harf" — ularni alohida olib tashlaymiz
    return "".join(ch for ch in s if ch.isalnum() and ch not in "ʼʻ")


class Command(BaseCommand):
    help = "Takroriy savollarni topadi va (--apply bilan) ortiqchalarini is_active=False qiladi"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="O'zgarishlarni bazaga yozish")

    def handle(self, *args, **opts):
        qs = (Question.objects.filter(is_active=True)
              .select_related("topic")
              .annotate(uses=Count("exam_answers", distinct=True))
              .prefetch_related(Prefetch("answers", queryset=Answer.objects.order_by("id"))))
        groups = defaultdict(list)
        for q in qs:
            groups[(_norm(q.text), q.image.name if q.image else "")].append(q)
        groups = [g for g in groups.values() if len(g) > 1]
        groups.sort(key=lambda g: min(q.pk for q in g))

        busy = set(ExamAnswer.objects.filter(exam__status=Exam.STATUS_IN_PROGRESS)
                   .values_list("question_id", flat=True))

        to_deactivate, manual = [], []
        w = self.stdout.write
        w(f"Takroriy guruhlar: {len(groups)}\n")
        for i, g in enumerate(groups, 1):
            keep = sorted(g, key=lambda q: (-q.uses, q.pk))[0]
            sig = lambda q: (frozenset(_loose(a.text) for a in q.answers.all()),
                             frozenset(_loose(a.text) for a in q.answers.all() if a.is_correct))
            same = len({sig(q) for q in g}) == 1
            w(f"[{i}] {g[0].text[:90]}")
            w(f"    rasm: {g[0].image.name if g[0].image else '—'}")
            for q in sorted(g, key=lambda q: q.pk):
                correct = next((a.text for a in q.answers.all() if a.is_correct), "?")
                if not same:
                    mark = "QO'LDA"
                elif q.pk == keep.pk:
                    mark = "QOLADI"
                elif q.pk in busy:
                    mark = "QOLADI (jarayondagi imtihonda)"
                else:
                    mark = "NOFAOL"
                    to_deactivate.append(q)
                w(f"    #{q.pk:<6} {q.topic.name:<10} ishlatilgan: {q.uses:<3} to'g'ri: {correct[:50]:<50} -> {mark}")
            if not same:
                manual.append(g)
                w("    ! Javoblari yoki to'g'ri javobi farq qiladi — tegilmaydi, qo'lda ko'rib chiqing")
                for q in sorted(g, key=lambda q: q.pk):
                    others = set().union(*(sig(o)[0] for o in g if o.pk != q.pk))
                    for a in q.answers.all():
                        if _loose(a.text) not in others:
                            w(f"      faqat #{q.pk}da: {'[to`g`ri] ' if a.is_correct else ''}{a.text[:100]}")
            w("")

        per_topic = defaultdict(int)
        for q in to_deactivate:
            per_topic[q.topic.name] += 1
        w(f"Jami: {len(groups)} guruh, nofaol qilinadi: {len(to_deactivate)} ta savol, qo'lda: {len(manual)} guruh")
        if per_topic:
            w("Biletlar bo'yicha (shuncha savol kamayadi): " + ", ".join(f"{k}: -{v}" for k, v in sorted(per_topic.items())))

        if not opts["apply"]:
            w(self.style.WARNING("\nReja rejimi: hech narsa o'zgarmadi. Bajarish uchun: --apply"))
            return
        with transaction.atomic():
            n = Question.objects.filter(pk__in=[q.pk for q in to_deactivate], is_active=True).update(is_active=False)
        w(self.style.SUCCESS(f"\n{n} ta savol nofaol qilindi (o'chirilmadi)."))
