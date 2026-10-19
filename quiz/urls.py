from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("mavzular/", views.topic_list, name="topic_list"),
    path("imtihon/", views.exam_start, name="exam_start"),
]
