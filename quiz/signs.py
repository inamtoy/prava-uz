"""Pillow bilan oddiy yo'l belgilari rasmlarini chizish (namuna ma'lumotlar uchun)."""

import math

from PIL import Image, ImageDraw, ImageFont

SIZE = 400
RED = (207, 34, 46)
BLUE = (31, 90, 200)
YELLOW = (250, 200, 30)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)


def _font(size):
    for name in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _canvas():
    img = Image.new("RGB", (SIZE, SIZE), WHITE)
    return img, ImageDraw.Draw(img)


def _center_text(draw, text, size, fill):
    font = _font(size)
    box = draw.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text(((SIZE - w) / 2 - box[0], (SIZE - h) / 2 - box[1]), text, font=font, fill=fill)


def _polygon(n, radius, rotation=0.0):
    c = SIZE / 2
    return [
        (c + radius * math.cos(rotation + 2 * math.pi * i / n), c + radius * math.sin(rotation + 2 * math.pi * i / n))
        for i in range(n)
    ]


def speed_limit(value=70):
    img, d = _canvas()
    d.ellipse((20, 20, SIZE - 20, SIZE - 20), fill=RED)
    d.ellipse((70, 70, SIZE - 70, SIZE - 70), fill=WHITE)
    _center_text(d, str(value), 140, BLACK)
    return img


def stop():
    img, d = _canvas()
    d.polygon(_polygon(8, 185, math.pi / 8), fill=WHITE)
    d.polygon(_polygon(8, 175, math.pi / 8), fill=RED)
    _center_text(d, "STOP", 100, WHITE)
    return img


def no_entry():
    img, d = _canvas()
    d.ellipse((20, 20, SIZE - 20, SIZE - 20), fill=RED)
    d.rectangle((80, 165, SIZE - 80, 235), fill=WHITE)
    return img


def yield_sign():
    img, d = _canvas()
    d.polygon([(20, 50), (SIZE - 20, 50), (SIZE / 2, SIZE - 30)], fill=RED)
    d.polygon([(85, 88), (SIZE - 85, 88), (SIZE / 2, SIZE - 110)], fill=WHITE)
    return img


def no_stopping():
    img, d = _canvas()
    d.ellipse((20, 20, SIZE - 20, SIZE - 20), fill=RED)
    d.ellipse((60, 60, SIZE - 60, SIZE - 60), fill=BLUE)
    d.line((95, 95, SIZE - 95, SIZE - 95), fill=RED, width=36)
    d.line((SIZE - 95, 95, 95, SIZE - 95), fill=RED, width=36)
    return img


def main_road():
    img, d = _canvas()
    d.polygon(_polygon(4, 190), fill=BLACK)
    d.polygon(_polygon(4, 180), fill=WHITE)
    d.polygon(_polygon(4, 120), fill=YELLOW)
    return img


SIGNS = {
    "speed_70.png": speed_limit,
    "stop.png": stop,
    "no_entry.png": no_entry,
    "yield.png": yield_sign,
    "no_stopping.png": no_stopping,
    "main_road.png": main_road,
}
