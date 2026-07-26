from django.urls import path

from . import views

urlpatterns = [
    path("", views.household_list, name="household_list"),
    path("<int:pk>/", views.household_detail, name="household_detail"),
    path("<int:pk>/tags/<int:tag_id>/toggle/", views.toggle_tag, name="toggle_tag"),
    path("pipeline/", views.kanban, name="kanban"),
    path("applications/<int:pk>/move/", views.move_application, name="move_application"),
    path("applications/<int:pk>/note/", views.application_note, name="application_note"),
]
