"""Savollar Excel faylini (.xlsx) o'qish — qo'shimcha kutubxonasiz (zipfile + XML).

Ustunlar (1-varaq "Savollar"): №, Bilet, Savol №, Savol, Rasm (joylashtirilgan rasm),
A, B, C, D, To'g'ri javob (harf), To'g'ri javob matni, Rasm fayli, Izoh.
"""

import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
NS_DRAW = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

LETTERS = "ABCD"
ANSWER_COLUMNS = "FGHI"
MISSING_IMAGE_NOTE = "Rasm PDFda yo'qolgan"


@dataclass
class Row:
    number: int  # Excel qatori (sarlavhadan keyin 2 dan boshlanadi)
    ticket: int
    position: int
    text: str
    answers: list
    correct: int | None  # answers ichidagi indeks
    image_name: str
    image: bytes | None
    note: str
    problems: list = field(default_factory=list)

    @property
    def image_missing(self):
        return MISSING_IMAGE_NOTE in self.note


def uz_apostrophes(text):
    """` va ' ni o'zbek lotin yozuvidagi belgilarga almashtiradi: oʻ, gʻ (U+02BB), qolgani ʼ (U+02BC)."""
    text = re.sub(r"(?<=[oOgG])[`'‘’]", "ʻ", text)
    return re.sub(r"(?<=\w)[`'‘’]", "ʼ", text)


def clean(text):
    return uz_apostrophes(" ".join((text or "").split()))


def _rels(zf, path):
    """Fayl uchun .rels: {rId: zip ichidagi to'liq yo'l}."""
    folder, name = posixpath.split(path)
    rels_path = posixpath.join(folder, "_rels", name + ".rels")
    if rels_path not in zf.namelist():
        return {}
    result = {}
    for rel in ET.fromstring(zf.read(rels_path)).iter(f"{NS_PKG_REL}Relationship"):
        target = rel.get("Target")
        target = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(folder, target))
        result[rel.get("Id")] = target
    return result


def _first_sheet(zf):
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    sheet = workbook.find(f"{NS_MAIN}sheets/{NS_MAIN}sheet")
    return _rels(zf, "xl/workbook.xml")[sheet.get(f"{NS_REL}id")]


def _shared_strings(zf):
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{NS_MAIN}t")) for si in root.iter(f"{NS_MAIN}si")]


def _cells(zf, sheet_path):
    """{qator raqami (0 dan): {ustun harfi: matn}}."""
    shared = _shared_strings(zf)
    rows = {}
    for row in ET.fromstring(zf.read(sheet_path)).iter(f"{NS_MAIN}row"):
        values = {}
        for cell in row.iter(f"{NS_MAIN}c"):
            col = re.match(r"[A-Z]+", cell.get("r")).group()
            kind = cell.get("t")
            if kind == "inlineStr":
                value = "".join(t.text or "" for t in cell.iter(f"{NS_MAIN}t"))
            else:
                v = cell.find(f"{NS_MAIN}v")
                value = v.text if v is not None and v.text else ""
                if kind == "s" and value:
                    value = shared[int(value)]
            values[col] = value
        rows[int(row.get("r")) - 1] = values
    return rows


def _images_by_row(zf, sheet_path):
    """{qator raqami (0 dan): rasm baytlari} — varaqqa joylashtirilgan rasmlar."""
    sheet_rels = _rels(zf, sheet_path)
    images = {}
    for drawing_path in (p for p in sheet_rels.values() if "/drawings/" in p):
        drawing_rels = _rels(zf, drawing_path)
        for anchor in ET.fromstring(zf.read(drawing_path)):
            row = anchor.find(f"{NS_DRAW}from/{NS_DRAW}row")
            blip = anchor.find(f".//{NS_A}blip")
            if row is None or blip is None:
                continue
            images.setdefault(int(row.text), zf.read(drawing_rels[blip.get(f"{NS_REL}embed")]))
    return images


def _int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def read_questions(path):
    """Excel faylidagi savollar ro'yxati (Row). Muammoli qatorlar `problems` bilan qaytadi."""
    with zipfile.ZipFile(path) as zf:
        sheet = _first_sheet(zf)
        cells = _cells(zf, sheet)
        images = _images_by_row(zf, sheet)

    rows = []
    for index in sorted(i for i in cells if i > 0):  # 0 — sarlavha
        c = cells[index]
        text = clean(c.get("D"))
        if not text:
            continue
        options = [(letter, clean(c.get(col))) for letter, col in zip(LETTERS, ANSWER_COLUMNS)]
        options = [(letter, value) for letter, value in options if value]
        letter = (c.get("J") or "").strip().upper()
        correct = next((i for i, (l, _) in enumerate(options) if l == letter), None)
        row = Row(
            number=index + 1,
            ticket=_int(c.get("B")),
            position=_int(c.get("C")),
            text=text,
            answers=[value for _, value in options],
            correct=correct,
            image_name=(c.get("L") or "").strip(),
            image=images.get(index),
            note=(c.get("M") or "").strip(),
        )
        if row.ticket is None:
            row.problems.append("bilet raqami yoʻq")
        if not 2 <= len(row.answers) <= 4:
            row.problems.append(f"{len(row.answers)} ta javob (2–4 boʻlishi kerak)")
        if correct is None:
            row.problems.append("toʻgʻri javob belgilanmagan")
        rows.append(row)
    return rows
