"""To'liq o'lchamli rasmlarni bazadagi savollarga moslash — FAQAT HISOBOT (dry-run).

Bazaga va media/ ga hech narsa yozmaydi. Natija — CSV fayl va qisqa xulosa.

Dalillar (kuchlisidan kuchsiziga):
1. Rasm o'xshashligi — bazadagi kichik rasm va manbadagi to'liq rasm 9x8 kulrangga kichraytirilib,
   dHash (64 bit) olinadi; Hamming masofasi qancha kichik bo'lsa, shuncha o'xshash (0 — bir xil).
2. Matn va javoblar — agar --manifest berilsa (PDF'dan olingan matnlar): normallashtirilgan savol matni
   tengligi/o'xshashligi va javoblar to'plamining kesishuvi (Jaccard).
3. Fayl nomi — bazadagi rasm nomi bilan bir xil (PDF va bazada bilet raqamlari mos emas, shuning uchun kuchsiz dalil).

Moslik darajasi:
    aniq      — rasm masofasi <= 6 va (manifest matni mos yoki fayl nomi bir xil)
    yuqori    — rasm masofasi <= 6, raqobatchi yo'q
    o'rta     — rasm masofasi 7–12, yoki <= 6 lekin yaqin raqobatchi bor (rasm bir necha marta uchraydi)
    past      — faqat matn/javoblar mos (rasm o'xshamaydi)
    topilmadi — hech qaysi dalil yetarli emas

Manifest CSV (ixtiyoriy, UTF-8) ustunlari:
    file,text,answers,correct
    b085_s03_0.jpeg,"Savol matni","Javob A|Javob B|Javob C",2      (correct — 1 dan boshlanadi, bo'sh bo'lishi mumkin)

    python manage.py match_images --images-dir D:\\rasmlar
    python manage.py match_images --images-dir D:\\rasmlar --manifest D:\\rasmlar\\manifest.csv --out match.csv
"""
import csv
import difflib
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from PIL import Image, UnidentifiedImageError

from quiz.models import Question
from quiz.utils import normalize_text

EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
WATCH = (5910, 5911)  # rasmi savol matniga mos kelmaydi deb gumon qilinganlar


def dhash(path):
    """64 bitlik farq-xeshi (dHash). Fayl ochilmasa None."""
    try:
        with Image.open(path) as im:
            im.draft("L", (64, 64))  # JPEG uchun tez kichraytirish
            px = im.convert("L").resize((9, 8), Image.LANCZOS).load()
    except (OSError, UnidentifiedImageError):
        return None
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (px[x, y] > px[x + 1, y])
    return bits


def hamming(a, b):
    return (a ^ b).bit_count()


def answers_set(items):
    return {normalize_text(a) for a in items if normalize_text(a)}


class Command(BaseCommand):
    help = "To'liq o'lchamli rasmlarni savollarga moslash rejasi (dry-run, CSV hisobot)"

    def add_arguments(self, parser):
        parser.add_argument("--images-dir", required=True, help="To'liq o'lchamli rasmlar papkasi (ichki papkalar ham)")
        parser.add_argument("--manifest", help="PDF'dan olingan matnlar CSV (file,text,answers,correct)")
        parser.add_argument("--out", default="match_images.csv", help="CSV hisobot fayli (default: match_images.csv)")
        parser.add_argument("--max-dist", type=int, default=12, help="Rasm nomzodi uchun eng katta masofa (default 12)")

    def handle(self, *args, **opts):
        src_dir = Path(opts["images_dir"])
        if not src_dir.is_dir():
            raise CommandError(f"Papka topilmadi: {src_dir}")
        w = self.stdout.write

        # --- Manba rasmlar ---
        files = sorted(p for p in src_dir.rglob("*") if p.suffix.lower() in EXTS)
        if not files:
            raise CommandError(f"Papkada rasm yo'q: {src_dir}")
        w(f"Manba rasmlar: {len(files)} ta, xesh hisoblanmoqda…")
        src = []
        for p in files:
            h = dhash(p)
            if h is None:
                w(self.style.WARNING(f"  ochilmadi: {p.name}"))
            else:
                src.append((p, h))
        by_name = {p.name.lower(): (p, h) for p, h in src}

        # --- Manifest (ixtiyoriy) ---
        manifest = {}
        if opts["manifest"]:
            with open(opts["manifest"], encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    name = (r.get("file") or "").strip().lower()
                    if name:
                        manifest[name] = (normalize_text(r.get("text")),
                                          answers_set((r.get("answers") or "").split("|")))
            w(f"Manifest: {len(manifest)} ta yozuv")
        by_text = {}
        for name, (text, _) in manifest.items():
            by_text.setdefault(text, []).append(name)

        # --- Bazadagi rasmli savollar ---
        questions = (Question.objects.exclude(image="").exclude(image__isnull=True)
                     .select_related("topic").prefetch_related("answers").order_by("topic__order", "id"))
        rows, stats = [], {}
        for q in questions:
            db_name = Path(q.image.name).name
            try:
                qh = dhash(q.image.path)
            except (ValueError, NotImplementedError):
                qh = None
            q_text = normalize_text(q.text)
            q_answers = answers_set(a.text for a in q.answers.all())

            # Rasm nomzodlari: masofa bo'yicha eng yaqin 3 tasi
            # teng masofada nomi bir xil fayl oldinga chiqadi (bir xil rasm bir necha faylda bo'lishi mumkin)
            cands = sorted(((hamming(qh, h), p) for p, h in src),
                           key=lambda t: (t[0], t[1].name.lower() != db_name.lower()))[:3] if qh is not None else []
            best_dist, best = (cands[0][0], cands[0][1]) if cands else (None, None)
            rival = cands[1] if len(cands) > 1 and best_dist is not None and cands[1][0] - best_dist <= 2 else None

            # Matn bo'yicha nomzod (manifest bo'lsa)
            text_file, text_score, ans_score = None, 0.0, 0.0
            if manifest:
                exact = by_text.get(q_text, [])
                pool = exact or [n for n, (t, _) in manifest.items()
                                 if difflib.SequenceMatcher(None, q_text, t).quick_ratio() > 0.8]
                for name in pool:
                    t, ans = manifest[name]
                    ts = 1.0 if t == q_text else difflib.SequenceMatcher(None, q_text, t).ratio()
                    js = len(ans & q_answers) / len(ans | q_answers) if (ans or q_answers) else 0.0
                    if (ts, js) > (text_score, ans_score):
                        text_file, text_score, ans_score = name, ts, js

            name_same = best is not None and best.name.lower() == db_name.lower()
            text_ok = best is not None and text_file == best.name.lower() and text_score >= 0.95 and ans_score >= 0.75

            if best_dist is not None and best_dist <= 6 and (text_ok or name_same):
                level = "aniq"  # raqobatchi bo'lsa ham: o'sha rasm boshqa faylda ham bor, lekin nom/matn tasdiqlaydi
            elif best_dist is not None and best_dist <= 6 and not rival:
                level = "yuqori"
            elif best_dist is not None and best_dist <= opts["max_dist"]:
                level = "o'rta"
            elif text_file and text_score >= 0.95 and ans_score >= 0.75:
                level, best, best_dist = "past", by_name.get(text_file, (None,))[0], None
            else:
                level, best = "topilmadi", None
            if qh is None:
                note = "bazadagi rasm fayli ochilmadi"
            elif rival:
                note = f"raqobatchi: {rival[1].name} (masofa {rival[0]})"
            else:
                note = ""
            if q.pk in WATCH:
                note = (note + "; " if note else "") + "GUMON: rasm savol matniga mos emas"
            stats[level] = stats.get(level, 0) + 1
            rows.append({
                "question_id": q.pk, "bilet": q.topic.name, "faol": int(q.is_active),
                "savol": q.text[:120], "db_rasm": db_name,
                "topilgan_fayl": best.name if best else "", "rasm_masofa": "" if best_dist is None else best_dist,
                "nom_bir_xil": int(name_same), "manifest_fayl": text_file or "",
                "matn_moslik": f"{text_score:.2f}" if manifest else "", "javob_moslik": f"{ans_score:.2f}" if manifest else "",
                "daraja": level,
                "nomzodlar": "; ".join(f"{p.name}:{d}" for d, p in cands),
                "izoh": note,
            })

        out = Path(opts["out"])
        with open(out, "w", encoding="utf-8-sig", newline="") as f:  # BOM — Excel o'zbekcha harflarni to'g'ri ochishi uchun
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["question_id"])
            writer.writeheader()
            writer.writerows(rows)

        # Bir faylga bir nechta savol tushgan holatlar (bir xil rasmli savollar uchun normal bo'lishi mumkin)
        used = {}
        for r in rows:
            if r["topilgan_fayl"]:
                used.setdefault(r["topilgan_fayl"], []).append(r["question_id"])
        shared = {k: v for k, v in used.items() if len(v) > 1}

        w(f"\nRasmli savollar: {len(rows)} ta")
        for k in ("aniq", "yuqori", "o'rta", "past", "topilmadi"):
            w(f"  {k:<10} {stats.get(k, 0)}")
        w(f"Bir faylga bir nechta savol tushgan: {len(shared)} ta fayl")
        unused = len(src) - len(used)
        w(f"Hech qaysi savolga tushmagan manba rasmlar: {unused} ta")

        w("\nAlohida tekshiriladiganlar (#5910, #5911):")
        for r in rows:
            if r["question_id"] in WATCH:
                w(f"  #{r['question_id']} {r['bilet']}: {r['savol'][:70]}")
                w(f"     bazada: {r['db_rasm']}  ->  topildi: {r['topilgan_fayl'] or '—'}  "
                  f"masofa: {r['rasm_masofa']}  daraja: {r['daraja']}")
                w(f"     nomzodlar: {r['nomzodlar']}")
        missing = [r for r in rows if r["daraja"] == "topilmadi"]
        if missing:
            w(f"\nTopilmaganlar ({len(missing)}): " + ", ".join(f"#{r['question_id']}" for r in missing[:40])
              + (" …" if len(missing) > 40 else ""))
        w(self.style.SUCCESS(f"\nCSV: {out.resolve()}"))
        w(self.style.WARNING("Dry-run: bazaga va media/ ga hech narsa yozilmadi."))
