from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("mavzular/", views.topic_list, name="topic_list"),
    path("mashq/sessiya/<int:pk>/", views.practice, name="practice"),
    path("mashq/<slug:slug>/", views.practice_start, name="practice_start"),
    path("imtihon/", views.exam_start, name="exam_start"),
    path("imtihon/<int:pk>/", views.exam, name="exam"),
    path("imtihon/<int:pk>/yakunlash/", views.exam_finish, name="exam_finish"),
    path("api/imtihon/<int:pk>/javob/", views.exam_answer, name="exam_answer"),
]
