from django.urls import path

from . import views

urlpatterns = [
    path("", views.gallery, name="public_gallery"),
    path("animals/<int:pk>/", views.public_animal, name="public_animal"),
    path("foster/", views.foster_form, name="foster_form"),
    path("adopt/", views.adoption_form, name="adoption_form"),
]
