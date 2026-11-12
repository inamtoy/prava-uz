"""Savol izohlarini JSON fayldan import qilish.

Fayl formati (savollar/izohlar/bilet_NNN.json):
    {"bilet": "...", "savollar": [{"question_id": 1, "savol": "...", "izoh": "...", "ishonch": "yuqori", ...}]}

Qoidalar:
- Faqat explanation BO'SH savollar to'ldiriladi — mavjud izoh hech qachon ustidan yozilmaydi.
- izoh bo'sh yoki ishonch "yuqori" bo'lmagan yozuvlar o'tkazib yuboriladi.
- Bazadagi savol matni fayldagi "savol" bilan mos kelmasa — o'tkazib yuboriladi (ID almashgan bo'lishi mumkin).

    python manage.py import_explanations savollar/izohlar/bilet_001.json          # faqat ko'rsatadi
    python manage.py import_explanations savollar/izohlar/bilet_001.json --apply  # bazaga yozadi
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from quiz.models import Question


def _norm(s):
    return " ".join((s or "").split())


class Command(BaseCommand):
    help = "JSON fayldagi izohlarni explanation'i bo'sh savollarga yozadi (--apply'siz faqat ko'rsatadi)"

    def add_arguments(self, parser):
        parser.add_argument("path", help="JSON fayl yo'li")
        parser.add_argument("--apply", action="store_true", help="O'zgarishlarni bazaga yozish")

    def handle(self, *args, **opts):
        path = Path(opts["path"])
        if not path.exists():
            raise CommandError(f"Fayl topilmadi: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON xato: {e}")
        rows = data.get("savollar") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise CommandError("Faylda 'savollar' ro'yxati yo'q")

        questions = Question.objects.in_bulk([r.get("question_id") for r in rows if r.get("question_id")])
        updates, skipped = [], []
        for r in rows:
            qid, text = r.get("question_id"), (r.get("izoh") or "").strip()
            q = questions.get(qid)
            if not text:
                skipped.append((qid, "izoh yo'q (" + (r.get("holat") or "tekshirish kerak") + ")"))
            elif r.get("ishonch") != "yuqori":
                skipped.append((qid, f"ishonch: {r.get('ishonch')}"))
            elif q is None:
                skipped.append((qid, "bazada bunday savol yo'q"))
            elif r.get("savol") and _norm(r["savol"]) != _norm(q.text):
                skipped.append((qid, "savol matni bazadagidan farq qiladi"))
            elif q.explanation.strip():
                skipped.append((qid, "izoh allaqachon bor — ustidan yozilmaydi"))
            else:
                q.explanation = text
                updates.append(q)

        w = self.stdout.write
        w(f"Fayl: {path} — {len(rows)} ta yozuv\n")
        for q in updates:
            w(f"  + #{q.pk}: {q.explanation[:110]}{'…' if len(q.explanation) > 110 else ''}")
        for qid, why in skipped:
            w(f"  - #{qid}: o'tkazildi — {why}")
        w(f"\nYoziladi: {len(updates)} ta, o'tkaziladi: {len(skipped)} ta")

        if not opts["apply"]:
            w(self.style.WARNING("Reja rejimi: hech narsa o'zgarmadi. Bajarish uchun: --apply"))
            return
        with transaction.atomic():
            # Poyga holatidan himoya: yozish paytida ham faqat bo'sh izohlarni yangilaymiz
            n = sum(Question.objects.filter(pk=q.pk, explanation="").update(explanation=q.explanation) for q in updates)
        w(self.style.SUCCESS(f"{n} ta savolga izoh yozildi."))
