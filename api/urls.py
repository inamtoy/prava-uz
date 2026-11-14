from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.register, name="api_register"),
    path("auth/login/", views.login, name="api_login"),
    path("auth/logout/", views.logout, name="api_logout"),
    path("me/", views.me, name="api_me"),
    path("config/", views.config, name="api_config"),
    path("topics/", views.topics, name="api_topics"),
    path("topics/<slug:slug>/practice/", views.practice_start, name="api_practice_start"),
    path("exams/", views.exam_current_or_start, name="api_exams"),
    path("sessions/<int:pk>/", views.session, name="api_session"),
    path("sessions/<int:pk>/answer/", views.answer, name="api_answer"),
    path("sessions/<int:pk>/finish/", views.finish, name="api_finish"),
    path("sessions/<int:pk>/result/", views.result, name="api_result"),
    path("stats/", views.stats, name="api_stats"),
]
