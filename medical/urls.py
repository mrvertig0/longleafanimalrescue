from django.urls import path

from . import views

urlpatterns = [
    path("care-log/", views.care_log, name="care_log"),
    path("meds/<int:med_id>/toggle/", views.toggle_med, name="toggle_med"),
    path("events/<int:event_id>/complete/", views.complete_event, name="complete_event"),
    path("animals/<int:animal_id>/events/add/", views.add_event, name="add_event"),
    path("animals/<int:animal_id>/medications/add/", views.add_medication, name="add_medication"),
    path("animals/<int:animal_id>/regenerate/", views.regenerate, name="regenerate_schedule"),
]
