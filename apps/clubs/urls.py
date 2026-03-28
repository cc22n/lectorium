from django.urls import path
from . import views

app_name = "clubs"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("explore/", views.explore_view, name="explore"),
    path("create/", views.create_view, name="create"),
    path("<int:pk>/", views.detail_view, name="detail"),
    path("<int:pk>/join/", views.join_view, name="join"),
    path("<int:pk>/leave/", views.leave_view, name="leave"),
    path("<int:pk>/force-start/", views.force_start_view, name="force_start"),
    path("<int:pk>/close-discussion/", views.close_discussion_view, name="close_discussion"),
]
