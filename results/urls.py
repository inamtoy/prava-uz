from django.urls import path

from . import views

urlpatterns = [
    path("natija/<int:pk>/", views.result, name="result"),
]
