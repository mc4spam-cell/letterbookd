from django.urls import path

from . import views

urlpatterns = [
    path("livres/recherche/", views.search, name="books_search"),
    path("livres/ajouter/", views.add, name="books_add"),
    path("livres/<int:book_id>/", views.detail, name="books_detail"),
]
