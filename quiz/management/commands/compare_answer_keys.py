"""Javob kalitlarini manba Excel bilan solishtirish — FAQAT HISOBOT (bazaga hech narsa yozmaydi).

Har bir bazadagi savol Excel qatoriga savol matni + javoblar to'plami bo'yicha moslanadi (quiz.source_match),
so'ng bazadagi to'g'ri javob Excel'dagi "To'g'ri javob matni" (K ustuni) bilan solishtiriladi.
Qo'shimcha: Excel'ning o'zida "To'g'ri javob" harfi (J) va "To'g'ri javob matni" (K) bir-biriga mosmi.

Holatlar:
    mos                — bazadagi to'g'ri javob = manbadagi
    KALIT FARQ         — bazadagi to'g'ri javob manbadagidan boshqa
    manba ziddiyatli   — Excel'da harf (J) va matn (K) turli javobni ko'rsatadi
    manbada topilmadi  — Excel'da savol matni + javoblari mos qator yo'q

    python manage.py compare_answer_keys                      # barcha farqlar CSV'ga
    python manage.py compare_answer_keys --ids 6064 6074      # faqat shu savollar (jadval ekranga)
"""
import csv
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from quiz.models import Question
from quiz.source_match import DEFAULT_XLSX, SourceIndex, loose, norm, row_correct_by_letter, row_ref

# dedupe_questions hisobotidagi 1, 2, 9-guruhlar: matni bir xil, to'g'ri javobi boshqa
KEY_GROUPS = [(6064, 6074), (6085, 6415), (7033, 7228)]


def same(a, b):
    return norm(a) == norm(b) or (loose(a) and loose(a) == loose(b))


class Command(BaseCommand):
    help = "Bazadagi to'g'ri javoblarni manba Excel bilan solishtiradi (CSV hisobot, bazani o'zgartirmaydi)"

    def add_arguments(self, parser):
        parser.add_argument("--xlsx", default=DEFAULT_XLSX)
        parser.add_argument("--out", default="answer_keys_diff.csv", help="Farqlar CSV fayli")
        parser.add_argument("--ids", nargs="*", type=int, help="Faqat shu savol ID'lari")

    def handle(self, *args, **opts):
        if not Path(opts["xlsx"]).exists():
            raise CommandError(f"Excel topilmadi: {opts['xlsx']}")
        src = SourceIndex(opts["xlsx"])
        qs = Question.objects.select_related("topic").prefetch_related("answers").order_by("id")
        results = {}
        for q in qs:  # moslash hamma savollar bo'yicha (bir xil qatorlar to'g'ri taqsimlanishi uchun)
            answers = list(q.answers.all())
            m = src.match(q, [a.text for a in answers], q.image.name.rsplit("/", 1)[-1] if q.image else "")
            db_correct = [a.text for a in answers if a.is_correct]
            db_text = db_correct[0] if len(db_correct) == 1 else " | ".join(db_correct) or "—"
            row = m.row
            src_k = row.correct_text if row else ""
            src_j = row_correct_by_letter(row)
            if row is None:
                status = "manbada topilmadi"
            elif src_k and src_j and not same(src_k, src_j):
                status = "manba ziddiyatli"
            elif same(db_text, src_k or src_j):
                status = "mos"
            else:
                status = "KALIT FARQ"
            results[q.pk] = {
                "question_id": q.pk, "bilet": q.topic.name, "faol": int(q.is_active), "savol": q.text[:150],
                "excel_qator": row_ref(row), "excel_moslik": m.status,
                "bazadagi_togri": db_text, "manba_togri_matn": src_k, "manba_togri_harf": src_j,
                "holat": status, "izoh": m.note,
            }

        w = self.stdout.write
        stats = Counter(r["holat"] for r in results.values())
        w(f"Savollar: {len(results)} ta (Excel: {len(src.rows)} qator)")
        for k in ("mos", "KALIT FARQ", "manba ziddiyatli", "manbada topilmadi"):
            w(f"  {k:<18} {stats.get(k, 0)}")

        w("\nMatni bir xil, kaliti boshqa savollar (dedupe hisobotidagi 1, 2, 9-guruhlar):")
        for group in KEY_GROUPS:
            for qid in group:
                r = results.get(qid)
                if r:
                    w(f"  #{qid:<5} {r['bilet']:<9} Excel {r['excel_qator'] or '—':<7} {r['holat']:<17} "
                      f"baza: {r['bazadagi_togri'][:45]:<45} | manba: {(r['manba_togri_matn'] or '—')[:45]}")
            w("")

        if opts["ids"]:
            for qid in opts["ids"]:
                r = results.get(qid)
                w(f"#{qid}: " + (str(r) if r else "topilmadi"))
            return

        diff = [r for r in results.values() if r["holat"] != "mos"]
        out = Path(opts["out"])
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(next(iter(results.values()))))
            writer.writeheader()
            writer.writerows(diff)
        w(self.style.SUCCESS(f"Farqlar CSV ({len(diff)} ta): {out.resolve()}"))
        w(self.style.WARNING("Bazaga hech narsa yozilmadi."))
