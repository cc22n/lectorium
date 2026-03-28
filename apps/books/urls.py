from django.urls import path
from . import views

app_name = "books"

urlpatterns = [
    path("search/", views.book_search_view, name="search"),
    path("create/", views.manual_create_view, name="manual_create"),
    path("save-from-google/", views.save_google_book_view, name="save_from_google"),
]
