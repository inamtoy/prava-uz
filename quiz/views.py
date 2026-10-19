from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    return render(request, "quiz/home.html")


@login_required
def topic_list(request):
    return render(request, "quiz/home.html")


@login_required
def exam_start(request):
    return render(request, "quiz/home.html")
