"""Admin ro'yxat sahifalari uchun umumiy sarlavha: nom, son, tugmalar, KPI kartochkalar, tez filtrlar.

Barcha raqamlar bazadan olinadi (soxta "o'sish %" yo'q). Shablon: templates/admin/prava/list_head.html.
"""


def query_url(request, **params):
    """Joriy GET parametrlarini saqlab, berilganlarini almashtiradi (None — olib tashlaydi)."""
    query = request.GET.copy()
    query.pop("p", None)  # filtr o'zgarsa birinchi sahifaga
    for key, value in params.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    return f"{request.path}?{encoded}" if encoded else request.path


def tab(request, param, value, label, count=None):
    """Segmentli tugma: value=None — "Hammasi"."""
    current = request.GET.get(param)
    return {
        "label": label,
        "count": count,
        "url": query_url(request, **{param: value}),
        "active": current == value if value is not None else current is None,
    }


def pill(request, param, value, label, count=None, tone="neutral"):
    """Yoqib-o'chiriladigan filtr: bosilsa yoqiladi, qayta bosilsa o'chadi."""
    active = request.GET.get(param) == value
    return {
        "label": label,
        "count": count,
        "tone": tone,
        "active": active,
        "url": query_url(request, **{param: None if active else value}),
    }


class PravaListMixin:
    """ModelAdmin uchun: ro'yxat tepasiga Stitch uslubidagi sarlavha qo'shadi."""

    list_before_template = "admin/prava/list_head.html"
    show_add_link = False  # unfold'ning ko'k "+" tugmasi o'rniga sarlavhadagi "Yangi ..." tugmasi
    list_head_title = ""
    list_head_subtitle = ""
    filter_params = ()  # "Filtrlarni tozalash" shu parametrlarni olib tashlaydi

    def get_list_head(self, request):
        return {}

    def changelist_view(self, request, extra_context=None):
        head = {"title": self.list_head_title, "subtitle": self.list_head_subtitle}
        head.update(self.get_list_head(request))
        active = [p for p in request.GET if p in self.filter_params or p == "q"]
        if active:
            head["clear_url"] = query_url(request, **{p: None for p in active})
        extra_context = {**(extra_context or {}), "prava_head": head}
        return super().changelist_view(request, extra_context)
