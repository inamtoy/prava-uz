"""Savollar bilan ishlash uchun umumiy yordamchilar."""


def normalize_text(s):
    """Bo'sh joylar bitta probelga keltiriladi, kichik harfga o'tkaziladi."""
    return " ".join((s or "").split()).lower()


def question_key(text, image):
    """Bir xil savolni aniqlash kaliti: normallashtirilgan matn + rasm fayli yo'li.

    Rasmli savolda `image` — ImageFieldFile yoki yo'l satri; rasmsizda bo'sh.
    """
    name = getattr(image, "name", image) or ""
    return normalize_text(text), name
