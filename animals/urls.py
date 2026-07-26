from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("animals/new/", views.animal_create, name="animal_create"),
    path("animals/<int:pk>/", views.animal_detail, name="animal_detail"),
    path("animals/<int:pk>/edit/", views.animal_edit, name="animal_edit"),
    path("animals/<int:pk>/status/", views.update_status, name="animal_status"),
    path("animals/<int:pk>/placements/add/", views.add_placement, name="add_placement"),
    path("animals/<int:pk>/placements/<int:placement_id>/end/", views.end_placement, name="end_placement"),
]
