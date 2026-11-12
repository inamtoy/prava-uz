"""To'liq o'lchamli rasmlarni bazadagi savollarga moslash.

Tartib:
  a) Bazadagi savol → Excel qatori (savol matni + javoblar to'plami; bo'sh joy, harf, ʻ/'/` farqi normallashtiriladi).
     Bilet raqamlari ishlatilmaydi (bazada 91, PDF/Excel'da 139 bilet).
  b) Excel qatoridagi "Rasm fayli" → kutilgan to'liq rasm (--images-dir ichida).
  c) Bazadagi kichik rasmning dHash'i kutilgan fayl bilan solishtiriladi:
       aniq                    — masofa <= --max-dist (default 6): almashtirishga tayyor
       NOTO'G'RI BIRIKTIRILGAN — kutilgan fayl kichik rasmga o'xshamaydi; CSV'da kutilgan fayl va
                                 kichik rasmga eng o'xshash fayl (ikkala nomzod) ko'rsatiladi
       qo'lda tekshirish       — Excel'da mos qator yo'q / Excel'da rasm fayli yo'q / fayl papkada yo'q
     --images-dir topilmasa, c) bosqichi o'tkaziladi ("rasm tekshirilmadi").

Sukut bo'yicha — faqat hisobot (CSV + jadval), hech narsa o'zgarmaydi.
--apply: faqat "aniq" toifasi. To'liq rasm media/questions/<eski_nom>_asl.<ext> sifatida eski faylning
YONIGA nusxalanadi, savol shu faylga ulanadi. Eski fayl o'chirilmaydi.

    python manage.py match_images
    python manage.py match_images --images-dir savollar\\rasmlar_asl --out match_images.csv
    python manage.py match_images --apply
"""
import csv
import shutil
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from quiz.models import Question
from quiz.source_match import DEFAULT_XLSX, SourceIndex, row_ref

EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
WATCH = (5910, 5911)  # rasmi savol matniga mos kelmaydi deb gumon qilinganlar
OK, WRONG, MANUAL, SKIPPED = "aniq", "NOTO'G'RI BIRIKTIRILGAN", "qo'lda tekshirish", "rasm tekshirilmadi"
SUFFIX = "_asl"


def dhash(path):
    """64 bitlik farq-xeshi (dHash). Fayl ochilmasa None."""
    try:
        with Image.open(path) as im:
            im.draft("L", (64, 64))  # JPEG uchun tez kichraytirish
            px = im.convert("L").resize((9, 8), Image.LANCZOS).load()
    except (OSError, UnidentifiedImageError, ValueError):
        return None
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (px[x, y] > px[x + 1, y])
    return bits


def hamming(a, b):
    return (a ^ b).bit_count()


class Command(BaseCommand):
    help = "To'liq o'lchamli rasmlarni savollarga moslash (sukut bo'yicha dry-run, CSV hisobot)"

    def add_arguments(self, parser):
        parser.add_argument("--images-dir", default="savollar/rasmlar_asl", help="To'liq o'lchamli rasmlar papkasi")
        parser.add_argument("--xlsx", default=DEFAULT_XLSX, help="Manba Excel (\"Savollar\" varag'i)")
        parser.add_argument("--out", default="match_images.csv", help="CSV hisobot fayli")
        parser.add_argument("--max-dist", type=int, default=6, help="'aniq' uchun eng katta dHash masofasi (default 6)")
        parser.add_argument("--apply", action="store_true", help="'aniq' toifasini almashtirish (eski fayl qoladi)")

    def handle(self, *args, **opts):
        w = self.stdout.write
        if not Path(opts["xlsx"]).exists():
            raise CommandError(f"Excel topilmadi: {opts['xlsx']}")
        src = SourceIndex(opts["xlsx"])
        w(f"Excel: {len(src.rows)} ta qator")

        img_dir = Path(opts["images_dir"])
        have_images = img_dir.is_dir()
        files, hashes = {}, {}
        if have_images:
            files = {p.name.lower(): p for p in img_dir.rglob("*") if p.suffix.lower() in EXTS}
            w(f"To'liq rasmlar: {len(files)} ta ({img_dir}), xesh hisoblanmoqda…")
            for name, p in files.items():
                h = dhash(p)
                if h is not None:
                    hashes[name] = h
        else:
            w(self.style.WARNING(f"Rasmlar papkasi topilmadi: {img_dir} — faqat Excel bo'yicha moslash (c bosqichi o'tkaziladi)"))
        if opts["apply"] and not have_images:
            raise CommandError("--apply uchun rasmlar papkasi kerak")

        questions = Question.objects.select_related("topic").prefetch_related("answers").order_by("id")
        rows, plan = [], []
        for q in questions:
            db_name = Path(q.image.name).name if q.image else ""
            m = src.match(q, [a.text for a in q.answers.all()], db_name)
            excel_img = m.row.image_name if m.row is not None else ""
            if not db_name and not excel_img:
                continue  # rasmsiz savol, Excel'da ham rasm yo'q — bu hisobotga tegishli emas
            expected = excel_img.lower()
            exp_dist = best_name = best_dist = None
            thumb = dhash(q.image.path) if db_name else None
            notes = [m.note] if m.note else []

            if m.row is None or m.status not in ("mos", "mos (tinish farqi)"):
                cat = MANUAL
                notes.insert(0, f"Excel'da mos qator topilmadi ({m.status})")
            elif not db_name:
                cat = MANUAL
                notes.insert(0, "bazada rasm yo'q, Excel'da bor")
            elif not excel_img:
                cat = MANUAL
                notes.insert(0, "Excel'da rasm fayli ko'rsatilmagan" + (f" — {m.row.note}" if m.row.note else ""))
            elif not have_images:
                cat = SKIPPED
            elif expected not in files:
                cat = MANUAL
                notes.insert(0, "kutilgan fayl papkada yo'q")
            elif thumb is None or expected not in hashes:
                cat = MANUAL
                notes.insert(0, "rasm faylini ochib bo'lmadi")
            else:
                exp_dist = hamming(thumb, hashes[expected])
                best_name, best_dist = min(hashes.items(), key=lambda kv: (hamming(thumb, kv[1]), kv[0] != expected))
                best_dist = hamming(thumb, best_dist)
                cat = OK if exp_dist <= opts["max_dist"] else WRONG
            if q.pk in WATCH:
                notes.append("GUMON: rasm savol matniga mos emas (oldingi tekshiruv)")
            if db_name.lower() != expected and expected and db_name:
                notes.append(f"bazadagi nom boshqa: {db_name}")

            rows.append({
                "question_id": q.pk, "bilet": q.topic.name, "faol": int(q.is_active), "savol": q.text[:120],
                "db_rasm": db_name, "excel_qator": row_ref(m.row), "excel_moslik": m.status,
                "kutilgan_fayl": excel_img, "kutilgan_masofa": "" if exp_dist is None else exp_dist,
                "eng_yaqin_fayl": "" if best_name is None else files[best_name].name,
                "eng_yaqin_masofa": "" if best_dist is None else best_dist,
                "toifa": cat, "izoh": "; ".join(notes),
            })
            if cat == OK:
                plan.append((q, files[expected]))

        out = Path(opts["out"])
        with open(out, "w", encoding="utf-8-sig", newline="") as f:  # BOM — Excel o'zbekcha harflarni to'g'ri ochadi
            writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["question_id"])
            writer.writeheader()
            writer.writerows(rows)

        stats = Counter(r["toifa"] for r in rows)
        w(f"\nRasm bilan bog'liq savollar: {len(rows)} ta")
        for k in (OK, WRONG, MANUAL, SKIPPED):
            if stats.get(k):
                w(f"  {k:<26} {stats[k]}")
        reasons = Counter(r["izoh"].split(";")[0] for r in rows if r["toifa"] == MANUAL)
        for reason, n in reasons.most_common():
            w(f"      {n:>4}  {reason}")

        w("\n#5910, #5911:")
        for r in rows:
            if r["question_id"] in WATCH:
                w(f"  #{r['question_id']} ({r['bilet']}, Excel {r['excel_qator']}): {r['toifa']}")
                w(f"     kutilgan: {r['kutilgan_fayl'] or '—'} (masofa {r['kutilgan_masofa'] if r['kutilgan_masofa'] != '' else '—'}), "
                  f"eng yaqin: {r['eng_yaqin_fayl'] or '—'} (masofa {r['eng_yaqin_masofa'] if r['eng_yaqin_masofa'] != '' else '—'})")
        w(self.style.SUCCESS(f"\nCSV: {out.resolve()}"))

        if not opts["apply"]:
            w(self.style.WARNING("Dry-run: bazaga va media/ ga hech narsa yozilmadi. Almashtirish: --apply (faqat 'aniq')."))
            return
        self._apply(plan)

    def _apply(self, plan):
        media = Path(settings.MEDIA_ROOT)
        copied = updated = 0
        with transaction.atomic():
            for q, src_path in plan:
                old = Path(q.image.name)
                if old.stem.endswith(SUFFIX):
                    continue  # allaqachon almashtirilgan
                new_rel = (old.parent / f"{old.stem}{SUFFIX}{src_path.suffix.lower()}").as_posix()
                dest = media / new_rel
                if not dest.exists():
                    shutil.copy2(src_path, dest)
                    copied += 1
                # Poyga holatidan himoya: faqat rasm hali o'sha eski fayl bo'lsa yangilanadi
                updated += Question.objects.filter(pk=q.pk, image=q.image.name).update(image=new_rel)
        self.stdout.write(self.style.SUCCESS(
            f"{copied} ta fayl nusxalandi, {updated} ta savol yangi rasmga ulandi. Eski fayllar media/ da qoldi."))
