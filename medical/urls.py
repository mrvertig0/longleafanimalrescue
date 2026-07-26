from django.urls import path

from . import views

urlpatterns = [
    path("events/<int:event_id>/complete/", views.complete_event, name="complete_event"),
    path("animals/<int:animal_id>/events/add/", views.add_event, name="add_event"),
    path("animals/<int:animal_id>/medications/add/", views.add_medication, name="add_medication"),
    path("animals/<int:animal_id>/regenerate/", views.regenerate, name="regenerate_schedule"),
    path("animals/<int:animal_id>/records/upload/", views.upload_record, name="upload_record"),
    path("records/<int:record_id>/delete/", views.delete_record, name="delete_record"),
]
