from django.urls import path

from . import views

urlpatterns = [
    path("", views.reminder_list, name="reminder_list"),
    path("mark-sent/", views.mark_sent, name="mark_reminder_sent"),
]
