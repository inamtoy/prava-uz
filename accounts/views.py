from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


def register(request):
    return HttpResponse("Tez orada")


@login_required
def profile(request):
    return HttpResponse("Tez orada")
