"""Bazadagi savollarni manba Excel qatorlariga (savollar/avtotest_savollar_javoblar.xlsx) moslash.

Bilet raqamlari mos emas (bazada 91 ta 15 talik bilet, PDF/Excel'da 139 ta), shuning uchun moslash
faqat matn bo'yicha: savol matni + javoblar to'plami. Normallashtirish: bo'sh joylar, katta-kichik harf,
apostrof turlari (ʻ ʼ ' ` ‘ ’) farqi e'tiborga olinmaydi.

match_images va compare_answer_keys buyruqlari shu moduldan foydalanadi.
"""
import difflib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from quiz.xlsx_import import read_questions

DEFAULT_XLSX = "savollar/avtotest_savollar_javoblar.xlsx"
_APOS = str.maketrans({c: "'" for c in "ʻʼ`‘’´"})


def norm(s):
    """Bo'sh joy, harf katta-kichikligi va apostrof turlari farqisiz."""
    return " ".join((s or "").split()).lower().translate(_APOS)


def loose(s):
    """Faqat harf va raqamlar — tinish belgilari farqini ham e'tiborsiz qoldirish uchun (zaxira tekshiruv)."""
    return "".join(ch for ch in norm(s) if ch.isalnum())


@dataclass
class Match:
    row: object = None          # xlsx_import.Row yoki None
    status: str = "topilmadi"   # mos | mos (tinish farqi) | javoblar farq | matn o'xshash | topilmadi
    note: str = ""
    alternatives: list = field(default_factory=list)  # boshqa nomzod qatorlar


class SourceIndex:
    def __init__(self, path=DEFAULT_XLSX):
        self.path = Path(path)
        self.rows = read_questions(self.path)
        self.by_text = defaultdict(list)
        for r in self.rows:
            self.by_text[norm(r.text)].append(r)
        self.used = set()  # bitta Excel qatori bitta savolga — bir xil savollar turli qatorlarga taqsimlansin

    @staticmethod
    def _answers(items, fn=norm):
        return frozenset(fn(a) for a in items if fn(a))

    def _pick(self, rows, image_name):
        """Bir nechta teng nomzoddan: rasm fayli nomi bir xil > hali ishlatilmagan > birinchisi."""
        rows = sorted(rows, key=lambda r: (r.image_name.lower() != image_name.lower() if image_name else False,
                                           id(r) in self.used, r.number))
        return rows[0]

    def match(self, question, answers, image_name=""):
        """question — Question, answers — uning javob matnlari ro'yxati, image_name — bazadagi fayl nomi."""
        qa, qa_loose = self._answers(answers), self._answers(answers, loose)
        cands = self.by_text.get(norm(question.text), [])
        result = Match()

        exact = [r for r in cands if self._answers(r.answers) == qa]
        status = "mos"
        if not exact:
            exact = [r for r in cands if self._answers(r.answers, loose) == qa_loose]
            status = "mos (tinish farqi)"
        if exact:
            result.row, result.status = self._pick(exact, image_name), status
            if len(exact) > 1:
                result.note = f"Excel'da {len(exact)} ta bir xil qator"
                result.alternatives = [r for r in exact if r is not result.row]
        elif cands:
            def jac(r):
                ra = self._answers(r.answers, loose)
                return len(ra & qa_loose) / len(ra | qa_loose) if ra | qa_loose else 0
            best = max(cands, key=jac)
            result.status, result.alternatives = "javoblar farq", sorted(cands, key=jac, reverse=True)
            result.note = f"matn bir xil, javoblar mos emas (eng yaqini: bilet {best.ticket} / {best.position}, {jac(best):.0%})"
        else:
            qt = norm(question.text)
            close = difflib.get_close_matches(qt, self.by_text.keys(), n=3, cutoff=0.9)
            if close:
                result.status = "matn o'xshash"
                result.alternatives = [r for t in close for r in self.by_text[t]]
                result.note = "matn aynan topilmadi, o'xshashlari: " + "; ".join(
                    f"bilet {r.ticket}/{r.position}" for r in result.alternatives[:3])
        if result.row is not None:
            self.used.add(id(result.row))
        return result


def row_ref(r):
    return f"{r.ticket}/{r.position}" if r is not None else ""


def row_correct_by_letter(r):
    return r.answers[r.correct] if r is not None and r.correct is not None else ""
