"""Takroriy savollar hisoboti (faqat o'qiydi, bazaga hech narsa yozmaydi).

Takroriy = faol savollar, matni (bo'sh joylar va harf katta-kichikligidan qat'i nazar) va rasmi bir xil.
Bunday savollar biletlarda qoladi (rasmiy biletlarda ham takrorlanadi); imtihonda esa
results.services.start_exam ularning faqat bittasini tanlaydi.

Hisobot har guruh uchun ko'rsatadi:
- savollar qaysi biletlarda va necha marta ishlatilgan;
- javoblar to'plami bir xilmi ("bir xil") yoki farq qiladimi ("FARQ" — qaysi javoblar faqat bittasida bor).
  Solishtirishda apostrof, tinish belgilari va kirill/lotin o'xshash harflar farqi e'tiborga olinmaydi.

    python manage.py dedupe_questions
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count, Prefetch

from quiz.models import Answer, Question
from quiz.utils import normalize_text, question_key

# Kirill harflari, ko'rinishi lotinchaga o'xshash (Excel'dagi aralash yozuv: "30 м")
_LOOKALIKE = str.maketrans("аеосрхмкту", "aeocpxmkty")


def _loose(s):
    """Javoblarni solishtirish uchun: apostrof, tinish belgilari va kirill/lotin o'xshash harflar farqi e'tiborsiz."""
    s = normalize_text(s).translate(_LOOKALIKE)
    # ʼ ʻ (U+02BC, U+02BB) Python uchun "harf" — ularni alohida olib tashlaymiz
    return "".join(ch for ch in s if ch.isalnum() and ch not in "ʼʻ")


class Command(BaseCommand):
    help = "Takroriy savollar hisoboti (bazani o'zgartirmaydi)"

    def handle(self, *args, **opts):
        qs = (Question.objects.filter(is_active=True)
              .select_related("topic")
              .annotate(uses=Count("exam_answers", distinct=True))
              .prefetch_related(Prefetch("answers", queryset=Answer.objects.order_by("id"))))
        groups = defaultdict(list)
        for q in qs:
            groups[question_key(q.text, q.image)].append(q)
        groups = [g for g in groups.values() if len(g) > 1]
        groups.sort(key=lambda g: min(q.pk for q in g))

        def sig(q):
            return (frozenset(_loose(a.text) for a in q.answers.all()),
                    frozenset(_loose(a.text) for a in q.answers.all() if a.is_correct))

        w = self.stdout.write
        w(f"Takroriy guruhlar: {len(groups)}\n")
        different = 0
        for i, g in enumerate(groups, 1):
            same = len({sig(q) for q in g}) == 1
            different += not same
            w(f"[{i}] {g[0].text[:90]}")
            w(f"    rasm: {g[0].image.name if g[0].image else '—'}   javoblar: {'bir xil' if same else 'FARQ'}")
            for q in sorted(g, key=lambda q: q.pk):
                correct = next((a.text for a in q.answers.all() if a.is_correct), "?")
                w(f"    #{q.pk:<6} {q.topic.name:<10} ishlatilgan: {q.uses:<3} to'g'ri: {correct[:60]}")
            if not same:
                for q in sorted(g, key=lambda q: q.pk):
                    others = set().union(*(sig(o)[0] for o in g if o.pk != q.pk))
                    for a in q.answers.all():
                        if _loose(a.text) not in others:
                            w(f"      faqat #{q.pk}da: {'[to`g`ri] ' if a.is_correct else ''}{a.text[:100]}")
            w("")

        n = sum(len(g) for g in groups)
        w(f"Jami: {len(groups)} guruh, {n} ta savol; javoblari farq qiladigan guruhlar: {different}")
        w("Imtihonda har guruhdan faqat bittasi tanlanadi (results.services.start_exam). Bazaga hech narsa yozilmadi.")
